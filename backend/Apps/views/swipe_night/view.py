from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from models.models import SwipeNightPick, SwipeNightSession, User
from tools.permissions import IsTokenValid, RequireAppModule
from tools.spark_helpers import blocked_ids, get_or_create_pair_match, serialize_user_card
from tools.utils import ApiResponse


def _tonight(app_id):
    now = timezone.localtime()
    date = now.date() if now.time() < time(23, 0) else now.date() + timedelta(days=1)
    start = timezone.make_aware(datetime.combine(date, time(19, 0)))
    end = timezone.make_aware(datetime.combine(date, time(23, 0)))
    session, _ = SwipeNightSession.objects.get_or_create(
        app_id=app_id, starts_at=start, ends_at=end,
        defaults={'status': 'open'},
    )
    # Auto-close past windows
    if session.status == 'open' and session.ends_at and session.ends_at < timezone.now():
        session.status = 'closed'
        session.save(update_fields=['status'])
    return session


def settle_mutual_picks(session):
    """Create matches for mutual picks; return list of {match_id, user_a, user_b}."""
    picks = list(SwipeNightPick.objects.filter(session=session))
    by_actor = {}
    for p in picks:
        by_actor.setdefault(p.actor_id, set()).add(p.target_id)
    matched_pairs = set()
    results = []
    for actor_id, targets in by_actor.items():
        for tid in targets:
            pair = tuple(sorted((actor_id, tid)))
            if pair in matched_pairs:
                continue
            if actor_id in by_actor.get(tid, set()):
                matched_pairs.add(pair)
                match, created = get_or_create_pair_match(pair[0], pair[1], app_id=session.app_id)
                results.append({
                    'match_id': match.id,
                    'user_a': pair[0],
                    'user_b': pair[1],
                    'created': created,
                })
    return results


@extend_schema(tags=[_('Swipe Night')])
class SwipeNightViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        session = _tonight(request.user.app_id or 'spark_main')
        return ApiResponse(data={
            'id': session.id,
            'starts_at': session.starts_at.isoformat(),
            'ends_at': session.ends_at.isoformat(),
            'status': session.status,
        }, message='ok')

    @action(detail=False, methods=['get'], url_path='candidates')
    def candidates(self, request):
        user = request.user
        session = _tonight(user.app_id or 'spark_main')
        if session.status not in ('open',):
            return ApiResponse(code=400, message='session_not_open', data={'status': session.status})
        picked = SwipeNightPick.objects.filter(session=session, actor=user).values_list('target_id', flat=True)
        rows = User.objects.filter(app_id=user.app_id, discovery_enabled=True, status=1).exclude(
            id=user.id
        ).exclude(id__in=picked).exclude(id__in=blocked_ids(user)).order_by('-online_at', '-id')[:50]
        return ApiResponse(data={
            'session_id': session.id,
            'list': [serialize_user_card(row) for row in rows],
        }, message='ok')

    @action(detail=False, methods=['post'], url_path='pick')
    def pick(self, request):
        user = request.user
        session = _tonight(user.app_id or 'spark_main')
        if session.status != 'open':
            return ApiResponse(code=400, message='session_not_open')
        try:
            target = User.objects.get(id=int(request.data.get('target_id')), app_id=user.app_id, status=1)
        except (User.DoesNotExist, TypeError, ValueError):
            return ApiResponse(code=404, message='not found')
        if target.id == user.id or target.id in blocked_ids(user):
            return ApiResponse(code=403, message='blocked')
        pick, created = SwipeNightPick.objects.get_or_create(session=session, actor=user, target=target)
        return ApiResponse(data={
            'pick_id': pick.id, 'created': created, 'session_id': session.id,
        }, message='ok', code=201 if created else 200)

    @action(detail=False, methods=['post'], url_path='settle')
    def settle(self, request):
        user = request.user
        session = _tonight(user.app_id or 'spark_main')
        # Personal mutual matches involving this user
        matches = []
        picks = SwipeNightPick.objects.filter(session=session, actor=user).select_related('target')
        for pick in picks:
            if SwipeNightPick.objects.filter(session=session, actor=pick.target, target=user).exists():
                match, created = get_or_create_pair_match(user.id, pick.target_id, app_id=user.app_id)
                matches.append({'match_id': match.id, 'target_id': pick.target_id, 'created': created})
        # If window closed and not settled, settle whole session once
        if session.status == 'closed':
            all_matches = settle_mutual_picks(session)
            session.status = 'settled'
            session.save(update_fields=['status'])
            return ApiResponse(data={
                'session_id': session.id,
                'status': session.status,
                'matches': matches,
                'session_matches': all_matches,
            }, message='ok')
        return ApiResponse(data={'session_id': session.id, 'matches': matches}, message='ok')
