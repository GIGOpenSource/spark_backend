from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.spark_helpers import (
    serialize_user_card, live_match_filter, serialize_match_messaging, extend_match_open_window,
    can_user_open_chat, clear_match_expire_if_opened, message_contains_banned, blocked_ids,
)
from tools.qa_templates import list_qa_templates
from tools.push_service import (
    notify_safe, EVENT_QA_NEED_ANSWER, EVENT_QA_NEED_REVIEW,
)
from models.models import Match, Conversation, Message, Swipe


def _qa_room_link(match):
    conv = Conversation.objects.filter(match=match).first()
    if conv:
        return f'/pagesA/chat/room?id={conv.id}'
    return '/pages/chat/index'


def _notify_qa_stage(match, event_type, recipient, actor):
    if not recipient:
        return
    nick = (actor.nickname if actor else '') or ''
    notify_safe(recipient, event_type, {
        'nickname': nick,
        'match_id': match.id,
        'deep_link': _qa_room_link(match),
    })


@extend_schema(tags=[_('匹配')])
class MatchViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('发送开场白'))
    @action(detail=False, methods=['post'], url_path='open-message')
    def open_message(self, request):
        content = (request.data.get('content') or '').strip()
        if not content:
            return ApiResponse(code=400, message='content required')
        if len(content) > 2000:
            return ApiResponse(code=400, message='content too long')
        match = Match.objects.filter(id=request.data.get('match_id')).filter(
            Q(user_a=request.user) | Q(user_b=request.user),
        ).first()
        if not match:
            return ApiResponse(code=404, message='not found')
        if match.status != 'active' or (match.expire_at and match.expire_at < timezone.now()):
            return ApiResponse(code=400, message='match_expired')
        other = match.user_b if match.user_a_id == request.user.id else match.user_a
        if other.id in blocked_ids(request.user):
            return ApiResponse(code=403, message='blocked')
        if other.app_id and request.user.app_id and other.app_id != request.user.app_id:
            return ApiResponse(code=403, message='cross_app')
        banned = message_contains_banned(request.user.app_id, content, request.user.country or '*', user=request.user)
        if banned:
            return ApiResponse(code=400, message='content_blocked', data={'word': banned})
        ok, err = can_user_open_chat(match, request.user)
        if not ok:
            return ApiResponse(code=403, message=err or 'waiting_for_opener',
                               data=serialize_match_messaging(match, request.user))
        conv, _ = Conversation.objects.get_or_create(
            match=match, defaults={'user_a': match.user_a, 'user_b': match.user_b},
        )
        message = Message.objects.create(conversation=conv, sender=request.user, content=content, msg_type='text')
        conv.last_message, conv.last_at = content[:512], timezone.now()
        conv.save(update_fields=['last_message', 'last_at'])
        clear_match_expire_if_opened(match)
        return ApiResponse(data={'match_id': match.id, 'conversation_id': conv.id, 'message_id': message.id},
                           message='ok', code=201)

    @extend_schema(summary=_('匹配列表'))
    @action(detail=False, methods=['get'], url_path='list')
    def list_matches(self, request):
        user = request.user
        rows = Match.objects.filter(
            Q(user_a=user) | Q(user_b=user),
        ).filter(live_match_filter()).order_by('-id')[:50]
        items = []
        for m in rows:
            other = m.user_b if m.user_a_id == user.id else m.user_a
            # hard isolation: only same-app peers
            if other.app_id and user.app_id and other.app_id != user.app_id:
                continue
            conv = Conversation.objects.filter(match=m).first()
            items.append({
                'match_id': m.id,
                'conversation_id': conv.id if conv else None,
                'user': serialize_user_card(other),
                'created_at': m.created_at.isoformat(),
                'expire_at': m.expire_at.isoformat() if m.expire_at else None,
                'status': m.status,
                **serialize_match_messaging(m, user),
            })
        return ApiResponse(data={'list': items}, message='ok')

    @extend_schema(summary=_('她说推荐题库'))
    @action(detail=False, methods=['get'], url_path='qa/templates')
    def qa_templates(self, request):
        locale = request.query_params.get('locale') or getattr(request.user, 'locale', None) or 'zh'
        app_id = getattr(request.user, 'app_id', '') or ''
        return ApiResponse(data={'list': list_qa_templates(locale, app_id=app_id)}, message='ok')

    @extend_schema(summary=_('延长开聊时限'))
    @action(detail=False, methods=['post'], url_path='extend')
    def extend_match(self, request):
        """Bumble-like Extend: opener extends unopened women_first match once."""
        mid = request.data.get('match_id')
        m = Match.objects.filter(id=mid).filter(Q(user_a=request.user) | Q(user_b=request.user)).first()
        if not m:
            return ApiResponse(message='not found', code=404)
        ok, err = extend_match_open_window(m, request.user)
        if not ok:
            code = 403 if err == 'need_extend' else 400
            data = serialize_match_messaging(m, request.user)
            if err == 'need_extend':
                data['need_shop'] = True
            return ApiResponse(code=code, message=err or 'extend_failed', data=data)
        m.refresh_from_db()
        return ApiResponse(data={
            'match_id': m.id,
            **serialize_match_messaging(m, request.user),
        }, message='ok')

    @extend_schema(summary=_('她说出题'))
    @action(detail=False, methods=['post'], url_path='qa/ask')
    def qa_ask(self, request):
        from models.models import MatchQA
        mid = request.data.get('match_id')
        question = (request.data.get('question') or '').strip()
        if not question:
            return ApiResponse(code=400, message='question required')
        m = Match.objects.filter(id=mid).filter(Q(user_a=request.user) | Q(user_b=request.user)).first()
        if not m or m.messaging_mode != 'qa_gate':
            return ApiResponse(code=404, message='not found')
        qa = MatchQA.objects.filter(match=m).first()
        if not qa or qa.asker_id != request.user.id:
            return ApiResponse(code=403, message='not_asker')
        if qa.status != MatchQA.STATUS_NEED_QUESTION:
            return ApiResponse(code=400, message='invalid_status')
        qa.question = question[:500]
        qa.status = MatchQA.STATUS_NEED_ANSWER
        qa.save(update_fields=['question', 'status', 'updated_at'])
        from Apps.views.match.consumers import broadcast_match_qa
        broadcast_match_qa(m, request.user)
        _notify_qa_stage(m, EVENT_QA_NEED_ANSWER, qa.answerer, request.user)
        return ApiResponse(data=serialize_match_messaging(m, request.user), message='ok')

    @extend_schema(summary=_('她说答题'))
    @action(detail=False, methods=['post'], url_path='qa/answer')
    def qa_answer(self, request):
        from models.models import MatchQA
        mid = request.data.get('match_id')
        answer = (request.data.get('answer') or '').strip()
        if not answer:
            return ApiResponse(code=400, message='answer required')
        m = Match.objects.filter(id=mid).filter(Q(user_a=request.user) | Q(user_b=request.user)).first()
        if not m or m.messaging_mode != 'qa_gate':
            return ApiResponse(code=404, message='not found')
        qa = MatchQA.objects.filter(match=m).first()
        if not qa or qa.answerer_id != request.user.id:
            return ApiResponse(code=403, message='not_answerer')
        if qa.status not in (MatchQA.STATUS_NEED_ANSWER, MatchQA.STATUS_REJECTED):
            return ApiResponse(code=400, message='invalid_status')
        qa.answer = answer[:1000]
        qa.status = MatchQA.STATUS_NEED_REVIEW
        qa.save(update_fields=['answer', 'status', 'updated_at'])
        from Apps.views.match.consumers import broadcast_match_qa
        broadcast_match_qa(m, request.user)
        _notify_qa_stage(m, EVENT_QA_NEED_REVIEW, qa.asker, request.user)
        return ApiResponse(data=serialize_match_messaging(m, request.user), message='ok')

    @extend_schema(summary=_('她说审阅'))
    @action(detail=False, methods=['post'], url_path='qa/review')
    def qa_review(self, request):
        from models.models import MatchQA
        from tools.spark_helpers import clear_match_expire_if_opened
        mid = request.data.get('match_id')
        approve = bool(request.data.get('approve', True))
        allow_retry = request.data.get('allow_retry')
        if allow_retry is None:
            allow_retry = True
        m = Match.objects.filter(id=mid).filter(Q(user_a=request.user) | Q(user_b=request.user)).first()
        if not m or m.messaging_mode != 'qa_gate':
            return ApiResponse(code=404, message='not found')
        qa = MatchQA.objects.filter(match=m).first()
        if not qa or qa.asker_id != request.user.id:
            return ApiResponse(code=403, message='not_asker')
        if qa.status != MatchQA.STATUS_NEED_REVIEW:
            return ApiResponse(code=400, message='invalid_status')
        if approve:
            qa.status = MatchQA.STATUS_APPROVED
            qa.save(update_fields=['status', 'updated_at'])
            clear_match_expire_if_opened(m)
        else:
            # 她说：拒绝后可要求重答（默认），或直接结束匹配
            if allow_retry:
                qa.status = MatchQA.STATUS_NEED_ANSWER
                qa.answer = ''
                qa.save(update_fields=['status', 'answer', 'updated_at'])
                _notify_qa_stage(m, EVENT_QA_NEED_ANSWER, qa.answerer, request.user)
            else:
                qa.status = MatchQA.STATUS_REJECTED
                qa.save(update_fields=['status', 'updated_at'])
                m.status = 'ended'
                m.save(update_fields=['status'])
        from Apps.views.match.consumers import broadcast_match_qa
        broadcast_match_qa(m, request.user)
        return ApiResponse(data=serialize_match_messaging(m, request.user), message='ok')

    @extend_schema(summary=_('取消匹配'))
    @action(detail=False, methods=['post'], url_path='unmatch')
    def unmatch(self, request):
        """Tinder-like: end match and clear pair likes so both can reappear in feed."""
        mid = request.data.get('match_id')
        m = Match.objects.filter(id=mid).filter(Q(user_a=request.user) | Q(user_b=request.user)).first()
        if not m:
            return ApiResponse(message='not found', code=404)
        m.status = 'ended'
        m.save(update_fields=['status'])
        a_id, b_id = m.user_a_id, m.user_b_id
        Swipe.objects.filter(
            Q(actor_id=a_id, target_id=b_id) | Q(actor_id=b_id, target_id=a_id),
            is_undone=False,
            action__in=('like', 'super_like'),
        ).update(is_undone=True)
        return ApiResponse(message='ok')
