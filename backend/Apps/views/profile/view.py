import logging
import os
import uuid

from django.conf import settings
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.spark_helpers import serialize_user_card, has_vip_at_least, validate_social_links, blocked_ids
from models.models import User, UserPhoto, UserFilter, Block, Report

logger = logging.getLogger(__name__)


@extend_schema(tags=[_('资料')])
class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(summary=_('我的资料'))
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        return ApiResponse(data=serialize_user_card(request.user, include_pending_photos=True), message='ok')

    @extend_schema(summary=_('更新资料'))
    @action(detail=False, methods=['put', 'patch'], url_path='me/update')
    def update_me(self, request):
        user = request.user
        fields = [
            'nickname', 'bio', 'job', 'city', 'country', 'gender', 'mbti', 'zodiac',
            'relationship', 'looking_for', 'locale', 'invisible_mode', 'is_traveling',
            'passport_city', 'school', 'orientation', 'pronouns', 'looking_for_intent',
            'discovery_enabled', 'global_mode',
        ]
        for f in fields:
            if f in request.data:
                if f == 'invisible_mode' and request.data.get(f) and not has_vip_at_least(user, 'plus'):
                    return ApiResponse(code=403, message='need_plus', data={'need_vip': True})
                if f == 'global_mode' and request.data.get(f) and not has_vip_at_least(user, 'plus'):
                    return ApiResponse(code=403, message='need_plus', data={'need_vip': True})
                if f == 'passport_city':
                    city = request.data.get(f) or ''
                    # leaving home city requires Plus
                    home = (user.city or '').strip().lower()
                    if city and city.strip().lower() != home and not has_vip_at_least(user, 'plus'):
                        return ApiResponse(code=403, message='need_plus', data={'need_vip': True})
                setattr(user, f, request.data.get(f))
        if 'height_cm' in request.data:
            try:
                h = request.data.get('height_cm')
                user.height_cm = int(h) if h not in (None, '') else None
            except (TypeError, ValueError):
                pass
        if 'languages' in request.data:
            langs = request.data.get('languages') or []
            if isinstance(langs, str):
                langs = [x.strip() for x in langs.split(',') if x.strip()]
            user.languages = langs if isinstance(langs, list) else []
        for jf in ('interests', 'lifestyle', 'social_links'):
            if jf in request.data:
                if jf == 'social_links':
                    ok, bad = validate_social_links(user.app_id, request.data.get(jf) or {})
                    if not ok:
                        return ApiResponse(code=400, message=f'domain_not_allowed:{bad}')
                setattr(user, jf, request.data.get(jf))
        if 'hide_age' in request.data:
            user.hide_age = bool(request.data.get('hide_age'))
        if 'lat' in request.data:
            try:
                user.lat = float(request.data.get('lat'))
            except (TypeError, ValueError):
                pass
        if 'lng' in request.data:
            try:
                user.lng = float(request.data.get('lng'))
            except (TypeError, ValueError):
                pass
        for f in ('passport_lat', 'passport_lng'):
            if f in request.data:
                try:
                    setattr(user, f, float(request.data.get(f)))
                except (TypeError, ValueError):
                    pass
        if 'birthday' in request.data and request.data.get('birthday'):
            from datetime import date
            b = request.data.get('birthday')
            user.birthday = date.fromisoformat(b) if isinstance(b, str) else b
        if not user.invite_code:
            import secrets
            user.invite_code = secrets.token_hex(4)
        user.save()
        return ApiResponse(data=serialize_user_card(user, include_pending_photos=True), message='ok')

    @extend_schema(summary=_('兴趣投票'))
    @action(detail=False, methods=['post'], url_path='interest-vote')
    def interest_vote(self, request):
        interest = (request.data.get('interest') or '').strip()
        try:
            target = User.objects.get(id=int(request.data.get('target_id')))
        except (User.DoesNotExist, TypeError, ValueError):
            return ApiResponse(code=404, message='not found')
        if not interest:
            return ApiResponse(code=400, message='interest required')
        if target.id == request.user.id or target.id in blocked_ids(request.user):
            return ApiResponse(code=403, message='blocked')
        key = interest[:64]
        votes = dict(target.interest_votes or {})
        votes[key] = int(votes.get(key, 0) or 0) + 1
        target.interest_votes = votes
        target.save(update_fields=['interest_votes', 'updated_at'])
        return ApiResponse(data={'target_id': target.id, 'interest': key, 'votes': votes[key]}, message='ok')

    @extend_schema(summary=_('他人资料'))
    @action(detail=False, methods=['get'], url_path='detail')
    def user_detail(self, request):
        # 方法名不能叫 detail：会与 ViewSetMixin.detail 布尔属性冲突，打爆 /api/schema/
        uid = request.query_params.get('user_id')
        try:
            target = User.objects.get(id=uid)
        except User.DoesNotExist:
            return ApiResponse(message='not found', code=404)
        if target.id in blocked_ids(request.user):
            return ApiResponse(code=403, message='blocked')
        return ApiResponse(data=serialize_user_card(target, viewer=request.user), message='ok')

    @extend_schema(summary=_('别人眼中的我'))
    @action(detail=False, methods=['get'], url_path='preview')
    def preview(self, request):
        return ApiResponse(
            data=serialize_user_card(request.user, include_pending_photos=False),
            message='ok',
        )

    @extend_schema(summary=_('Smart Photos 建议排序'))
    @action(detail=False, methods=['post'], url_path='photos/smart')
    def smart_photos(self, request):
        user = request.user
        photos = list(UserPhoto.objects.filter(user=user).order_by('sort_order', 'id'))
        if not photos:
            return ApiResponse(data={'photo_ids': [], 'scores': []}, message='ok')

        def score(p):
            s = 0
            if p.audit_status == 'approved':
                s += 50
            elif p.audit_status == 'pending':
                s += 10
            if p.is_primary:
                s += 5
            url = (p.url or '').lower()
            if any(x in url for x in ('.jpg', '.jpeg', '.png', '.webp')):
                s += 5
            # Prefer earlier ids slightly (stability) then reverse for variety
            s += max(0, 10 - (p.sort_order or 0))
            return s

        ranked = sorted(photos, key=score, reverse=True)
        ids = [p.id for p in ranked]
        apply = bool(request.data.get('apply'))
        if apply and ids:
            for i, pid in enumerate(ids):
                photo = next(p for p in photos if p.id == pid)
                photo.sort_order = i
                photo.is_primary = i == 0
                photo.save(update_fields=['sort_order', 'is_primary'])
            first = UserPhoto.objects.filter(user=user, audit_status='approved').order_by('sort_order', 'id').first()
            if first:
                user.avatar_url = first.url
                user.save(update_fields=['avatar_url'])
        return ApiResponse(data={
            'photo_ids': ids,
            'scores': [{'id': p.id, 'score': score(p), 'url': p.url} for p in ranked],
            'applied': apply,
            'photos': [
                {'id': p.id, 'url': p.url, 'sort_order': p.sort_order, 'audit_status': p.audit_status}
                for p in UserPhoto.objects.filter(user=user).order_by('sort_order', 'id')
            ],
        }, message='ok')

    @extend_schema(summary=_('上传照片'))
    @action(detail=False, methods=['post'], url_path='photos')
    def upload_photo(self, request):
        user = request.user
        url = request.data.get('url')
        f = request.FILES.get('file')
        if f:
            name = f'photos/{user.id}/{uuid.uuid4().hex}_{f.name}'
            path = default_storage.save(name, ContentFile(f.read()))
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            url = request.build_absolute_uri(media_url + path) if hasattr(request, 'build_absolute_uri') else media_url + path
        if not url:
            return ApiResponse(message='url or file required', code=400)
        sort_order = int(request.data.get('sort_order') or user.photos.count())
        photo = UserPhoto.objects.create(
            user=user, url=url, sort_order=sort_order, is_primary=sort_order == 0,
            audit_status='pending',
        )
        # Pending photos are owner-visible only; public avatar stays on last approved
        return ApiResponse(data={
            'id': photo.id, 'url': photo.url, 'audit_status': photo.audit_status,
        }, message='ok', code=201)

    @extend_schema(summary=_('照片排序'))
    @action(detail=False, methods=['post'], url_path='photos/reorder')
    def reorder_photos(self, request):
        user = request.user
        ids = request.data.get('photo_ids') or []
        if not isinstance(ids, list) or not ids:
            return ApiResponse(message='photo_ids required', code=400)
        owned = {p.id: p for p in UserPhoto.objects.filter(user=user, id__in=ids)}
        if len(owned) != len(set(ids)):
            return ApiResponse(message='invalid photo_ids', code=400)
        for i, pid in enumerate(ids):
            photo = owned[int(pid)]
            photo.sort_order = i
            photo.is_primary = i == 0
            photo.save(update_fields=['sort_order', 'is_primary'])
        first = UserPhoto.objects.filter(user=user, audit_status='approved').order_by('sort_order', 'id').first()
        if first:
            user.avatar_url = first.url
            user.save(update_fields=['avatar_url'])
        return ApiResponse(data={'photos': [
            {'id': p.id, 'url': p.url, 'sort_order': p.sort_order, 'audit_status': p.audit_status}
            for p in UserPhoto.objects.filter(user=user).order_by('sort_order', 'id')
        ]}, message='ok')

    @extend_schema(summary=_('删除照片'))
    @action(detail=False, methods=['delete'], url_path=r'photos/(?P<photo_id>[0-9]+)')
    def delete_photo(self, request, photo_id=None):
        photo = UserPhoto.objects.filter(user=request.user, id=photo_id).first()
        if not photo:
            return ApiResponse(message='not found', code=404)
        photo.delete()
        return ApiResponse(message='ok')

    @extend_schema(summary=_('筛选设置'))
    @action(detail=False, methods=['get', 'post'], url_path='filters')
    def filters(self, request):
        obj, _ = UserFilter.objects.get_or_create(user=request.user)
        if request.method == 'GET':
            lifestyle = request.user.lifestyle or {}
            return ApiResponse(data={
                'gender': obj.gender, 'age_min': obj.age_min, 'age_max': obj.age_max,
                'distance_km': obj.distance_km, 'relationship': obj.relationship,
                'language': obj.language, 'zodiac': obj.zodiac, 'education': obj.education,
                'mbti': obj.mbti, 'recommend_type': obj.recommend_type,
                'audience_strict': bool(lifestyle.get('audience_strict')),
                'advanced_unlocked': has_vip_at_least(request.user, 'gold'),
            }, message='ok')
        advanced_fields = ('relationship', 'language', 'zodiac', 'education', 'mbti', 'recommend_type', 'audience_strict')
        wants_advanced = any(f in request.data for f in advanced_fields)
        if wants_advanced and not has_vip_at_least(request.user, 'gold'):
            return ApiResponse(code=403, message='need_gold', data={'need_vip': True})
        for f in ('gender', 'relationship', 'language', 'zodiac', 'education', 'mbti', 'recommend_type'):
            if f in request.data:
                setattr(obj, f, request.data.get(f))
        for f in ('age_min', 'age_max', 'distance_km'):
            if f in request.data:
                val = int(request.data.get(f))
                if f == 'distance_km':
                    # F-14: keep discovery radius sane (default 100; clamp 1–200)
                    val = max(1, min(200, val))
                setattr(obj, f, val)
        # Heal legacy huge defaults once touched
        if obj.distance_km and obj.distance_km > 200:
            obj.distance_km = 100
        obj.save()
        if 'audience_strict' in request.data:
            lifestyle = dict(request.user.lifestyle or {})
            lifestyle['audience_strict'] = bool(request.data.get('audience_strict'))
            request.user.lifestyle = lifestyle
            request.user.save(update_fields=['lifestyle'])
        return ApiResponse(message='ok')

    @extend_schema(summary=_('拉黑'))
    @action(detail=False, methods=['post'], url_path='block')
    def block(self, request):
        tid = request.data.get('user_id')
        if not tid:
            return ApiResponse(message='user_id required', code=400)
        Block.objects.get_or_create(user=request.user, blocked_user_id=tid)
        # end active match if any
        from models.models import Match, SayHi, Swipe
        Match.objects.filter(
            Q(user_a=request.user, user_b_id=tid) | Q(user_a_id=tid, user_b=request.user),
            status='active',
        ).update(status='ended')
        SayHi.objects.filter(
            Q(sender=request.user, receiver_id=tid) | Q(sender_id=tid, receiver=request.user),
            status='pending',
        ).update(status='expired')
        # Tinder-like: clear pair likes so unblock can rematch via new swipes
        Swipe.objects.filter(
            Q(actor=request.user, target_id=tid) | Q(actor_id=tid, target=request.user),
            is_undone=False,
            action__in=('like', 'super_like'),
        ).update(is_undone=True)
        return ApiResponse(message='ok')

    @extend_schema(summary=_('已拉黑列表'))
    @action(detail=False, methods=['get'], url_path='blocks')
    def blocks(self, request):
        rows = Block.objects.filter(user=request.user).select_related('blocked_user').order_by('-id')[:200]
        return ApiResponse(data={
            'list': [serialize_user_card(b.blocked_user) for b in rows if b.blocked_user_id]
        }, message='ok')

    @extend_schema(summary=_('解除拉黑'))
    @action(detail=False, methods=['post'], url_path='unblock')
    def unblock(self, request):
        tid = request.data.get('user_id')
        Block.objects.filter(user=request.user, blocked_user_id=tid).delete()
        return ApiResponse(message='ok')

    @extend_schema(summary=_('举报'))
    @action(detail=False, methods=['post'], url_path='report')
    def report(self, request):
        reason = (request.data.get('reason') or 'other').strip().lower()
        if reason not in Report.ALLOWED_REASONS:
            return ApiResponse(code=400, message='invalid_reason', data={
                'allowed': sorted(Report.ALLOWED_REASONS),
            })
        Report.objects.create(
            reporter=request.user,
            target_user_id=request.data.get('user_id'),
            reason=reason,
            detail=request.data.get('detail') or '',
            app_id=getattr(request.user, 'app_id', None) or 'spark_main',
        )
        return ApiResponse(message='ok', code=201)
