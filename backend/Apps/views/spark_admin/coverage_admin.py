"""Coverage admin endpoints — user safety, verify, QA, side features, banners, matches, ledgers."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action

from models.models import (
    AnalyticsEvent, BoostSession, CampusProfile, Compliment, DateShare,
    EmergencyContact, EntitlementLedger, FaceToFaceSession, Match, MatchmakerInvite,
    MatchQA, OpsBanner, QaTemplate, SayHi, SelectQueue, SwipeNightPick,
    SwipeNightSession, User, UserSafetyPref, VerifyInquiry,
)
from tools.spark_helpers import (
    ensure_daily_feed, ensure_daily_likes, get_or_create_pair_match,
    grant_ledger, period_day_key, serialize_match_messaging, serialize_user_card,
)
from tools.utils import ApiResponse, CustomPagination


def _audit(request, event, props=None):
    try:
        AnalyticsEvent.objects.create(
            app_id=getattr(request.user, 'app_id', None) or 'spark_main',
            user=request.user if getattr(request.user, 'id', None) else None,
            event=event,
            props=props or {},
        )
    except Exception:
        pass


class CoverageAdminMixin:
    """Mixin appended onto SparkAdminViewSet."""

    @extend_schema(summary=_('用户安全'))
    @action(detail=False, methods=['get', 'post'], url_path='user-safety')
    def user_safety_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            kind = request.query_params.get('kind') or 'date_shares'
            page = CustomPagination()
            if kind == 'sos':
                qs = AnalyticsEvent.objects.filter(**scope, event='sos').select_related('user').order_by('-id')
                result = page.paginate_queryset(qs, request)
                data = [{
                    'id': e.id,
                    'user_id': e.user_id,
                    'nickname': (e.user.nickname or e.user.username) if e.user_id else '',
                    'props': e.props or {},
                    'created_at': e.created_at.isoformat() if e.created_at else None,
                } for e in result]
                return page.get_paginated_response(data)
            if kind == 'emergency':
                user_scope = scope
                qs = EmergencyContact.objects.filter(
                    user__app_id__in=user_scope.get('app_id__in') or [user_scope.get('app_id', app_id)]
                    if 'app_id__in' in user_scope or 'app_id' in user_scope
                    else Q()
                )
                # simpler:
                if 'app_id__in' in scope:
                    qs = EmergencyContact.objects.filter(user__app_id__in=scope['app_id__in'])
                else:
                    qs = EmergencyContact.objects.filter(user__app_id=scope.get('app_id', app_id))
                qs = qs.select_related('user').order_by('-id')
                result = page.paginate_queryset(qs, request)
                data = [{
                    'id': r.id,
                    'user_id': r.user_id,
                    'nickname': r.user.nickname or r.user.username,
                    'name': r.name,
                    'phone': r.phone,
                } for r in result]
                return page.get_paginated_response(data)
            # date shares
            if 'app_id__in' in scope:
                qs = DateShare.objects.filter(user__app_id__in=scope['app_id__in'])
            else:
                qs = DateShare.objects.filter(user__app_id=scope.get('app_id', app_id))
            qs = qs.select_related('user').order_by('-id')
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': s.id,
                'user_id': s.user_id,
                'nickname': s.user.nickname or s.user.username,
                'peer_name': s.peer_name,
                'place': s.place or s.venue,
                'when_text': s.when_text,
                'share_token': s.share_token,
                'expires_at': s.expires_at.isoformat() if s.expires_at else None,
                'sms_sent': s.sms_sent,
                'expired': bool(s.expires_at and s.expires_at < timezone.now()),
            } for s in result]
            return page.get_paginated_response(data)

        app_id, err = self._write_app_id(request)
        if err:
            return err
        action_name = request.data.get('action')
        if action_name == 'revoke_share':
            sid = request.data.get('id')
            share = DateShare.objects.filter(id=sid, user__app_id=app_id).first()
            if not share:
                return ApiResponse(code=404, message='not found')
            share.expires_at = timezone.now() - timedelta(seconds=1)
            share.save(update_fields=['expires_at'])
            _audit(request, 'admin_revoke_date_share', {'share_id': share.id})
            return ApiResponse(data={'id': share.id, 'revoked': True}, message='ok')
        return ApiResponse(code=400, message='unknown action')

    @extend_schema(summary=_('实人核验工单'))
    @action(detail=False, methods=['get', 'post'], url_path='verify-inquiries')
    def verify_inquiries_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            qs = VerifyInquiry.objects.filter(**scope).select_related('user').order_by('-id')
            status_f = request.query_params.get('status')
            if status_f:
                qs = qs.filter(status=status_f)
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': r.id,
                'app_id': r.app_id,
                'user_id': r.user_id,
                'nickname': r.user.nickname or r.user.username,
                'inquiry_id': r.inquiry_id,
                'status': r.status,
                'provider': r.provider,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'decided_at': r.decided_at.isoformat() if r.decided_at else None,
            } for r in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        action_name = request.data.get('action') or 'decide'
        rid = request.data.get('id')
        row = VerifyInquiry.objects.filter(id=rid, app_id=app_id).select_related('user').first()
        if not row:
            return ApiResponse(code=404, message='not found')
        if action_name == 'decide':
            approve = bool(request.data.get('approve', True))
            row.status = VerifyInquiry.STATUS_APPROVED if approve else VerifyInquiry.STATUS_DECLINED
            row.decided_at = timezone.now()
            row.save(update_fields=['status', 'decided_at', 'updated_at'])
            row.user.is_verified = bool(approve)
            row.user.save(update_fields=['is_verified', 'updated_at'])
            _audit(request, 'admin_verify_decide', {'inquiry_id': row.inquiry_id, 'approve': approve})
            return ApiResponse(data={'id': row.id, 'status': row.status}, message='ok')
        return ApiResponse(code=400, message='unknown action')

    @extend_schema(summary=_('QA 模板'))
    @action(detail=False, methods=['get', 'post'], url_path='qa-templates')
    def qa_templates_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            write_app = concrete_app_id_safe(request, app_id)
            locale = request.query_params.get('locale') or ''
            if write_app:
                qs = QaTemplate.objects.filter(Q(app_id='') | Q(app_id=write_app)).order_by('sort', 'id')
            else:
                qs = QaTemplate.objects.all().order_by('sort', 'id')
            if locale:
                qs = qs.filter(locale__istartswith=locale[:2])
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': t.id, 'app_id': t.app_id, 'locale': t.locale, 'text': t.text,
                'tags': t.tags or [], 'enabled': t.enabled, 'sort': t.sort,
            } for t in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        tid = request.data.get('id')
        if request.data.get('action') == 'delete' and tid:
            QaTemplate.objects.filter(id=tid).delete()
            return ApiResponse(message='ok')
        defaults = {
            'app_id': request.data.get('app_id') if request.data.get('app_id') is not None else app_id,
            'locale': (request.data.get('locale') or 'zh')[:16],
            'text': (request.data.get('text') or '')[:500],
            'tags': request.data.get('tags') if isinstance(request.data.get('tags'), list) else [],
            'enabled': bool(request.data.get('enabled', True)),
            'sort': int(request.data.get('sort') or 0),
        }
        if not defaults['text']:
            return ApiResponse(code=400, message='text required')
        if tid:
            row = QaTemplate.objects.filter(id=tid).first()
            if not row:
                return ApiResponse(code=404, message='not found')
            for k, v in defaults.items():
                setattr(row, k, v)
            row.save()
        else:
            row = QaTemplate.objects.create(**defaults)
        return ApiResponse(data={'id': row.id}, message='ok', code=201 if not tid else 200)

    @extend_schema(summary=_('Match QA 巡查'))
    @action(detail=False, methods=['get'], url_path='match-qa')
    def match_qa_admin(self, request):
        app_id, err = self._app_id(request)
        if err:
            return err
        scope = self._app_scope(request, app_id)
        if 'app_id__in' in scope:
            qs = MatchQA.objects.filter(
                Q(match__user_a__app_id__in=scope['app_id__in']) | Q(match__user_b__app_id__in=scope['app_id__in'])
            )
        else:
            aid = scope.get('app_id', app_id)
            qs = MatchQA.objects.filter(
                Q(match__user_a__app_id=aid) | Q(match__user_b__app_id=aid)
            )
        status_f = request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f)
        else:
            qs = qs.exclude(status=MatchQA.STATUS_APPROVED)
        qs = qs.select_related('match', 'asker', 'answerer').order_by('-updated_at')
        page = CustomPagination()
        result = page.paginate_queryset(qs, request)
        data = [{
            'id': qa.id,
            'match_id': qa.match_id,
            'status': qa.status,
            'question': qa.question,
            'answer': qa.answer,
            'asker_id': qa.asker_id,
            'answerer_id': qa.answerer_id,
            'updated_at': qa.updated_at.isoformat() if qa.updated_at else None,
        } for qa in result]
        return page.get_paginated_response(data)

    @extend_schema(summary=_('Swipe Night 场次'))
    @action(detail=False, methods=['get', 'post'], url_path='swipe-night')
    def swipe_night_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            qs = SwipeNightSession.objects.filter(**scope).order_by('-starts_at')
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = []
            for s in result:
                picks = SwipeNightPick.objects.filter(session=s).count()
                data.append({
                    'id': s.id, 'app_id': s.app_id, 'status': s.status,
                    'starts_at': s.starts_at.isoformat() if s.starts_at else None,
                    'ends_at': s.ends_at.isoformat() if s.ends_at else None,
                    'pick_count': picks,
                })
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        starts = request.data.get('starts_at')
        ends = request.data.get('ends_at')
        now = timezone.now()
        try:
            from django.utils.dateparse import parse_datetime
            starts_at = parse_datetime(starts) if starts else now
            ends_at = parse_datetime(ends) if ends else (now + timedelta(hours=3))
        except Exception:
            starts_at, ends_at = now, now + timedelta(hours=3)
        if timezone.is_naive(starts_at):
            starts_at = timezone.make_aware(starts_at)
        if timezone.is_naive(ends_at):
            ends_at = timezone.make_aware(ends_at)
        session = SwipeNightSession.objects.create(
            app_id=app_id, starts_at=starts_at, ends_at=ends_at, status='open',
        )
        _audit(request, 'admin_swipe_night_create', {'session_id': session.id})
        return ApiResponse(data={'id': session.id, 'status': session.status}, message='ok', code=201)

    @extend_schema(summary=_('Swipe Night 操作'))
    @action(detail=False, methods=['post'], url_path='swipe-night/action')
    def swipe_night_action(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        action_name = request.data.get('action')
        sid = request.data.get('session_id') or request.data.get('id')
        session = SwipeNightSession.objects.filter(id=sid, app_id=app_id).first()
        if not session:
            return ApiResponse(code=404, message='not found')
        if action_name == 'close':
            session.status = 'closed'
            session.save(update_fields=['status'])
            return ApiResponse(data={'id': session.id, 'status': session.status}, message='ok')
        if action_name == 'settle':
            from Apps.views.swipe_night.view import settle_mutual_picks
            results = settle_mutual_picks(session)
            session.status = 'settled'
            session.save(update_fields=['status'])
            _audit(request, 'admin_swipe_night_settle', {'session_id': session.id, 'matches': len(results)})
            return ApiResponse(data={
                'id': session.id, 'status': session.status, 'matches': len(results), 'list': results,
            }, message='ok')
        if action_name == 'cancel':
            session.status = 'closed'
            session.save(update_fields=['status'])
            return ApiResponse(data={'id': session.id, 'status': session.status}, message='ok')
        return ApiResponse(code=400, message='unknown action')

    @extend_schema(summary=_('Matchmaker 邀请'))
    @action(detail=False, methods=['get', 'post'], url_path='matchmaker')
    def matchmaker_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            if 'app_id__in' in scope:
                qs = MatchmakerInvite.objects.filter(matchmaker__app_id__in=scope['app_id__in'])
            else:
                qs = MatchmakerInvite.objects.filter(matchmaker__app_id=scope.get('app_id', app_id))
            status_f = request.query_params.get('status')
            if status_f:
                qs = qs.filter(Q(a_status=status_f) | Q(b_status=status_f))
            qs = qs.select_related('matchmaker', 'user_a', 'user_b').order_by('-id')
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': i.id,
                'matchmaker_id': i.matchmaker_id,
                'user_a_id': i.user_a_id,
                'user_b_id': i.user_b_id,
                'a_status': i.a_status,
                'b_status': i.b_status,
                'message': i.message,
                'match_id': i.match_id,
                'created_at': i.created_at.isoformat() if i.created_at else None,
            } for i in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        if request.data.get('action') == 'void':
            invite = MatchmakerInvite.objects.filter(id=request.data.get('id')).first()
            if not invite:
                return ApiResponse(code=404, message='not found')
            invite.a_status = 'rejected'
            invite.b_status = 'rejected'
            invite.save(update_fields=['a_status', 'b_status'])
            _audit(request, 'admin_matchmaker_void', {'invite_id': invite.id})
            return ApiResponse(data={'id': invite.id}, message='ok')
        return ApiResponse(code=400, message='unknown action')

    @extend_schema(summary=_('Campus 审核'))
    @action(detail=False, methods=['get', 'post'], url_path='campus')
    def campus_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            if 'app_id__in' in scope:
                qs = CampusProfile.objects.filter(user__app_id__in=scope['app_id__in'])
            else:
                qs = CampusProfile.objects.filter(user__app_id=scope.get('app_id', app_id))
            status_f = request.query_params.get('status')
            if status_f:
                qs = qs.filter(status=status_f)
            qs = qs.select_related('user').order_by('-id')
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': c.id,
                'user_id': c.user_id,
                'nickname': c.user.nickname or c.user.username,
                'school': c.school,
                'edu_email': c.edu_email,
                'status': c.status,
                'verified': c.verified,
                'reject_reason': c.reject_reason,
            } for c in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        campus = CampusProfile.objects.filter(id=request.data.get('id'), user__app_id=app_id).first()
        if not campus:
            return ApiResponse(code=404, message='not found')
        action_name = request.data.get('action') or 'approve'
        if action_name == 'approve':
            campus.status = CampusProfile.STATUS_VERIFIED
            campus.verified = True
            campus.verified_at = timezone.now()
            campus.reject_reason = ''
            campus.save()
        elif action_name == 'reject':
            campus.status = CampusProfile.STATUS_REJECTED
            campus.verified = False
            campus.reject_reason = (request.data.get('reason') or '')[:256]
            campus.save()
        else:
            return ApiResponse(code=400, message='unknown action')
        _audit(request, 'admin_campus_' + action_name, {'campus_id': campus.id})
        return ApiResponse(data={'id': campus.id, 'status': campus.status}, message='ok')

    @extend_schema(summary=_('Select 审核'))
    @action(detail=False, methods=['get', 'post'], url_path='select')
    def select_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            qs = SelectQueue.objects.filter(**scope).select_related('user').order_by('-id')
            status_f = request.query_params.get('status')
            if status_f:
                qs = qs.filter(status=status_f)
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': r.id, 'app_id': r.app_id, 'user_id': r.user_id,
                'nickname': r.user.nickname or r.user.username,
                'status': r.status, 'note': r.note,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            } for r in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        row = SelectQueue.objects.filter(id=request.data.get('id'), app_id=app_id).first()
        if not row:
            return ApiResponse(code=404, message='not found')
        action_name = request.data.get('action') or 'select'
        if action_name in ('select', 'approve'):
            row.status = SelectQueue.STATUS_SELECTED
        elif action_name == 'reject':
            row.status = SelectQueue.STATUS_REJECTED
        elif action_name == 'remove':
            row.status = SelectQueue.STATUS_REJECTED
        else:
            return ApiResponse(code=400, message='unknown action')
        row.save(update_fields=['status', 'updated_at'])
        _audit(request, 'admin_select_' + action_name, {'id': row.id})
        return ApiResponse(data={'id': row.id, 'status': row.status}, message='ok')

    @extend_schema(summary=_('Face to Face 会话'))
    @action(detail=False, methods=['get', 'post'], url_path='face-to-face')
    def face_to_face_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            if 'app_id__in' in scope:
                qs = FaceToFaceSession.objects.filter(user__app_id__in=scope['app_id__in'])
            else:
                qs = FaceToFaceSession.objects.filter(user__app_id=scope.get('app_id', app_id))
            active_only = request.query_params.get('active') != '0'
            if active_only:
                qs = qs.filter(Q(end_at__isnull=True) | Q(end_at__gt=timezone.now()))
            qs = qs.select_related('user').order_by('-id')
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': s.id, 'user_id': s.user_id,
                'nickname': s.user.nickname or s.user.username,
                'lat': s.lat, 'lng': s.lng, 'radius_km': s.radius_km,
                'start_at': s.start_at.isoformat() if s.start_at else None,
                'end_at': s.end_at.isoformat() if s.end_at else None,
            } for s in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        session = FaceToFaceSession.objects.filter(id=request.data.get('id'), user__app_id=app_id).first()
        if not session:
            return ApiResponse(code=404, message='not found')
        if request.data.get('action') == 'end':
            session.end_at = timezone.now()
            session.is_active = False
            session.save(update_fields=['end_at', 'is_active'])
            _audit(request, 'admin_f2f_end', {'session_id': session.id})
            return ApiResponse(data={'id': session.id, 'ended': True}, message='ok')
        return ApiResponse(code=400, message='unknown action')

    @extend_schema(summary=_('运营 Banner'))
    @action(detail=False, methods=['get', 'post'], url_path='ops-banners')
    def ops_banners_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            qs = OpsBanner.objects.filter(**scope).order_by('sort', 'id')
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': b.id, 'app_id': b.app_id, 'placement': b.placement,
                'title': b.title, 'subtitle': b.subtitle, 'image_url': b.image_url,
                'deep_link': b.deep_link, 'enabled': b.enabled, 'sort': b.sort,
                'starts_at': b.starts_at.isoformat() if b.starts_at else None,
                'ends_at': b.ends_at.isoformat() if b.ends_at else None,
            } for b in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        if request.data.get('action') == 'delete':
            OpsBanner.objects.filter(id=request.data.get('id'), app_id=app_id).delete()
            return ApiResponse(message='ok')
        from django.utils.dateparse import parse_datetime
        bid = request.data.get('id')
        fields = {
            'app_id': app_id,
            'placement': request.data.get('placement') or OpsBanner.PLACEMENT_DISCOVER_HOME,
            'title': (request.data.get('title') or '')[:128],
            'subtitle': (request.data.get('subtitle') or '')[:256],
            'image_url': (request.data.get('image_url') or '')[:500],
            'deep_link': (request.data.get('deep_link') or '')[:512],
            'enabled': bool(request.data.get('enabled', True)),
            'sort': int(request.data.get('sort') or 0),
        }
        if not fields['title']:
            return ApiResponse(code=400, message='title required')
        starts = request.data.get('starts_at')
        ends = request.data.get('ends_at')
        fields['starts_at'] = parse_datetime(starts) if starts else None
        fields['ends_at'] = parse_datetime(ends) if ends else None
        if bid:
            row = OpsBanner.objects.filter(id=bid, app_id=app_id).first()
            if not row:
                return ApiResponse(code=404, message='not found')
            for k, v in fields.items():
                setattr(row, k, v)
            row.save()
        else:
            row = OpsBanner.objects.create(**fields)
        return ApiResponse(data={'id': row.id}, message='ok', code=201 if not bid else 200)

    @extend_schema(summary=_('匹配巡查'))
    @action(detail=False, methods=['get'], url_path='matches')
    def matches_admin(self, request):
        app_id, err = self._app_id(request)
        if err:
            return err
        scope = self._app_scope(request, app_id)
        if 'app_id__in' in scope:
            qs = Match.objects.filter(
                Q(user_a__app_id__in=scope['app_id__in']) | Q(user_b__app_id__in=scope['app_id__in'])
            )
        else:
            aid = scope.get('app_id', app_id)
            qs = Match.objects.filter(Q(user_a__app_id=aid) | Q(user_b__app_id=aid))
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(Q(user_a_id=user_id) | Q(user_b_id=user_id))
        status_f = request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f)
        qs = qs.select_related('user_a', 'user_b').order_by('-id')
        page = CustomPagination()
        result = page.paginate_queryset(qs, request)
        data = []
        for m in result:
            data.append({
                'id': m.id,
                'status': m.status,
                'messaging_mode': m.messaging_mode,
                'user_a_id': m.user_a_id,
                'user_b_id': m.user_b_id,
                'user_a': m.user_a.nickname or m.user_a.username,
                'user_b': m.user_b.nickname or m.user_b.username,
                'expire_at': m.expire_at.isoformat() if m.expire_at else None,
                'opened_at': m.opened_at.isoformat() if m.opened_at else None,
                'created_at': m.created_at.isoformat() if m.created_at else None,
            })
        return page.get_paginated_response(data)

    @extend_schema(summary=_('匹配操作'))
    @action(detail=False, methods=['post'], url_path='matches/action')
    def matches_action(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        mid = request.data.get('match_id') or request.data.get('id')
        m = Match.objects.filter(id=mid).filter(
            Q(user_a__app_id=app_id) | Q(user_b__app_id=app_id)
        ).first()
        if not m:
            return ApiResponse(code=404, message='not found')
        if request.data.get('action') == 'force_unmatch':
            m.status = 'ended'
            m.save(update_fields=['status'])
            _audit(request, 'admin_force_unmatch', {'match_id': m.id})
            return ApiResponse(data={'id': m.id, 'status': m.status}, message='ok')
        return ApiResponse(code=400, message='unknown action')

    @extend_schema(summary=_('额度账本'))
    @action(detail=False, methods=['get', 'post'], url_path='ledgers')
    def ledgers_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            user_id = request.query_params.get('user_id')
            if 'app_id__in' in scope:
                qs = EntitlementLedger.objects.filter(user__app_id__in=scope['app_id__in'])
            else:
                qs = EntitlementLedger.objects.filter(user__app_id=scope.get('app_id', app_id))
            if user_id:
                qs = qs.filter(user_id=user_id)
            kind = request.query_params.get('kind')
            if kind:
                qs = qs.filter(kind=kind)
            qs = qs.select_related('user').order_by('-id')
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': r.id, 'user_id': r.user_id,
                'nickname': r.user.nickname or r.user.username,
                'kind': r.kind, 'balance': r.balance, 'period_key': r.period_key,
                'updated_at': r.updated_at.isoformat() if getattr(r, 'updated_at', None) else None,
            } for r in result]
            boosts = []
            if user_id:
                bqs = BoostSession.objects.filter(user_id=user_id).order_by('-id')[:20]
                boosts = [{
                    'id': b.id, 'start_at': b.start_at.isoformat() if b.start_at else None,
                    'end_at': b.end_at.isoformat() if b.end_at else None,
                } for b in bqs]
            resp = page.get_paginated_response(data)
            body = resp.data
            body['boosts'] = boosts
            return resp
        app_id, err = self._write_app_id(request)
        if err:
            return err
        user = User.objects.filter(id=request.data.get('user_id'), app_id=app_id, role='user').first()
        if not user:
            return ApiResponse(code=404, message='user not found')
        kind = request.data.get('kind')
        qty = int(request.data.get('quantity') or 0)
        kind_map = {
            'super_like': EntitlementLedger.SUPER_LIKE,
            'boost': EntitlementLedger.BOOST,
            'rewind': EntitlementLedger.REWIND,
            'daily_like': EntitlementLedger.DAILY_LIKE,
            'daily_feed': EntitlementLedger.DAILY_FEED,
        }
        if kind not in kind_map or qty == 0:
            return ApiResponse(code=400, message='invalid kind/quantity')
        grant_ledger(user, kind_map[kind], qty, period_key=request.data.get('period_key') or 'admin')
        _audit(request, 'admin_ledger_grant', {'user_id': user.id, 'kind': kind, 'qty': qty})
        return ApiResponse(message='ok')


def is_all_like(app_id):
    return app_id in ('*', 'ALL', 'all', '', None)


def concrete_app_id_safe(request, app_id):
    """Return concrete app_id or None when workspace is * (no silent remap)."""
    from tools.admin_rbac import is_all_app
    if is_all_app(app_id):
        return None
    return app_id


def _settle_swipe_night(session):
    """Mutual picks → matches. Returns match count."""
    picks = list(SwipeNightPick.objects.filter(session=session))
    by_actor = {}
    for p in picks:
        by_actor.setdefault(p.actor_id, set()).add(p.target_id)
    matched = set()
    count = 0
    for actor_id, targets in by_actor.items():
        for tid in targets:
            pair = tuple(sorted((actor_id, tid)))
            if pair in matched:
                continue
            if actor_id in by_actor.get(tid, set()):
                matched.add(pair)
                ua = User.objects.filter(id=pair[0]).first()
                ub = User.objects.filter(id=pair[1]).first()
                if ua and ub:
                    get_or_create_pair_match(ua.id, ub.id, app_id=session.app_id)
                    count += 1
    return count
