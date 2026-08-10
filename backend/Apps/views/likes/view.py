from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.spark_helpers import (
    serialize_user_card, serialize_funnel_card, has_vip_at_least, get_discover_param,
    live_match_filter, blocked_ids, get_product_profile, consume_ledger, bump_right_swipe,
    get_or_create_pair_match, serialize_match_messaging, ensure_match_qa, reactivate_match_messaging,
    grant_ledger,
)
from tools.push_service import notify_safe, EVENT_NEW_LIKE, EVENT_NEW_MATCH
from models.models import Swipe, SayHi, Match, Conversation, User, Message, Compliment, EntitlementLedger, LikeUnlock


@extend_schema(tags=[_('喜欢')])
class LikesViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('谁喜欢我'))
    @action(detail=False, methods=['get'], url_path='received')
    def received(self, request):
        user = request.user
        gold = has_vip_at_least(user, 'gold')
        sort = (request.query_params.get('sort') or 'all').lower()
        if sort not in ('nearby', 'common', 'new', 'all', 'super'):
            return ApiResponse(code=400, message='invalid sort')
        blocked = blocked_ids(user)
        like_cutoff = timezone.now() - timedelta(days=14)
        likes = Swipe.objects.filter(
            target=user, is_undone=False, action__in=('like', 'super_like'),
            created_at__gte=like_cutoff,
        ).select_related('actor')
        if sort == 'super':
            likes = likes.filter(action='super_like')
        likes = likes.order_by('-created_at', '-id')[:100]
        unlocked_ids = set(LikeUnlock.objects.filter(user=user).values_list('swipe_id', flat=True))
        # exclude already matched (live only)
        matched_ids = set()
        for m in Match.objects.filter(Q(user_a=user) | Q(user_b=user)).filter(live_match_filter()):
            matched_ids.add(m.user_b_id if m.user_a_id == user.id else m.user_a_id)
        items = []
        for s in likes:
            if s.actor_id in matched_ids or s.actor_id in blocked:
                continue
            card = serialize_user_card(s.actor, blur=not (gold or s.id in unlocked_ids))
            card['swipe_id'] = s.id
            card['action'] = s.action
            if s.action == 'super_like':
                comp = Compliment.objects.filter(
                    sender_id=s.actor_id, receiver=user, status__in=('pending', 'matched'),
                ).order_by('-id').first()
                if comp:
                    card['compliment_message'] = comp.message
                    card['compliment_photo'] = comp.photo_url
            items.append(card)
        if sort == 'nearby' and user.lat is not None and user.lng is not None:
            def distance(item):
                lat, lng = item.get('lat'), item.get('lng')
                if lat is None or lng is None:
                    return float('inf')
                return (float(lat) - user.lat) ** 2 + (float(lng) - user.lng) ** 2
            items.sort(key=distance)
        elif sort == 'common':
            interests = set(user.interests or [])
            items.sort(key=lambda item: len(interests.intersection(item.get('interests') or [])), reverse=True)

        # Robot fillers for non-gold after threshold (client blurs locked likes)
        if not gold:
            param = get_discover_param(user.app_id, user.country or '*')
            threshold = int(getattr(param, 'like_bonus_threshold', 0) or 0)
            real_like_count = len(items)
            if real_like_count >= threshold:
                from tools.spark_helpers import robot_funnel_qs
                bonus = robot_funnel_qs(
                    user.app_id, user.country or '*',
                    locale=getattr(user, 'locale', None) or 'en',
                )[:param.like_bonus_count]
                for f in bonus:
                    items.append(serialize_funnel_card(f, blur=True))

        return ApiResponse(data={
            'list': items,
            'count': len(items),
            'unlocked': gold,
            'unlocked_ids': list(unlocked_ids),
        }, message='ok')

    @extend_schema(summary=_('解锁一条喜欢'))
    @action(detail=False, methods=['post'], url_path='unlock')
    def unlock(self, request):
        user = request.user
        try:
            swipe = Swipe.objects.get(
                id=int(request.data.get('swipe_id')), target=user, is_undone=False,
                action__in=('like', 'super_like'),
            )
        except (Swipe.DoesNotExist, TypeError, ValueError):
            return ApiResponse(code=404, message='not found')
        # W-03: consume before create so concurrent loser cannot unlock free / delete after consume
        gold = has_vip_at_least(user, 'gold')
        with transaction.atomic():
            existing = (
                LikeUnlock.objects.select_for_update()
                .filter(user=user, swipe=swipe)
                .first()
            )
            if existing:
                return ApiResponse(
                    data={'swipe_id': swipe.id, 'unlocked': True, 'created': False},
                    message='ok',
                )
            if not gold:
                ok, _ = consume_ledger(user, EntitlementLedger.LIKES_UNLOCK)
                if not ok:
                    return ApiResponse(code=403, message='need_likes_unlock', data={'need_shop': True})
            try:
                LikeUnlock.objects.create(user=user, swipe=swipe)
                created = True
            except IntegrityError:
                # Concurrent winner already unlocked; refund if we consumed
                if not gold:
                    grant_ledger(user, EntitlementLedger.LIKES_UNLOCK, 1, period_key='purchased')
                created = False
        return ApiResponse(data={'swipe_id': swipe.id, 'unlocked': True, 'created': created}, message='ok')

    @extend_schema(summary=_('我喜欢过的'))
    @action(detail=False, methods=['get'], url_path='sent')
    def sent(self, request):
        user = request.user
        blocked = blocked_ids(user)
        likes = list(Swipe.objects.filter(
            actor=user, is_undone=False, action__in=('like', 'super_like'),
        ).select_related('target').prefetch_related('target__photos').order_by('-id')[:50])
        matches = {
            (m.user_b_id if m.user_a_id == user.id else m.user_a_id): m
            for m in Match.objects.filter(Q(user_a=user) | Q(user_b=user)).filter(live_match_filter())
        }
        match_ids = [m.id for m in matches.values()]
        conv_by_match = {
            c.match_id: c
            for c in Conversation.objects.filter(match_id__in=match_ids)
        } if match_ids else {}

        target_ids = [s.target_id for s in likes if s.target_id not in blocked and s.target_id not in matches]
        past_peer_ids = set()
        if target_ids:
            for a, b in Match.objects.filter(
                Q(user_a=user, user_b_id__in=target_ids) | Q(user_b=user, user_a_id__in=target_ids),
            ).filter(
                Q(status__in=('expired', 'ended'))
                | (Q(status='active') & Q(expire_at__lt=timezone.now()))
            ).values_list('user_a_id', 'user_b_id'):
                past_peer_ids.add(b if a == user.id else a)

        now = timezone.now()
        items = []
        for s in likes:
            if s.target_id in blocked:
                continue
            card = serialize_user_card(s.target)
            card['action'] = s.action
            card['swipe_id'] = s.id
            m = matches.get(s.target_id)
            if m:
                card['is_matched'] = True
                card['match_id'] = m.id
                card['status'] = 'matched'
                conv = conv_by_match.get(m.id)
                card['conversation_id'] = conv.id if conv else None
            else:
                card['is_matched'] = False
                card['match_id'] = None
                card['conversation_id'] = None
                card['status'] = 'waiting'
                past = s.target_id in past_peer_ids
                if past or (s.created_at and now - s.created_at > timedelta(days=14)):
                    card['status'] = 'expired'
            items.append(card)
        return ApiResponse(data={'list': items}, message='ok')

    @extend_schema(summary=_('Say Hi'))
    @action(detail=False, methods=['post'], url_path='say-hi')
    def say_hi(self, request):
        user = request.user
        profile = get_product_profile(user.app_id or 'spark_main')
        # 她说：禁止 Say Hi 绕过「女问男答再开聊」
        if profile.get('messaging_mode') == 'qa_gate' or profile.get('qa_gate_enabled'):
            return ApiResponse(code=400, message='qa_gate_no_say_hi')
        target_id = request.data.get('target_id')
        message = request.data.get('message') or 'Hi!'
        try:
            target = User.objects.get(id=int(target_id))
        except (User.DoesNotExist, TypeError, ValueError):
            return ApiResponse(message='not found', code=404)

        if target.app_id and user.app_id and target.app_id != user.app_id:
            return ApiResponse(code=403, message='cross_app')
        if target.id in blocked_ids(user):
            return ApiResponse(code=403, message='blocked')

        exists = Match.objects.filter(
            Q(user_a=user, user_b=target) | Q(user_a=target, user_b=user),
        ).filter(live_match_filter()).first()
        if exists:
            conv, _ = Conversation.objects.get_or_create(
                match=exists,
                defaults={'user_a': exists.user_a, 'user_b': exists.user_b},
            )
            return ApiResponse(data={'matched': True, 'conversation_id': conv.id}, message='ok')

        # Reciprocal like → create match (same as swipe path); no Platinum required
        reciprocal = Swipe.objects.filter(
            actor=target, target=user, is_undone=False, action__in=('like', 'super_like'),
            created_at__gte=timezone.now() - timedelta(days=14),
        ).exists()
        if reciprocal:
            param = get_discover_param(user.app_id, user.country or '*')
            a, b = sorted([user.id, target.id])
            match, created = get_or_create_pair_match(
                a, b, expire_days=param.match_expire_days, app_id=user.app_id,
            )
            if created or match.status != 'active' or (match.expire_at and match.expire_at < timezone.now()):
                reactivate_match_messaging(
                    match, user, target, app_id=user.app_id, expire_days=param.match_expire_days,
                )
            else:
                ensure_match_qa(match)
            Swipe.objects.filter(actor=user, target=target, is_undone=False).update(is_undone=True)
            Swipe.objects.create(actor=user, target=target, action='like')
            SayHi.objects.filter(
                Q(sender=user, receiver=target) | Q(sender=target, receiver=user),
                status='pending',
            ).update(status='matched')
            Compliment.objects.filter(
                Q(sender=user, receiver=target) | Q(sender=target, receiver=user),
                status='pending',
            ).update(status='matched')
            conv = Conversation.objects.filter(match=match).first()
            if not conv:
                pre = Conversation.objects.filter(match__isnull=True).filter(
                    Q(user_a_id=a, user_b_id=b) | Q(user_a_id=b, user_b_id=a)
                ).order_by('-id').first()
                if pre:
                    pre.match = match
                    pre.save(update_fields=['match'])
                    conv = pre
                else:
                    conv = Conversation.objects.create(match=match, user_a_id=a, user_b_id=b)
            notify_safe(target, EVENT_NEW_MATCH, {
                'nickname': user.nickname or user.username or '',
                'match_id': match.id,
                'conversation_id': conv.id,
                'from_user_id': user.id,
            })
            return ApiResponse(data={
                'matched': True,
                'match_id': match.id,
                'conversation_id': conv.id,
            }, message='ok', code=201)

        if not has_vip_at_least(user, 'platinum'):
            return ApiResponse(code=403, message='need_platinum', data={'need_vip': True})

        param = get_discover_param(user.app_id, user.country or '*')
        # expire old pending say-hi between pair
        SayHi.objects.filter(
            Q(sender=user, receiver=target) | Q(sender=target, receiver=user),
            status='pending',
        ).update(status='expired')
        sh = SayHi.objects.create(
            sender=user, receiver=target, message=message,
            expire_at=timezone.now() + timedelta(days=param.say_hi_expire_days),
        )
        # Prefer existing pair conversation (incl. prior match thread) to keep history
        a, b = sorted([user.id, target.id])
        conv = Conversation.objects.filter(
            Q(user_a_id=a, user_b_id=b) | Q(user_a_id=b, user_b_id=a)
        ).order_by('-id').first()
        if conv and conv.match_id:
            # detach from dead/expired match so thread becomes prematch again
            conv.match = None
            conv.save(update_fields=['match'])
        if not conv:
            conv = Conversation.objects.create(user_a_id=a, user_b_id=b, match=None)
        msg = Message.objects.create(
            conversation=conv, sender=user, content=message, msg_type='text',
        )
        conv.last_message = message
        conv.last_at = timezone.now()
        conv.save(update_fields=['last_message', 'last_at'])
        return ApiResponse(data={
            'say_hi_id': sh.id,
            'conversation_id': conv.id,
            'matched': False,
            'message_id': msg.id,
        }, message='ok', code=201)

    @extend_schema(summary=_('Bumble Compliment'))
    @action(detail=False, methods=['post'], url_path='compliment')
    def compliment(self, request):
        """Photo/bio compliment: consumes super_like + creates pending Compliment + swipe."""
        user = request.user
        profile = get_product_profile(user.app_id or 'spark_main')
        if not profile.get('compliment_enabled'):
            return ApiResponse(code=400, message='compliment_disabled')
        target_id = request.data.get('target_id')
        message = (request.data.get('message') or '').strip()
        photo_url = (request.data.get('photo_url') or '').strip() or None
        target_kind = (request.data.get('target_kind') or 'photo').strip() or 'photo'
        if not message:
            return ApiResponse(code=400, message='message required')
        if len(message) > 150:
            return ApiResponse(code=400, message='message too long')
        try:
            target = User.objects.get(id=int(target_id))
        except (User.DoesNotExist, TypeError, ValueError):
            return ApiResponse(message='not found', code=404)
        if target.id in blocked_ids(user):
            return ApiResponse(code=403, message='blocked')
        if target.app_id and user.app_id and target.app_id != user.app_id:
            return ApiResponse(code=403, message='cross_app')

        ok, _ = consume_ledger(user, EntitlementLedger.SUPER_LIKE)
        if not ok:
            return ApiResponse(code=403, message='need_super_like', data={'need_shop': True})

        Swipe.objects.filter(actor=user, target=target, is_undone=False).update(is_undone=True)
        swipe = Swipe.objects.create(actor=user, target=target, action='super_like')
        bump_right_swipe(target)
        Compliment.objects.create(
            sender=user,
            receiver=target,
            photo_url=photo_url,
            target_kind=target_kind[:32],
            message=message[:150],
            status='pending',
        )

        matched = False
        match_data = None
        reciprocal = Swipe.objects.filter(
            actor=target, target=user, is_undone=False, action__in=('like', 'super_like'),
            created_at__gte=timezone.now() - timedelta(days=14),
        ).exists()
        if reciprocal:
            param = get_discover_param(user.app_id, user.country or '*')
            a, b = sorted([user.id, target.id])
            match, created = get_or_create_pair_match(
                a, b, expire_days=param.match_expire_days, app_id=user.app_id,
            )
            stale = (
                created
                or match.status != 'active'
                or (match.expire_at and match.expire_at < timezone.now())
            )
            if stale:
                reactivate_match_messaging(
                    match, user, target, app_id=user.app_id, expire_days=param.match_expire_days,
                )
            else:
                ensure_match_qa(match)
            Compliment.objects.filter(
                Q(sender=user, receiver=target) | Q(sender=target, receiver=user),
                status='pending',
            ).update(status='matched')
            SayHi.objects.filter(
                Q(sender=user, receiver=target) | Q(sender=target, receiver=user),
                status='pending',
            ).update(status='matched')
            conv = Conversation.objects.filter(match=match).first()
            if not conv:
                pre = Conversation.objects.filter(match__isnull=True).filter(
                    Q(user_a_id=a, user_b_id=b) | Q(user_a_id=b, user_b_id=a)
                ).order_by('-id').first()
                if pre:
                    pre.match = match
                    pre.save(update_fields=['match'])
                    conv = pre
                else:
                    conv = Conversation.objects.create(match=match, user_a_id=a, user_b_id=b)
            matched = True
            match_data = {
                'match_id': match.id,
                'conversation_id': conv.id,
                'user': serialize_user_card(target),
                **serialize_match_messaging(match, user),
            }
            notify_safe(target, EVENT_NEW_MATCH, {
                'nickname': user.nickname or user.username or '',
                'match_id': match.id,
                'conversation_id': conv.id,
                'from_user_id': user.id,
            })
        else:
            notify_safe(target, EVENT_NEW_LIKE, {
                'nickname': user.nickname or user.username or '',
                'from_user_id': user.id,
            })

        return ApiResponse(data={
            'swipe_id': swipe.id,
            'matched': matched,
            'match': match_data,
            'compliment': True,
        }, message='ok', code=201)

    @extend_schema(summary=_('收到的 Compliment'))
    @action(detail=False, methods=['get'], url_path='compliments')
    def compliments_received(self, request):
        user = request.user
        gold = has_vip_at_least(user, 'gold')
        rows = Compliment.objects.filter(
            receiver=user, status='pending',
        ).select_related('sender').order_by('-id')[:50]
        items = []
        for c in rows:
            card = serialize_user_card(c.sender, blur=not gold)
            card['compliment_id'] = c.id
            card['compliment_message'] = c.message
            card['compliment_photo'] = c.photo_url
            card['action'] = 'super_like'
            items.append(card)
        return ApiResponse(data={'list': items, 'unlocked': gold}, message='ok')
