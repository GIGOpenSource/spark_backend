import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.rate_limit import rate_limit
from tools.spark_helpers import (
    blocked_ids, serialize_user_card, serialize_funnel_card,
    ensure_daily_likes, ensure_daily_superlike, ensure_daily_feed, consume_ledger, has_vip_at_least, active_boost,
    check_review_mode, get_discover_param, apply_user_filters, get_or_create_pair_match,
    live_match_filter, viewer_passes_audience, robot_funnel_qs,
    bump_card_impressions, bump_right_swipe, ensure_recommend_stat,
    get_funnel_abc_rule, pick_users_by_abc_mix, get_product_profile, list_active_ops_banners,
    serialize_match_messaging, reactivate_match_messaging, ensure_match_qa,
    viewer_origin, get_or_refresh_top_picks, next_top_picks_refresh_at, bump_boost_metric,
    check_feed_soft_cap,
)
from tools.push_service import notify_safe, EVENT_NEW_LIKE, EVENT_NEW_MATCH
from models.models import User, Swipe, Match, FunnelPool, Conversation, EntitlementLedger, BoostSession, Message, Compliment, SayHi

logger = logging.getLogger(__name__)


@extend_schema(tags=[_('推荐')])
class RecommendViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('推荐 Feed'))
    @action(detail=False, methods=['get'], url_path='feed')
    @rate_limit('recommend_feed', rate=3.0, capacity=15.0, by='user')
    def feed(self, request):
        user = request.user
        platform = request.query_params.get('platform', 'h5')
        package_name = request.query_params.get('package_name', 'app.spark')
        version = request.query_params.get('app_version', '1.0.0')
        if check_review_mode(user.app_id, platform, package_name, version):
            return ApiResponse(data={'list': [], 'review_mode': True}, message='ok')

        limit = int(request.query_params.get('limit', 20))
        product_profile = get_product_profile(user.app_id or 'spark_main')
        mode = (request.query_params.get('mode') or '').strip().lower()
        category = (request.query_params.get('category') or '').strip().lower()
        dating_mode = (request.query_params.get('dating_mode') or '').strip().lower()
        if dating_mode not in ('date', 'bff', 'bizz'):
            dating_mode = ''
        if not dating_mode and category in ('dating', 'date', 'bff', 'bizz', 'long_term', 'interests'):
            dating_mode = 'bff' if category == 'bff' else ('bizz' if category == 'bizz' else ('date' if category in ('dating', 'date') else ''))
        # Top Picks requires Gold+
        top_picks_mode = mode in ('top_picks', 'top-picks', 'best_bees', 'for_you')
        next_refresh_at = None
        if top_picks_mode and not has_vip_at_least(user, 'gold'):
            return ApiResponse(
                code=403, message='need_gold',
                data={
                    'need_vip': True, 'locked': True, 'list': [],
                    'next_refresh_at': next_top_picks_refresh_at().isoformat(),
                    'feed_mode': 'top_picks',
                },
            )
        # 她说：每日21人只约束「推荐」；探索不消耗、不被截断
        cap_cfg = product_profile.get('daily_feed_cap')
        apply_daily_cap = bool(cap_cfg) and mode not in ('explore', 'fun', 'top_picks', 'top-picks', 'best_bees', 'campus', 'select', 'f2f')
        feed_ledger = ensure_daily_feed(user) if cap_cfg else None
        daily_feed_left = int(feed_ledger.balance) if feed_ledger is not None else None
        daily_feed_cap = int(cap_cfg) if cap_cfg else None
        if apply_daily_cap and daily_feed_left is not None:
            limit = min(limit, daily_feed_left)

        # F-13: soft fatigue for shells without hard daily_feed_cap
        soft_ok, soft_left, soft_limit = True, None, None
        if not cap_cfg and mode not in ('explore', 'fun', 'top_picks', 'top-picks', 'best_bees', 'campus', 'select', 'f2f'):
            soft_ok, soft_left, soft_limit = check_feed_soft_cap(user, bump=False)
            if not soft_ok:
                daily = ensure_daily_likes(user)
                daily_left = None if has_vip_at_least(user, 'plus') else daily.balance
                return ApiResponse(data={
                    'list': [],
                    'review_mode': False,
                    'boost_active': bool(active_boost(user)),
                    'passport_city': user.passport_city or '',
                    'passport_lat': getattr(user, 'passport_lat', None),
                    'passport_lng': getattr(user, 'passport_lng', None),
                    'daily_like_left': daily_left,
                    'daily_feed_cap': soft_limit,
                    'daily_feed_left': 0,
                    'feed_mode': mode or 'recommend',
                    'next_refresh_at': None,
                    'banners': list_active_ops_banners(user.app_id or 'spark_main'),
                    'ops_banners': list_active_ops_banners(user.app_id or 'spark_main'),
                    'refresh_at_hint': 'tomorrow',
                    'feed_soft_cap': True,
                    'vip_feed_bonus': product_profile.get('daily_feed_vip_bonus') or {},
                }, message='ok')
            if soft_left is not None:
                limit = min(limit, soft_left)

        cards = []
        if apply_daily_cap and daily_feed_left == 0:
            daily = ensure_daily_likes(user)
            daily_left = None if has_vip_at_least(user, 'plus') else daily.balance
            return ApiResponse(data={
                'list': [],
                'review_mode': False,
                'boost_active': bool(active_boost(user)),
                'passport_city': user.passport_city or '',
                'passport_lat': getattr(user, 'passport_lat', None),
                'passport_lng': getattr(user, 'passport_lng', None),
                'daily_like_left': daily_left,
                'daily_feed_cap': daily_feed_cap,
                'daily_feed_left': 0,
                'feed_mode': mode or 'recommend',
                'next_refresh_at': None,
                'banners': list_active_ops_banners(user.app_id or 'spark_main'),
                'ops_banners': list_active_ops_banners(user.app_id or 'spark_main'),
                'refresh_at_hint': 'tomorrow',
                'vip_feed_bonus': product_profile.get('daily_feed_vip_bonus') or {},
            }, message='ok')

        if not user.has_recharged:
            # Unpaid: robot card feed
            pool = robot_funnel_qs(
                user.app_id, user.country or '*', locale=getattr(user, 'locale', None) or 'en',
            )[:limit]
            cards = [serialize_funnel_card(i) for i in pool]
        else:
            # Paid: real users mixed by recommend-rule A/B/C share; shortfall filled randomly
            exclude = blocked_ids(user)
            exclude.add(user.id)
            # Only exclude recent swipes (90d) so older passes can resurface
            swiped = set(Swipe.objects.filter(
                actor=user, is_undone=False,
                created_at__gte=timezone.now() - timedelta(days=90),
            ).values_list('target_id', flat=True))
            exclude |= swiped
            qs = User.objects.filter(
                role='user', status=1, profile_complete=True, invisible_mode=False,
                discovery_enabled=True,
            ).exclude(id__in=exclude)
            profile = get_product_profile(user.app_id or 'spark_main')
            if profile.get('feed_same_app_only', True):
                qs = qs.filter(app_id=user.app_id or 'spark_main')
            try:
                filters = user.filters
            except Exception:
                filters = None
            qs = apply_user_filters(qs, filters, viewer=user)
            if dating_mode:
                same_mode = qs.filter(
                    Q(looking_for_intent=dating_mode) | Q(lifestyle__contains={'dating_mode': dating_mode})
                )
                if same_mode.exists():
                    qs = same_mode
            if category == 'interests' and (user.interests or []):
                # Prefer users sharing at least one interest (JSON contains any is awkward; filter in python later)
                pass
            if mode == 'campus' and getattr(user, 'school', None):
                qs = qs.filter(school__iexact=user.school)
            # Passport: prefer lat/lng bbox around destination; fallback city string
            if getattr(user, 'is_traveling', False):
                olat, olng = viewer_origin(user)
                if olat is not None and olng is not None and not (getattr(user, 'global_mode', False) and has_vip_at_least(user, 'plus')):
                    deg = 50.0 / 111.0  # ~50km travel radius default
                    try:
                        if filters and filters.distance_km:
                            deg = float(filters.distance_km) / 111.0
                    except Exception:
                        pass
                    qs = qs.filter(
                        lat__isnull=False, lng__isnull=False,
                        lat__gte=olat - deg, lat__lte=olat + deg,
                        lng__gte=olng - deg, lng__lte=olng + deg,
                    )
                else:
                    passport = (user.passport_city or '').strip()
                    if passport:
                        # B-06: exact / iexact first; avoid leading-wildcard icontains when possible
                        exact = qs.filter(
                            Q(city__iexact=passport) | Q(passport_city__iexact=passport)
                        )
                        if exact.exists():
                            qs = exact
                        else:
                            starts = qs.filter(
                                Q(city__istartswith=passport) | Q(passport_city__istartswith=passport)
                            )
                            if starts.exists():
                                qs = starts
                            else:
                                qs = qs.filter(
                                    Q(city__icontains=passport) | Q(passport_city__icontains=passport)
                                )
            recommend_type = (filters.recommend_type if filters else None) or 'precise'
            if mode in ('explore', 'fun'):
                recommend_type = 'fun'
            elif top_picks_mode:
                recommend_type = 'precise'
            app_scope = user.app_id or 'spark_main'
            # B-05: if maintenance precomputed candidates, prefer that id set
            try:
                import json
                from tools.spark_helpers import _cfg_redis
                r = _cfg_redis()
                raw_cand = r.getKey(f'feed_cand:{app_scope}') if r else None
                if raw_cand:
                    cand_ids = json.loads(raw_cand)
                    if isinstance(cand_ids, list) and cand_ids:
                        preferred = qs.filter(id__in=cand_ids)
                        if preferred.exists():
                            qs = preferred
            except Exception:
                pass
            boosted_ids = list(BoostSession.objects.filter(
                is_active=True, end_at__gt=timezone.now(),
                user__app_id=app_scope,
            ).values_list('user_id', flat=True))
            # Priority Likes: people who Priority-liked YOU bubble to your feed (any tier)
            priority_ids = list(Swipe.objects.filter(
                target=user, is_undone=False, is_priority=True,
                action__in=('like', 'super_like'),
                created_at__gte=timezone.now() - timedelta(days=14),
            ).values_list('actor_id', flat=True)[:limit])
            boosted = list(
                qs.filter(id__in=boosted_ids)
                .select_related('recommend_stat')
                .prefetch_related('photos')[:limit]
            )
            rest_qs = qs.exclude(id__in=boosted_ids)
            pool_size = max(limit * 3, 40)
            candidates = list(
                rest_qs.select_related('recommend_stat').prefetch_related('photos')[:pool_size]
            )
            if category == 'interests' and (user.interests or []):
                my_set = set(user.interests or [])
                candidates = sorted(
                    candidates,
                    key=lambda u: -len(my_set.intersection(set(u.interests or []))),
                )
            if recommend_type in ('explore', 'fun') and category != 'interests':
                import random
                random.shuffle(candidates)
            if top_picks_mode:
                def _grade_rank(u):
                    try:
                        g = (u.recommend_stat.grade or 'C').upper()
                    except Exception:
                        g = 'C'
                    return 0 if g == 'A' else (1 if g == 'B' else 2)
                candidates = sorted(candidates, key=_grade_rank)
                pick_ids, next_refresh_at = get_or_refresh_top_picks(
                    user, [u.id for u in candidates], limit=limit,
                )
                id_map = {u.id: u for u in candidates}
                rest = [id_map[i] for i in pick_ids if i in id_map]
                if len(rest) < limit:
                    for u in candidates:
                        if u.id not in pick_ids:
                            rest.append(u)
                        if len(rest) >= limit:
                            break
            else:
                rule = get_funnel_abc_rule(
                    user.app_id, user.country or '*', getattr(user, 'locale', None) or '*',
                )
                if rule:
                    rest = pick_users_by_abc_mix(
                        candidates, limit,
                        a_percent=rule.a_percent,
                        b_percent=rule.b_percent,
                        c_percent=rule.c_percent,
                    )
                else:
                    import random
                    random.shuffle(candidates)
                    rest = candidates[:limit]
            if priority_ids:
                priority = list(
                    qs.filter(id__in=priority_ids).exclude(id__in=boosted_ids)
                    .select_related('recommend_stat')
                    .prefetch_related('photos')[:limit]
                )
                seen = set()
                ordered = []
                for u in priority + boosted + rest:
                    if u.id in seen:
                        continue
                    seen.add(u.id)
                    ordered.append(u)
                    if len(ordered) >= limit:
                        break
            else:
                ordered = (boosted + rest)[:limit]
            ordered = [u for u in ordered if viewer_passes_audience(u, user)][:limit]
            if len(ordered) < limit:
                import random
                seen = {u.id for u in ordered}
                leftovers = [u for u in candidates if u.id not in seen and viewer_passes_audience(u, user)]
                random.shuffle(leftovers)
                ordered.extend(leftovers[: limit - len(ordered)])
            # Rebuild ordered with photos/recommend_stat hydrated (guards mixed querysets)
            if ordered:
                hydrated = {
                    u.id: u for u in User.objects.filter(id__in=[u.id for u in ordered])
                    .prefetch_related('photos').select_related('recommend_stat')
                }
                ordered = [hydrated[u.id] for u in ordered if u.id in hydrated]
            priority_set = set(priority_ids)
            cards = []
            for u in ordered:
                card = serialize_user_card(u, viewer=user)
                try:
                    card['abc_grade'] = u.recommend_stat.grade
                except Exception:
                    card['abc_grade'] = ensure_recommend_stat(u).grade
                card['source'] = 'real'
                card['priority'] = u.id in priority_set
                cards.append(card)
            bump_card_impressions(ordered)

        boost = active_boost(user)
        daily = ensure_daily_likes(user)
        ensure_daily_superlike(user)
        daily_left = None if has_vip_at_least(user, 'plus') else daily.balance
        return ApiResponse(data={
            'list': cards,
            'daily_like_left': daily_left,
            'boost_active': bool(boost),
            'boost_end_at': boost.end_at.isoformat() if boost else None,
            'vip_tier': user.effective_vip,
            'passport_city': user.passport_city or '',
            'passport_lat': getattr(user, 'passport_lat', None),
            'passport_lng': getattr(user, 'passport_lng', None),
            'daily_feed_cap': daily_feed_cap,
            'daily_feed_left': daily_feed_left,
            'feed_mode': mode or 'recommend',
            'category': category or None,
            'dating_mode': dating_mode or None,
            'next_refresh_at': next_refresh_at.isoformat() if next_refresh_at else (
                next_top_picks_refresh_at().isoformat() if top_picks_mode else None
            ),
            'explore_categories': [
                {'key': 'dating', 'label': 'Dating'},
                {'key': 'bff', 'label': 'BFF'},
                {'key': 'interests', 'label': 'Interests'},
                {'key': 'bizz', 'label': 'Bizz'},
            ],
            'banners': list_active_ops_banners(user.app_id or 'spark_main'),
            'ops_banners': list_active_ops_banners(user.app_id or 'spark_main'),
        }, message='ok')

    @extend_schema(summary=_('划卡'))
    @action(detail=False, methods=['post'], url_path='swipe')
    @rate_limit('recommend_swipe', rate=5.0, capacity=25.0, by='user')
    def swipe(self, request):
        user = request.user
        target_id = request.data.get('target_id')
        action_name = request.data.get('action')  # like / pass / super_like
        feed_mode = (request.data.get('feed_mode') or 'recommend').strip().lower()
        if action_name not in ('like', 'pass', 'super_like'):
            return ApiResponse(message='invalid action', code=400)

        feed_left_after = None
        is_funnel = False
        target = None
        funnel = None
        if isinstance(target_id, str) and str(target_id).startswith('funnel_'):
            is_funnel = True
            funnel_id = int(str(target_id).replace('funnel_', ''))
            funnel = FunnelPool.objects.filter(id=funnel_id).first()
            if not funnel:
                return ApiResponse(message='not found', code=404)
            if funnel.linked_user_id:
                target = funnel.linked_user
        else:
            try:
                target = User.objects.get(id=int(target_id))
            except (User.DoesNotExist, TypeError, ValueError):
                return ApiResponse(message='not found', code=404)

        if target:
            # Same-app gate (both None counts as same)
            if (user.app_id or None) != (target.app_id or None):
                return ApiResponse(code=403, message='cross_app')
            if target.status != 1:
                return ApiResponse(code=403, message='target_unavailable')
            if not target.profile_complete:
                return ApiResponse(code=400, message='target_incomplete')
            if target.id in blocked_ids(user):
                return ApiResponse(code=403, message='blocked')

        # Gates before any ledger/feed consume (W-02)
        if feed_mode in ('top_picks', 'top-picks', 'best_bees') and not has_vip_at_least(user, 'gold'):
            return ApiResponse(code=403, message='need_gold', data={'need_vip': True})

        # 推荐额度：仅 recommend 模式消耗每日 feed（探索不扣）；含 funnel/robot（W-07）
        consume_feed_quota = feed_mode not in ('explore', 'fun')
        feed_ledger = ensure_daily_feed(user) if consume_feed_quota else None
        if feed_ledger is not None and consume_feed_quota:
            if feed_ledger.balance < 1:
                return ApiResponse(
                    code=403, message='daily_feed_limit',
                    data={'daily_feed_left': 0, 'daily_feed_cap': feed_ledger.balance},
                )
            feed_ledger.balance -= 1
            feed_ledger.save(update_fields=['balance', 'updated_at'])
            feed_left_after = feed_ledger.balance
        elif consume_feed_quota and feed_ledger is None:
            # F-13 soft cap for shells without hard daily_feed_cap
            soft_ok, soft_left, soft_limit = check_feed_soft_cap(user, bump=True)
            if not soft_ok:
                return ApiResponse(
                    code=403, message='daily_feed_limit',
                    data={
                        'daily_feed_left': 0,
                        'daily_feed_cap': soft_limit,
                        'feed_soft_cap': True,
                        'refresh_at_hint': 'tomorrow',
                    },
                )
            feed_left_after = soft_left

        # Funnel without linked user: consume quotas then exit (no Swipe row)
        if is_funnel and target is None:
            if action_name == 'like' and not has_vip_at_least(user, 'plus'):
                ok, daily = consume_ledger(user, EntitlementLedger.DAILY_LIKE)
                if not ok:
                    return ApiResponse(code=403, message='daily_like_limit', data={'need_vip': True})
            if action_name == 'super_like':
                ok2, _ = consume_ledger(user, EntitlementLedger.SUPER_LIKE)
                if not ok2:
                    return ApiResponse(code=403, message='need_super_like', data={'need_shop': True})
            return ApiResponse(data={
                'matched': False, 'funnel': True,
                'daily_feed_left': feed_left_after,
            }, message='ok')

        # Plus+ = unlimited likes (Tinder Plus); free users burn daily_like
        unlimited_likes = has_vip_at_least(user, 'plus')
        if action_name == 'like' and not unlimited_likes:
            ok, daily = consume_ledger(user, EntitlementLedger.DAILY_LIKE)
            if not ok:
                return ApiResponse(code=403, message='daily_like_limit', data={'need_vip': True})
        if action_name == 'super_like':
            ok, _ = consume_ledger(user, EntitlementLedger.SUPER_LIKE)
            if not ok:
                return ApiResponse(code=403, message='need_super_like', data={'need_shop': True})

        want_priority = bool(request.data.get('priority')) and has_vip_at_least(user, 'platinum')
        # Platinum likes are Priority Likes by default when priority not explicitly false
        if request.data.get('priority') is None and has_vip_at_least(user, 'platinum') and action_name in ('like', 'super_like'):
            want_priority = True

        Swipe.objects.filter(actor=user, target=target, is_undone=False).update(is_undone=True)
        swipe = Swipe.objects.create(
            actor=user, target=target, action=action_name, is_priority=want_priority,
        )
        if action_name in ('like', 'super_like'):
            bump_right_swipe(target)

        matched = False
        match_data = None
        if action_name in ('like', 'super_like'):
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
                # Prefer attaching existing prematch conversation to avoid orphan threads
                pre = Conversation.objects.filter(match__isnull=True).filter(
                    Q(user_a_id=a, user_b_id=b) | Q(user_a_id=b, user_b_id=a)
                ).first()
                conv = Conversation.objects.filter(match=match).first()
                if pre and conv and pre.id != conv.id:
                    Message.objects.filter(conversation=pre).update(conversation=conv)
                    if pre.last_at and (not conv.last_at or pre.last_at > conv.last_at):
                        conv.last_message = pre.last_message
                        conv.last_at = pre.last_at
                        conv.save(update_fields=['last_message', 'last_at'])
                    pre.delete()
                elif pre and not conv:
                    pre.match = match
                    pre.save(update_fields=['match'])
                    conv = pre
                elif not conv:
                    conv = Conversation.objects.create(match=match, user_a_id=a, user_b_id=b)
                matched = True
                bump_boost_metric([user.id, target.id], 'matches', 1)
                match_data = {
                    'match_id': match.id,
                    'conversation_id': conv.id,
                    'user': serialize_user_card(target, viewer=user),
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
            'daily_like_left': None if has_vip_at_least(user, 'plus') else ensure_daily_likes(user).balance,
            'daily_feed_left': feed_left_after,
        }, message='ok')

    @extend_schema(summary=_('撤回上一张'))
    @action(detail=False, methods=['post'], url_path='rewind')
    def rewind(self, request):
        user = request.user
        # Gates before consume (W-02): nothing / already-matched must not burn rewind
        last = Swipe.objects.filter(actor=user, is_undone=False).order_by('-id').first()
        if not last:
            return ApiResponse(message='nothing to rewind', code=400)
        # Tinder: cannot rewind a swipe that already matched
        if last.action in ('like', 'super_like') and last.target_id:
            live = Match.objects.filter(
                Q(user_a=user, user_b_id=last.target_id) | Q(user_a_id=last.target_id, user_b=user),
            ).filter(live_match_filter()).exists()
            if live:
                return ApiResponse(code=400, message='cannot_rewind_match')
        # Plus+ = unlimited rewind; otherwise consume rewind pack
        if not has_vip_at_least(user, 'plus'):
            ok, _ = consume_ledger(user, EntitlementLedger.REWIND)
            if not ok:
                return ApiResponse(code=403, message='need_rewind', data={'need_shop': True, 'need_vip': True})
        last.is_undone = True
        last.save(update_fields=['is_undone'])
        return ApiResponse(data={'rewound_target_id': last.target_id}, message='ok')
