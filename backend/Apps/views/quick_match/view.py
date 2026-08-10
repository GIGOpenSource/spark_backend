from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.spark_helpers import serialize_user_card, blocked_ids
from tools.token_tools import _redis
from models.models import Conversation, QmTicket, QmPair


QM_TICKET_TTL_MINUTES = 10
QM_LOCK_TTL_SEC = 5


def _serialize_ticket(t):
    if not t:
        return None
    return {
        'id': t.id,
        'status': t.status,
        'prefer': t.prefer or {},
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'expire_at': t.expire_at.isoformat() if t.expire_at else None,
    }


def _serialize_pair(p, viewer):
    if not p:
        return None
    other = p.user_b if p.user_a_id == viewer.id else p.user_a
    return {
        'id': p.id,
        'status': p.status,
        'conversation_id': p.conversation_id,
        'matched_at': p.matched_at.isoformat() if p.matched_at else None,
        'peer': serialize_user_card(other),
    }


def _expire_waiting_tickets(app_id):
    now = timezone.now()
    QmTicket.objects.filter(
        app_id=app_id, status=QmTicket.STATUS_WAITING, expire_at__lt=now,
    ).update(status=QmTicket.STATUS_EXPIRED)


def _try_match_locked(user, prefer):
    """Find a waiting peer and create pair + free-chat conversation. Caller holds Redis lock."""
    app_id = user.app_id or 'spark_main'
    _expire_waiting_tickets(app_id)
    blocked = blocked_ids(user)
    now = timezone.now()

    # Cancel any previous waiting ticket for this user
    QmTicket.objects.filter(
        user=user, app_id=app_id, status=QmTicket.STATUS_WAITING,
    ).update(status=QmTicket.STATUS_CANCELLED)

    # Already in active pair?
    active = QmPair.objects.filter(
        Q(user_a=user) | Q(user_b=user),
        app_id=app_id, status=QmPair.STATUS_ACTIVE,
    ).select_related('user_a', 'user_b', 'conversation').first()
    if active:
        return None, active, 'already_matched'

    candidates = (
        QmTicket.objects
        .filter(app_id=app_id, status=QmTicket.STATUS_WAITING)
        .exclude(user=user)
        .filter(Q(expire_at__isnull=True) | Q(expire_at__gte=now))
        .select_related('user')
        .order_by('created_at', 'id')
    )
    peer_ticket = None
    for t in candidates:
        if t.user_id in blocked:
            continue
        if user.app_id and t.user.app_id and t.user.app_id != user.app_id:
            continue
        # peer must not already be in active pair
        if QmPair.objects.filter(
            Q(user_a_id=t.user_id) | Q(user_b_id=t.user_id),
            status=QmPair.STATUS_ACTIVE,
        ).exists():
            continue
        peer_ticket = t
        break

    if not peer_ticket:
        ticket = QmTicket.objects.create(
            user=user,
            app_id=app_id,
            status=QmTicket.STATUS_WAITING,
            prefer=prefer or {},
            expire_at=now + timedelta(minutes=QM_TICKET_TTL_MINUTES),
        )
        return ticket, None, None

    peer = peer_ticket.user
    with transaction.atomic():
        ua, ub = (user, peer) if user.id < peer.id else (peer, user)
        conv = Conversation.objects.create(
            match=None,
            user_a=ua,
            user_b=ub,
            origin=Conversation.ORIGIN_QUICK_MATCH,
        )
        pair = QmPair.objects.create(
            user_a=ua,
            user_b=ub,
            app_id=app_id,
            conversation=conv,
            status=QmPair.STATUS_ACTIVE,
        )
        peer_ticket.status = QmTicket.STATUS_MATCHED
        peer_ticket.save(update_fields=['status'])
        my_ticket = QmTicket.objects.create(
            user=user,
            app_id=app_id,
            status=QmTicket.STATUS_MATCHED,
            prefer=prefer or {},
            expire_at=now + timedelta(minutes=QM_TICKET_TTL_MINUTES),
        )
    pair = QmPair.objects.select_related('user_a', 'user_b', 'conversation').get(id=pair.id)
    return my_ticket, pair, None


@extend_schema(tags=[_('一键速配')])
class QuickMatchViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('进入速配池'))
    @action(detail=False, methods=['post'], url_path='enter')
    def enter(self, request):
        user = request.user
        prefer = request.data.get('prefer') if isinstance(request.data.get('prefer'), dict) else {}
        app_id = user.app_id or 'spark_main'
        lock_key = f'qm:match:{app_id}'
        got_lock = False
        try:
            got_lock = bool(_redis.client.set(lock_key, str(user.id), nx=True, ex=QM_LOCK_TTL_SEC))
            if not got_lock:
                # brief wait without busy-spin: retry once after micro sleep
                import time
                time.sleep(0.05)
                got_lock = bool(_redis.client.set(lock_key, str(user.id), nx=True, ex=QM_LOCK_TTL_SEC))
            if not got_lock:
                return ApiResponse(code=429, message='busy')
            ticket, pair, err = _try_match_locked(user, prefer)
        finally:
            if got_lock:
                try:
                    _redis.delKey(lock_key)
                except Exception:
                    pass
        if err == 'already_matched':
            return ApiResponse(data={
                'ticket': None,
                'pair': _serialize_pair(pair, user),
                'matched': True,
            }, message='already_matched')
        return ApiResponse(data={
            'ticket': _serialize_ticket(ticket),
            'pair': _serialize_pair(pair, user),
            'matched': bool(pair),
        }, message='ok', code=201 if (ticket or pair) else 200)

    @extend_schema(summary=_('取消排队'))
    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request):
        user = request.user
        app_id = user.app_id or 'spark_main'
        updated = QmTicket.objects.filter(
            user=user, app_id=app_id, status=QmTicket.STATUS_WAITING,
        ).update(status=QmTicket.STATUS_CANCELLED)
        return ApiResponse(data={'cancelled': updated}, message='ok')

    @extend_schema(summary=_('速配状态'))
    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        user = request.user
        app_id = user.app_id or 'spark_main'
        _expire_waiting_tickets(app_id)
        ticket = QmTicket.objects.filter(
            user=user, app_id=app_id, status=QmTicket.STATUS_WAITING,
        ).order_by('-id').first()
        pair = QmPair.objects.filter(
            Q(user_a=user) | Q(user_b=user),
            app_id=app_id, status=QmPair.STATUS_ACTIVE,
        ).select_related('user_a', 'user_b', 'conversation').order_by('-id').first()
        return ApiResponse(data={
            'ticket': _serialize_ticket(ticket),
            'pair': _serialize_pair(pair, user),
            'matched': bool(pair),
        }, message='ok')

    @extend_schema(summary=_('结束本次速配'))
    @action(detail=False, methods=['post'], url_path='leave')
    def leave(self, request):
        user = request.user
        app_id = user.app_id or 'spark_main'
        pair_id = request.data.get('pair_id')
        qs = QmPair.objects.filter(
            Q(user_a=user) | Q(user_b=user),
            app_id=app_id, status=QmPair.STATUS_ACTIVE,
        )
        if pair_id:
            qs = qs.filter(id=pair_id)
        pair = qs.order_by('-id').first()
        if not pair:
            return ApiResponse(message='not found', code=404)
        pair.status = QmPair.STATUS_ENDED
        pair.ended_at = timezone.now()
        pair.save(update_fields=['status', 'ended_at'])
        return ApiResponse(data={'pair_id': pair.id, 'status': pair.status}, message='ok')
