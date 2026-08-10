import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import F, FloatField, Q
from django.db.models.functions import Cast
from django.utils import timezone

from models.models import (
    User, UserPhoto, EntitlementLedger, FunnelPool, DiscoverParam,
    Block, Swipe, BoostSession, CountryConfig, AppConfig, ReviewMode, WordFilter,
    DomainWhitelist, Match, FunnelAbcRule, UserRecommendStat, MatchQA, Compliment,
)

logger = logging.getLogger(__name__)

_CONFIG_CACHE_TTL = 600  # 10 minutes
_PROFILE_VER_KEY = 'cfg:product_profile:ver'
_WORD_VER_KEY = 'cfg:wordfilter:ver'


def _cfg_redis():
    try:
        from tools.token_tools import _redis
        return _redis
    except Exception:
        return None


def bump_product_profile_cache():
    r = _cfg_redis()
    if not r:
        return
    try:
        r.client.incr(_PROFILE_VER_KEY)
    except Exception:
        logger.exception('bump_product_profile_cache failed')


def bump_wordfilter_cache():
    r = _cfg_redis()
    if not r:
        return
    try:
        r.client.incr(_WORD_VER_KEY)
    except Exception:
        logger.exception('bump_wordfilter_cache failed')


def period_day_key():
    return timezone.now().strftime('%Y-%m-%d')


def get_or_create_ledger(user, kind, period_key=None, default=0):
    obj, _ = EntitlementLedger.objects.get_or_create(
        user=user, kind=kind, period_key=period_key or '',
        defaults={'balance': default},
    )
    return obj


def ensure_daily_feed(user):
    """她说-style daily recommend card quota (e.g. 21). No-op if product has no cap.

    VIP add-on: product_profile.daily_feed_vip_bonus = {plus, gold, platinum}.
    If ledger already exists for today, top up when VIP bonus increases (W-08 / BE-025).
    """
    profile = get_product_profile(user.app_id or 'spark_main')
    cap = profile.get('daily_feed_cap')
    if not cap:
        return None
    cap = int(cap)
    bonus_map = profile.get('daily_feed_vip_bonus') or {
        'plus': 5, 'gold': 10, 'platinum': 21,
    }
    vip = getattr(user, 'effective_vip', None) or user.vip_tier or 'none'
    try:
        bonus = int(bonus_map.get(vip) or 0)
    except (TypeError, ValueError):
        bonus = 0
    target = cap + bonus
    key = period_day_key()
    obj, created = EntitlementLedger.objects.get_or_create(
        user=user, kind=EntitlementLedger.DAILY_FEED, period_key=key,
        defaults={'balance': target},
    )
    marker_pk = f'vip_feed_bonus:{key}'
    marker, _ = EntitlementLedger.objects.get_or_create(
        user=user, kind=EntitlementLedger.DAILY_FEED, period_key=marker_pk,
        defaults={'balance': bonus if created else 0},
    )
    if created:
        # Fresh ledger already includes today's VIP bonus in defaults
        if bonus and int(marker.balance or 0) != bonus:
            marker.balance = bonus
            marker.save(update_fields=['balance', 'updated_at'])
        return obj
    if bonus <= 0:
        return obj
    # Top-up VIP bonus if ledger was created before purchase / upgrade
    already = int(marker.balance or 0)
    delta = bonus - already
    if delta > 0:
        obj.balance = int(obj.balance or 0) + delta
        obj.save(update_fields=['balance', 'updated_at'])
        marker.balance = bonus
        marker.save(update_fields=['balance', 'updated_at'])
    return obj


FEED_SOFT_CAP_DEFAULT = 200


def check_feed_soft_cap(user, *, bump=False):
    """Soft daily feed fatigue for shells without hard daily_feed_cap (F-13).

    Redis counter ``feed_soft:{user_id}:{day}``; limit from product_profile.feed_soft_cap
    or default 200. MatchUp hard cap stays on ensure_daily_feed.
    Returns (ok, remaining, limit).
    """
    profile = get_product_profile(user.app_id or 'spark_main')
    if profile.get('daily_feed_cap'):
        return True, None, None
    try:
        limit = int(profile.get('feed_soft_cap') or FEED_SOFT_CAP_DEFAULT)
    except (TypeError, ValueError):
        limit = FEED_SOFT_CAP_DEFAULT
    if limit <= 0:
        return True, None, None
    day = period_day_key()
    key = f'feed_soft:{user.id}:{day}'
    r = _cfg_redis()
    count = 0
    if r:
        try:
            raw = r.getKey(key)
            count = int(raw or 0)
        except Exception:
            logger.exception('feed_soft_cap redis read failed')
            count = 0
    if count >= limit:
        return False, 0, limit
    if bump and r:
        try:
            count = int(r.client.incr(key))
            if count == 1:
                r.client.expire(key, 86400 * 2)
        except Exception:
            logger.exception('feed_soft_cap redis incr failed')
    remaining = max(0, limit - count)
    return True, remaining, limit


def top_up_daily_entitlements_after_vip(user):
    """After VIP purchase/upgrade: refresh today's feed (and likes) ledgers."""
    ensure_daily_feed(user)
    ensure_daily_likes(user)
    ensure_daily_superlike(user)


def ensure_daily_likes(user):
    key = period_day_key()
    param = get_discover_param(user.app_id, user.country or '*')
    return get_or_create_ledger(user, EntitlementLedger.DAILY_LIKE, key, param.daily_like_limit)


def ensure_daily_superlike(user):
    """Tinder-like: free users get 1 Super Like per calendar day (PRD C3 default)."""
    key = f'daily:{period_day_key()}'
    return get_or_create_ledger(user, EntitlementLedger.SUPER_LIKE, key, 1)


# Spendable pools (markers vip_* are not spendable)
_SPENDABLE_KEYS = ('', 'grant', 'purchased', 'all')


def _is_spendable_period(period_key):
    pk = period_key or ''
    if pk.startswith('vip_'):
        return False
    if pk.startswith('daily:'):
        return True
    return pk in _SPENDABLE_KEYS


def clear_vip_grant_balances(user):
    """VIP expired → clear subscription grants; keep purchased packs."""
    EntitlementLedger.objects.filter(
        user=user,
        kind__in=(EntitlementLedger.SUPER_LIKE, EntitlementLedger.BOOST, EntitlementLedger.REWIND),
        period_key='grant',
    ).update(balance=0)


def ensure_vip_grants_consistent(user):
    """Lazy clear grant pool when effective VIP is none (before cron)."""
    if getattr(user, 'effective_vip', 'none') == 'none':
        clear_vip_grant_balances(user)


def apply_vip_subscription_grants(user, tier=None):
    """Grant current-period Gold/Platinum allotment if markers allow (purchase / ops / cron)."""
    tier = tier or getattr(user, 'effective_vip', None) or user.vip_tier
    if tier not in ('gold', 'platinum'):
        return False, False
    sl_qty = 10 if tier == 'platinum' else 5
    boost_qty = 2 if tier == 'platinum' else 1
    now = timezone.now()
    y, w, _ = now.isocalendar()
    week = f'{y}-W{w:02d}'
    month = now.strftime('%Y-%m')
    granted_sl = False
    granted_boost = False
    sl_marker, _ = EntitlementLedger.objects.get_or_create(
        user=user, kind=EntitlementLedger.SUPER_LIKE, period_key=f'vip_sl:{week}',
        defaults={'balance': 0},
    )
    if sl_marker.balance == 0:
        grant_ledger(user, EntitlementLedger.SUPER_LIKE, sl_qty, period_key='grant')
        sl_marker.balance = sl_qty
        sl_marker.save(update_fields=['balance', 'updated_at'])
        granted_sl = True
    boost_marker, _ = EntitlementLedger.objects.get_or_create(
        user=user, kind=EntitlementLedger.BOOST, period_key=f'vip_boost:{month}',
        defaults={'balance': 0},
    )
    if boost_marker.balance == 0:
        grant_ledger(user, EntitlementLedger.BOOST, boost_qty, period_key='grant')
        boost_marker.balance = boost_qty
        boost_marker.save(update_fields=['balance', 'updated_at'])
        granted_boost = True
    return granted_sl, granted_boost


def spendable_balances(user):
    """Aggregate spendable Super Like / Boost / Rewind / Likes Unlock / Extend / Rematch (+ Hive packs)."""
    out = {
        EntitlementLedger.SUPER_LIKE: 0,
        EntitlementLedger.BOOST: 0,
        EntitlementLedger.REWIND: 0,
        EntitlementLedger.LIKES_UNLOCK: 0,
        EntitlementLedger.EXTEND: 0,
        EntitlementLedger.REMATCH: 0,
        EntitlementLedger.HIVE: 0,
        EntitlementLedger.CONNECT: 0,
        EntitlementLedger.DATE_NIGHT: 0,
    }
    ensure_vip_grants_consistent(user)
    ensure_daily_superlike(user)
    for r in EntitlementLedger.objects.filter(user=user, kind__in=list(out.keys())):
        if _is_spendable_period(r.period_key):
            out[r.kind] = out.get(r.kind, 0) + max(0, r.balance)
    return out


def vip_rank(tier):
    order = {'none': 0, 'plus': 1, 'gold': 2, 'platinum': 3}
    return order.get(tier or 'none', 0)


def has_vip_at_least(user, tier):
    return vip_rank(user.effective_vip) >= vip_rank(tier)


def get_discover_param(app_id, country='*'):
    obj = DiscoverParam.objects.filter(app_id=app_id, country=country).first()
    if obj:
        return obj
    obj = DiscoverParam.objects.filter(app_id=app_id, country='*').first()
    if obj:
        return obj
    return DiscoverParam.objects.create(app_id=app_id, country='*')


def get_effective_config(app_id, country='*'):
    base = {}
    app = AppConfig.objects.filter(app_id=app_id).first()
    if app and app.config:
        base.update(app.config)
    star = CountryConfig.objects.filter(app_id=app_id, country='*').first()
    if star and star.config:
        base.update(star.config)
    if country and country != '*':
        specific = CountryConfig.objects.filter(app_id=app_id, country=country).first()
        if specific and specific.config:
            base.update(specific.config)
    return base


def check_review_mode(app_id, platform, package_name, version):
    row = ReviewMode.objects.filter(
        app_id=app_id, platform=platform,
        package_name=package_name, version=version, enabled=True,
    ).first()
    return bool(row)


def message_contains_banned(app_id, text, country='*', user=None):
    """Return first banned word found in text (admin WordFilter + user blocked_words).

    O-12: kind='allow' whitelist words are stripped from the scrubbed copy before
    ban matching so benign phrases containing a banned substring are not false-hit.
    """
    if not text:
        return None
    lower = str(text).lower()
    scrubbed = lower
    for w in _cached_allow_words(app_id, country):
        if w:
            scrubbed = scrubbed.replace(str(w).lower(), ' ')
    words = _cached_ban_words(app_id, country)
    if user is not None:
        try:
            pref = user.safety_pref
            words = list(words) + list(pref.blocked_words or [])
        except Exception:
            pass
    for w in words:
        if w and str(w).lower() in scrubbed:
            return w
    return None


def _cached_wordfilter_words(app_id, country='*', kind='ban'):
    """Compiled WordFilter list cached in Redis TTL 10 min."""
    import json
    r = _cfg_redis()
    cache_key = None
    if r:
        try:
            ver = r.getKey(_WORD_VER_KEY) or '0'
            cache_key = f'cfg:wordfilter:{kind}:{app_id}:{country or "*"}:v{ver}'
            cached = r.getKey(cache_key)
            if cached is not None:
                return json.loads(cached)
        except Exception:
            logger.exception('wordfilter cache read failed')
    words = list(WordFilter.objects.filter(app_id=app_id, kind=kind).filter(
        Q(country='*') | Q(country=country or '*')
    ).values_list('word', flat=True))
    if r and cache_key:
        try:
            r.setKey(cache_key, json.dumps(words), ex=_CONFIG_CACHE_TTL)
        except Exception:
            logger.exception('wordfilter cache write failed')
    return words


def _cached_ban_words(app_id, country='*'):
    return _cached_wordfilter_words(app_id, country, kind='ban')


def _cached_allow_words(app_id, country='*'):
    return _cached_wordfilter_words(app_id, country, kind='allow')

def live_match_filter():
    """status=active and not soft-expired by expire_at.

    Note: opened chats (any message) should clear expire_at via chat send /
    maintenance; this Q alone does not subquery messages.
    """
    now = timezone.now()
    return Q(status='active') & (Q(expire_at__isnull=True) | Q(expire_at__gt=now))


def match_is_live(match):
    """PRD: active + (within expire_at OR already opened chat).

    Read-only: badges / list paths must not clear expire_at. Use
    clear_match_expire_if_opened on write paths (chat send, etc.).
    """
    if not match or match.status != 'active':
        return False
    now = timezone.now()
    if not match.expire_at or match.expire_at > now:
        return True
    from models.models import Conversation, Message
    conv = Conversation.objects.filter(match_id=match.id).first()
    if not conv:
        return False
    if conv.last_message or Message.objects.filter(conversation_id=conv.id).exists():
        return True
    return False


def clear_match_expire_if_opened(match):
    """已匹配已开聊 → 不过期; also stamp opened_at once."""
    if not match:
        return
    fields = []
    if match.opened_at is None:
        match.opened_at = timezone.now()
        fields.append('opened_at')
    if match.expire_at is not None:
        match.expire_at = None
        fields.append('expire_at')
    if fields:
        match.save(update_fields=fields)


DEFAULT_PRODUCT_PROFILES = {
    'spark_main': {
        'messaging_mode': 'any',
        'match_open_hours': None,
        'extend_enabled': False,
        'compliment_enabled': False,
        'feed_same_app_only': True,
        'display_tiers': {'plus': 'Plus', 'gold': 'Gold', 'platinum': 'Platinum'},
    },
    'swipe_main': {
        'messaging_mode': 'women_first',
        'match_open_hours': 24,
        'extend_enabled': True,
        'compliment_enabled': True,
        'feed_same_app_only': True,
        'display_tiers': {
            'plus': 'Premium',
            'gold': 'Premium+',
            'platinum': 'Premium+ Spotlight',
        },
    },
    'matchup_main': {
        'messaging_mode': 'qa_gate',
        'match_open_hours': 48,
        'extend_enabled': False,
        'compliment_enabled': False,
        'qa_gate_enabled': True,
        'daily_feed_cap': 21,
        'daily_feed_vip_bonus': {'plus': 5, 'gold': 10, 'platinum': 21},
        'daily_like_limit_hint': 30,  # display hint; real limit from DiscoverParam
        'pay_channel': 'cn',  # wechat / alipay — not IAP USD
        'social_providers': ['wechat', 'douyin', 'xiaohongshu'],
        'feed_same_app_only': True,
        'display_tiers': {
            'plus': '会员',
            'gold': '高级会员',
            'platinum': '至尊会员',
        },
        'ops_banners': [
            {
                'title': '今日推荐名额有限',
                'subtitle': '认真滑完 21 人，遇见更对的人',
                'deep_link': '/pages/discover/index',
                'source': 'official',
            },
            {
                'title': '安全约会小贴士',
                'subtitle': '首次见面选公共场所，守护彼此',
                'deep_link': '/pagesA/me/safety',
                'source': 'official',
            },
        ],
    },
    'ember_main': {
        'messaging_mode': 'any',
        'match_open_hours': None,
        'extend_enabled': False,
        'compliment_enabled': False,
        'feed_same_app_only': True,
        'display_tiers': {'plus': 'Plus', 'gold': 'Gold', 'platinum': 'Platinum'},
    },
    'flick_main': {
        'messaging_mode': 'any',
        'match_open_hours': None,
        'extend_enabled': False,
        'compliment_enabled': False,
        'feed_same_app_only': True,
        'display_tiers': {'plus': 'Plus', 'gold': 'Gold', 'platinum': 'Platinum'},
    },
}


def default_product_profile(app_id):
    return dict(DEFAULT_PRODUCT_PROFILES.get(app_id) or DEFAULT_PRODUCT_PROFILES['spark_main'])


def get_product_profile(app_id):
    """Merge AppConfig.config.product_profile over defaults (additive, never removes keys).

    Cached in Redis TTL 10 min; bump via bump_product_profile_cache / set_product_profile.
    """
    app_id = app_id or 'spark_main'
    r = _cfg_redis()
    cache_key = None
    if r:
        try:
            ver = r.getKey(_PROFILE_VER_KEY) or '0'
            cache_key = f'cfg:product_profile:{app_id}:v{ver}'
            cached = r.getKey(cache_key)
            if cached:
                import json
                return json.loads(cached)
        except Exception:
            logger.exception('get_product_profile cache read failed')

    profile = default_product_profile(app_id)
    app = AppConfig.objects.filter(app_id=app_id).first()
    if app and isinstance(app.config, dict):
        stored = app.config.get('product_profile') or {}
        if isinstance(stored, dict):
            for k, v in stored.items():
                if k == 'display_tiers' and isinstance(v, dict):
                    merged = dict(profile.get('display_tiers') or {})
                    merged.update(v)
                    profile['display_tiers'] = merged
                else:
                    profile[k] = v

    if r and cache_key:
        try:
            import json
            r.setKey(cache_key, json.dumps(profile), ex=_CONFIG_CACHE_TTL)
        except Exception:
            logger.exception('get_product_profile cache write failed')
    return profile


def list_active_ops_banners(app_id, placement='discover_home'):
    """DB OpsBanner first; fall back to product_profile.ops_banners."""
    now = timezone.now()
    try:
        from models.models import OpsBanner
        qs = OpsBanner.objects.filter(app_id=app_id, placement=placement, enabled=True)
        rows = []
        for b in qs.order_by('sort', 'id')[:20]:
            if b.starts_at and b.starts_at > now:
                continue
            if b.ends_at and b.ends_at < now:
                continue
            rows.append({
                'id': b.id,
                'title': b.title,
                'subtitle': b.subtitle,
                'banner_title': b.title,
                'banner_subtitle': b.subtitle,
                'image_url': b.image_url,
                'banner_url': b.image_url,
                'deep_link': b.deep_link,
                'url': b.deep_link,
                'placement': b.placement,
            })
        if rows:
            return rows
    except Exception:
        logger.exception('list_active_ops_banners failed')
    profile = get_product_profile(app_id)
    return list(profile.get('ops_banners') or [])


def validate_product_profile(data):
    """Lightweight coerce/validate for product_profile JSON (E-08).

    Returns (cleaned_dict, errors). Unknown keys are kept; known keys coerced.
    """
    if data is None:
        return {}, []
    if not isinstance(data, dict):
        return {}, ['product_profile must be an object']
    out = dict(data)
    errors = []
    bool_keys = (
        'extend_enabled', 'compliment_enabled', 'feed_same_app_only',
        'qa_gate_enabled',
    )
    for k in bool_keys:
        if k in out and out[k] is not None:
            out[k] = bool(out[k])
    int_keys = (
        'match_open_hours', 'daily_feed_cap', 'daily_like_limit_hint', 'feed_soft_cap',
    )
    for k in int_keys:
        if k not in out or out[k] is None or out[k] == '':
            continue
        try:
            out[k] = int(out[k])
        except (TypeError, ValueError):
            errors.append(f'{k} must be int')
            out.pop(k, None)
    if 'messaging_mode' in out and out['messaging_mode'] is not None:
        mode = str(out['messaging_mode']).strip()
        if mode not in ('any', 'women_first', 'qa_gate'):
            errors.append('messaging_mode invalid')
        else:
            out['messaging_mode'] = mode
    if 'display_tiers' in out and out['display_tiers'] is not None:
        if not isinstance(out['display_tiers'], dict):
            errors.append('display_tiers must be object')
            out.pop('display_tiers', None)
    if 'daily_feed_vip_bonus' in out and out['daily_feed_vip_bonus'] is not None:
        if not isinstance(out['daily_feed_vip_bonus'], dict):
            errors.append('daily_feed_vip_bonus must be object')
            out.pop('daily_feed_vip_bonus', None)
        else:
            cleaned = {}
            for tier, val in out['daily_feed_vip_bonus'].items():
                try:
                    cleaned[str(tier)] = int(val)
                except (TypeError, ValueError):
                    errors.append(f'daily_feed_vip_bonus.{tier} must be int')
            out['daily_feed_vip_bonus'] = cleaned
    if 'ops_banners' in out and out['ops_banners'] is not None:
        if not isinstance(out['ops_banners'], list):
            errors.append('ops_banners must be list')
            out.pop('ops_banners', None)
    if 'social_providers' in out and out['social_providers'] is not None:
        if not isinstance(out['social_providers'], list):
            errors.append('social_providers must be list')
            out.pop('social_providers', None)
    return out, errors


def set_product_profile(app_id, patch):
    """Upsert product_profile keys into AppConfig.config (create AppConfig if missing)."""
    cleaned, _errs = validate_product_profile(patch if isinstance(patch, dict) else {})
    app, _ = AppConfig.objects.get_or_create(
        app_id=app_id,
        defaults={'name': app_id, 'config': {}},
    )
    cfg = dict(app.config or {})
    current = dict(cfg.get('product_profile') or {})
    if isinstance(cleaned, dict):
        for k, v in cleaned.items():
            if k == 'display_tiers' and isinstance(v, dict):
                tiers = dict(current.get('display_tiers') or {})
                tiers.update(v)
                current['display_tiers'] = tiers
            else:
                current[k] = v
    cfg['product_profile'] = current
    app.config = cfg
    app.save(update_fields=['config'])
    bump_product_profile_cache()
    return get_product_profile(app_id)

def resolve_match_opener(user_a, user_b, messaging_mode):
    """Women-first: women-identifying opens vs men. Non-binary defaults to opener rights.

    Same-gender / two women-openers / unknown → any (both can message).
    Non-binary can opt out via lifestyle.women_first_role = man|receiver.
    """
    if messaging_mode not in (Match.MSG_WOMEN_FIRST, Match.MSG_QA_GATE):
        return Match.MSG_ANY, None

    def _is_women_identifying(u):
        g = (getattr(u, 'gender', None) or '').lower()
        if g in {'female', 'f', 'woman', '女', 'women'}:
            return True
        if g in {'other', 'nonbinary', 'non-binary', 'nb', '非二元'}:
            life = getattr(u, 'lifestyle', None) or {}
            pref = str(life.get('women_first_role') or life.get('opener_role') or '').lower()
            if pref in {'man', 'men', 'male', 'receiver', 'no', 'false', '0'}:
                return False
            return True
        return False

    def _is_men_identifying(u):
        g = (getattr(u, 'gender', None) or '').lower()
        if g in {'male', 'm', 'man', '男', 'men'}:
            return True
        if g in {'other', 'nonbinary', 'non-binary', 'nb', '非二元'}:
            life = getattr(u, 'lifestyle', None) or {}
            pref = str(life.get('women_first_role') or life.get('opener_role') or '').lower()
            return pref in {'man', 'men', 'male', 'receiver', 'no', 'false', '0'}
        return False

    a_w, b_w = _is_women_identifying(user_a), _is_women_identifying(user_b)
    a_m, b_m = _is_men_identifying(user_a), _is_men_identifying(user_b)
    mode = messaging_mode
    if a_w and b_m and not b_w:
        return mode, user_a
    if b_w and a_m and not a_w:
        return mode, user_b
    return Match.MSG_ANY, None


def match_expire_at_for_profile(profile, expire_days=7):
    hours = profile.get('match_open_hours')
    if hours:
        return timezone.now() + timedelta(hours=int(hours))
    return timezone.now() + timedelta(days=expire_days)


def ensure_match_qa(match):
    """Create/reset 她说 QA row when match is qa_gate and not yet opened."""
    if not match or match.messaging_mode != Match.MSG_QA_GATE:
        return None
    if match.opened_at is not None:
        return getattr(match, 'qa', None)
    asker = match.opener_user
    if not asker:
        return None
    answerer = match.user_b if match.user_a_id == asker.id else match.user_a
    qa, created = MatchQA.objects.get_or_create(
        match=match,
        defaults={
            'asker': asker,
            'answerer': answerer,
            'status': MatchQA.STATUS_NEED_QUESTION,
            'expire_at': match.expire_at,
        },
    )
    reset = False
    if not created and qa.status in (MatchQA.STATUS_REJECTED, MatchQA.STATUS_EXPIRED):
        qa.question = ''
        qa.answer = ''
        qa.status = MatchQA.STATUS_NEED_QUESTION
        qa.expire_at = match.expire_at
        qa.asker = asker
        qa.answerer = answerer
        qa.save()
        reset = True
    if created or reset:
        try:
            from tools.push_service import notify_safe, EVENT_QA_NEED_QUESTION
            peer = answerer
            nick = (peer.nickname if peer else '') or ''
            from models.models import Conversation
            conv = Conversation.objects.filter(match=match).first()
            link = f'/pagesA/chat/room?id={conv.id}' if conv else '/pages/chat/index'
            notify_safe(asker, EVENT_QA_NEED_QUESTION, {
                'nickname': nick,
                'match_id': match.id,
                'deep_link': link,
            })
        except Exception:
            pass
    return qa


def reactivate_match_messaging(match, user_a, user_b, app_id=None, expire_days=7):
    """Reset messaging window/opener/QA for a (re)activated match."""
    resolved_app = app_id or getattr(user_a, 'app_id', None) or getattr(user_b, 'app_id', None) or 'spark_main'
    profile = get_product_profile(resolved_app)
    mode, opener = resolve_match_opener(user_a, user_b, profile.get('messaging_mode') or Match.MSG_ANY)
    match.status = 'active'
    match.expire_at = match_expire_at_for_profile(profile, expire_days)
    match.messaging_mode = mode
    match.opener_user = opener
    match.opened_at = None
    match.extend_count = 0
    match.save(update_fields=[
        'status', 'expire_at', 'messaging_mode', 'opener_user', 'opened_at', 'extend_count',
    ])
    ensure_match_qa(match)
    return match


def get_or_create_pair_match(user_a_id, user_b_id, expire_days=7, app_id=None):
    """Idempotent pair match; collapses duplicate rows if any.

    When created, applies product_profile messaging_mode / opener / expire window.
    """
    a, b = sorted([int(user_a_id), int(user_b_id)])
    rows = list(Match.objects.filter(user_a_id=a, user_b_id=b).order_by('-id'))
    created = False
    if rows:
        match = rows[0]
        for dup in rows[1:]:
            if dup.status == 'active':
                dup.status = 'ended'
                dup.save(update_fields=['status'])
    else:
        ua = User.objects.filter(id=a).first()
        ub = User.objects.filter(id=b).first()
        resolved_app = app_id or (ua.app_id if ua else None) or (ub.app_id if ub else None) or 'spark_main'
        profile = get_product_profile(resolved_app)
        mode = profile.get('messaging_mode') or Match.MSG_ANY
        mode, opener = resolve_match_opener(ua, ub, mode) if ua and ub else (Match.MSG_ANY, None)
        match = Match.objects.create(
            user_a_id=a, user_b_id=b,
            status='active',
            expire_at=match_expire_at_for_profile(profile, expire_days),
            messaging_mode=mode,
            opener_user=opener,
        )
        created = True
        ensure_match_qa(match)
    return match, created


def mark_match_opened(match):
    """Alias used by chat after first successful message."""
    clear_match_expire_if_opened(match)


def can_user_open_chat(match, user):
    """Return (ok, error_code). Spark any-mode always ok once match is live."""
    if not match:
        return True, None
    if match.opened_at is not None:
        return True, None
    if match.messaging_mode == Match.MSG_QA_GATE:
        qa = getattr(match, 'qa', None)
        if qa is None:
            try:
                qa = MatchQA.objects.filter(match=match).first()
            except Exception:
                qa = None
        if not qa or qa.status != MatchQA.STATUS_APPROVED:
            return False, 'qa_gate_pending'
        return True, None
    if match.messaging_mode != Match.MSG_WOMEN_FIRST:
        return True, None
    if match.opener_user_id is None:
        return True, None
    if user.id == match.opener_user_id:
        return True, None
    return False, 'waiting_for_opener'


def serialize_qa(match, viewer):
    qa = getattr(match, 'qa', None)
    if qa is None:
        try:
            qa = MatchQA.objects.filter(match_id=match.id).first()
        except Exception:
            return None
    if not qa:
        return None
    return {
        'status': qa.status,
        'question': qa.question or '',
        'answer': qa.answer or '',
        'i_am_asker': viewer.id == qa.asker_id,
        'i_am_answerer': viewer.id == qa.answerer_id,
        'expire_at': qa.expire_at.isoformat() if qa.expire_at else None,
        'can_ask': viewer.id == qa.asker_id and qa.status == MatchQA.STATUS_NEED_QUESTION,
        'can_answer': viewer.id == qa.answerer_id and qa.status == MatchQA.STATUS_NEED_ANSWER,
        'can_review': viewer.id == qa.asker_id and qa.status == MatchQA.STATUS_NEED_REVIEW,
    }


def serialize_match_messaging(match, viewer):
    if not match:
        return {}
    waiting = (
        match.messaging_mode == Match.MSG_WOMEN_FIRST
        and match.opened_at is None
        and match.opener_user_id is not None
        and viewer.id != match.opener_user_id
    )
    i_am_opener = bool(match.opener_user_id and viewer.id == match.opener_user_id)
    qa = serialize_qa(match, viewer) if match.messaging_mode == Match.MSG_QA_GATE else None
    terminal = {MatchQA.STATUS_APPROVED, MatchQA.STATUS_REJECTED, MatchQA.STATUS_EXPIRED}
    qa_pending = bool(
        qa and qa.get('status') not in terminal and match.opened_at is None
        and match.status == 'active'
    )
    if match.messaging_mode == Match.MSG_QA_GATE:
        can_send = bool(match.opened_at) or bool(qa and qa.get('status') == MatchQA.STATUS_APPROVED)
        waiting = qa_pending and not (qa and (qa.get('can_ask') or qa.get('can_answer') or qa.get('can_review')))
    elif match.messaging_mode == Match.MSG_WOMEN_FIRST:
        can_send = not waiting
    else:
        can_send = True
    profile = get_product_profile(
        getattr(viewer, 'app_id', None)
        or (match.user_a.app_id if match.user_a_id else None)
        or 'spark_main'
    )
    hours = profile.get('match_open_hours')
    free_left = max(0, 1 - int(match.extend_count or 0))
    paid_left = 0
    try:
        paid_left = int(spendable_balances(viewer).get(EntitlementLedger.EXTEND, 0) or 0)
    except Exception:
        paid_left = 0
    can_extend = (
        bool(profile.get('extend_enabled'))
        and match.messaging_mode == Match.MSG_WOMEN_FIRST
        and match.opened_at is None
        and match.status == 'active'
        and i_am_opener
        and match.expire_at is not None
        and (free_left > 0 or paid_left > 0)
    )
    return {
        'messaging_mode': match.messaging_mode or Match.MSG_ANY,
        'opener_user_id': match.opener_user_id,
        'opened_at': match.opened_at.isoformat() if match.opened_at else None,
        'i_am_opener': i_am_opener,
        'waiting_for_opener': waiting,
        'can_send': can_send,
        'expire_at': match.expire_at.isoformat() if match.expire_at else None,
        'extend_count': match.extend_count or 0,
        'can_extend': can_extend,
        'extend_free_left': free_left,
        'extend_paid_left': paid_left,
        'match_open_hours': hours,
        'extend_enabled': bool(profile.get('extend_enabled')),
        'compliment_enabled': bool(profile.get('compliment_enabled')),
        'qa_gate_enabled': bool(profile.get('qa_gate_enabled') or match.messaging_mode == Match.MSG_QA_GATE),
        'qa_gate_pending': qa_pending if match.messaging_mode == Match.MSG_QA_GATE else False,
        'qa': qa,
    }


def extend_match_open_window(match, viewer):
    """Bumble-like: first Extend free; further Extends consume paid Extend packs."""
    if not match or not viewer:
        return False, 'not_found'
    profile = get_product_profile(viewer.app_id or 'spark_main')
    if not profile.get('extend_enabled'):
        return False, 'extend_disabled'
    if match.messaging_mode != Match.MSG_WOMEN_FIRST:
        return False, 'not_applicable'
    if match.opened_at is not None:
        return False, 'already_opened'
    if match.status != 'active':
        return False, 'match_ended'
    if match.opener_user_id and viewer.id != match.opener_user_id:
        return False, 'not_opener'
    used = int(match.extend_count or 0)
    if used >= 1:
        ok, _ = consume_ledger(viewer, EntitlementLedger.EXTEND)
        if not ok:
            return False, 'need_extend'
    hours = int(profile.get('match_open_hours') or 24)
    base = match.expire_at if match.expire_at and match.expire_at > timezone.now() else timezone.now()
    match.expire_at = base + timedelta(hours=hours)
    match.extend_count = used + 1
    match.save(update_fields=['expire_at', 'extend_count'])
    return True, None



def blocked_ids(user):
    a = set(Block.objects.filter(user=user).values_list('blocked_user_id', flat=True))
    b = set(Block.objects.filter(blocked_user=user).values_list('user_id', flat=True))
    return a | b


def serialize_photo_list(user, include_pending=False):
    qs = user.photos.all()
    if not include_pending:
        qs = qs.filter(audit_status='approved')
    return [
        {'id': p.id, 'url': p.url, 'sort_order': p.sort_order, 'audit_status': p.audit_status}
        for p in qs
    ]


def serialize_user_card(user, blur=False, include_pending_photos=False, viewer=None, origin=None):
    photos = serialize_photo_list(user, include_pending=include_pending_photos)
    if not photos and user.avatar_url:
        photos = [{'id': 0, 'url': user.avatar_url, 'sort_order': 0, 'audit_status': 'approved'}]
    hide_age = bool(getattr(user, 'hide_age', False))
    data = {
        'id': user.id,
        'nickname': user.nickname or user.username,
        'age': None if hide_age else user.age,
        'hide_age': hide_age,
        'job': user.job or '',
        'city': user.city or '',
        'bio': user.bio or '',
        'looking_for': user.looking_for or '',
        'looking_for_intent': getattr(user, 'looking_for_intent', None) or '',
        'is_verified': user.is_verified,
        'is_traveling': user.is_traveling,
        'is_online': user.is_online and not user.invisible_mode,
        'online_at': user.online_at.isoformat() if user.online_at else None,
        'active_bucket': active_bucket(user),
        'mbti': user.mbti or '',
        'zodiac': user.zodiac or '',
        'relationship': user.relationship or '',
        'orientation': getattr(user, 'orientation', None) or '',
        'pronouns': getattr(user, 'pronouns', None) or '',
        'school': getattr(user, 'school', None) or '',
        'interests': user.interests or [],
        'interest_votes': getattr(user, 'interest_votes', None) or {},
        'lifestyle': user.lifestyle or {},
        'social_links': user.social_links or {},
        'photos': photos,
        'avatar_url': user.avatar_url or (photos[0]['url'] if photos else ''),
        'vip_tier': user.effective_vip,
        'vip_expire_at': user.vip_expire_at.isoformat() if user.vip_expire_at else None,
        'invisible_mode': user.invisible_mode,
        'discovery_enabled': bool(getattr(user, 'discovery_enabled', True)),
        'global_mode': bool(getattr(user, 'global_mode', False)),
        'profile_complete': user.profile_complete,
        'has_recharged': user.has_recharged,
        'locale': user.locale,
        'passport_city': user.passport_city or '',
        'passport_lat': getattr(user, 'passport_lat', None),
        'passport_lng': getattr(user, 'passport_lng', None),
        'gender': user.gender or '',
        'lat': user.lat,
        'lng': user.lng,
        'country': user.country or '',
        'phone': getattr(user, 'phone', None) or '',
        'height_cm': getattr(user, 'height_cm', None),
        'languages': getattr(user, 'languages', None) or [],
        'invite_code': getattr(user, 'invite_code', None) or '',
        'login_type': getattr(user, 'login_type', None) or '',
        'distance_km': None,
        'priority': False,
        'common_interests': [],
    }
    if viewer is not None:
        a = set(viewer.interests or [])
        b = set(user.interests or [])
        data['common_interests'] = sorted(a & b)
    origin_lat, origin_lng = None, None
    if origin and len(origin) == 2:
        origin_lat, origin_lng = origin
    elif viewer is not None:
        if getattr(viewer, 'is_traveling', False) and getattr(viewer, 'passport_lat', None) is not None:
            origin_lat, origin_lng = viewer.passport_lat, viewer.passport_lng
        else:
            origin_lat, origin_lng = viewer.lat, viewer.lng
    if origin_lat is not None and origin_lng is not None and user.lat is not None and user.lng is not None:
        data['distance_km'] = round(haversine_km(origin_lat, origin_lng, user.lat, user.lng), 1)
    # Peer card: redact phone + precise coords (keep city / passport_city / distance_km)
    if viewer is not None and getattr(viewer, 'id', None) != getattr(user, 'id', None):
        data['phone'] = ''
        data['lat'] = None
        data['lng'] = None
    if blur:
        data['blur'] = True
        nick = data['nickname'] or ''
        data['nickname'] = (nick[:1] + '…') if nick else 'Liked you'
        for p in data['photos']:
            p['url'] = p['url']  # client applies blur CSS
    return data


def haversine_km(lat1, lng1, lat2, lng2):
    from math import radians, sin, cos, sqrt, atan2
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def active_bucket(user):
    """now | today | week | older — based on online_at."""
    if not user or not user.online_at:
        return 'older'
    if getattr(user, 'invisible_mode', False):
        return 'older'
    delta = timezone.now() - user.online_at
    secs = delta.total_seconds()
    if secs < 300:
        return 'now'
    if secs < 86400:
        return 'today'
    if secs < 7 * 86400:
        return 'week'
    return 'older'


def viewer_origin(viewer):
    """Coords used for distance / passport travel feed."""
    if not viewer:
        return None, None
    if getattr(viewer, 'is_traveling', False) and getattr(viewer, 'passport_lat', None) is not None:
        return viewer.passport_lat, viewer.passport_lng
    return viewer.lat, viewer.lng


def next_top_picks_refresh_at(now=None):
    now = now or timezone.now()
    # Refresh daily at 18:00 local (server TZ)
    today_refresh = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if now < today_refresh:
        return today_refresh
    return today_refresh + timedelta(days=1)


def get_or_refresh_top_picks(user, candidate_ids, limit=10):
    """Return (pick_ids, next_refresh_at) for Gold Top Picks."""
    from models.models import TopPicksSnapshot
    now = timezone.now()
    snap = TopPicksSnapshot.objects.filter(user=user, refresh_at__gt=now).order_by('-id').first()
    if snap and snap.pick_ids:
        return list(snap.pick_ids)[:limit], snap.refresh_at
    refresh_at = next_top_picks_refresh_at(now)
    picks = list(candidate_ids)[:limit]
    TopPicksSnapshot.objects.create(user=user, pick_ids=picks, refresh_at=refresh_at)
    return picks, refresh_at


def bump_boost_metric(user_ids, field='impressions', amount=1):
    if not user_ids:
        return
    qs = BoostSession.objects.filter(
        user_id__in=list(user_ids), is_active=True, end_at__gt=timezone.now(),
    )
    for s in qs:
        setattr(s, field, int(getattr(s, field, 0) or 0) + amount)
        s.save(update_fields=[field])


def _birthday_cutoff(age_years):
    today = timezone.now().date()
    try:
        return today.replace(year=today.year - age_years)
    except ValueError:
        return today.replace(year=today.year - age_years, month=2, day=28)


def apply_user_filters(qs, filters, viewer=None):
    """Apply UserFilter fields to a User queryset. Distance skipped when coords missing."""
    if not filters:
        return qs
    if filters.gender:
        qs = qs.filter(gender=filters.gender)
    if filters.age_min is not None:
        qs = qs.filter(Q(birthday__isnull=True) | Q(birthday__lte=_birthday_cutoff(int(filters.age_min))))
    if filters.age_max is not None:
        qs = qs.filter(Q(birthday__isnull=True) | Q(birthday__gte=_birthday_cutoff(int(filters.age_max) + 1)))
    if filters.relationship:
        qs = qs.filter(relationship=filters.relationship)
    if filters.zodiac:
        qs = qs.filter(zodiac=filters.zodiac)
    if filters.mbti:
        qs = qs.filter(mbti=filters.mbti)
    if filters.language:
        qs = qs.filter(locale=filters.language)
    if filters.education:
        qs = qs.filter(lifestyle__education=filters.education)
    # distance_km: only when both sides have coords; skipped for global_mode (Plus+)
    skip_distance = bool(viewer and getattr(viewer, 'global_mode', False) and has_vip_at_least(viewer, 'plus'))
    if (
        not skip_distance
        and viewer and filters.distance_km
    ):
        olat, olng = viewer_origin(viewer)
        if olat is not None and olng is not None:
            deg = float(filters.distance_km) / 111.0
            qs = qs.filter(
                lat__isnull=False, lng__isnull=False,
                lat__gte=olat - deg, lat__lte=olat + deg,
                lng__gte=olng - deg, lng__lte=olng + deg,
            )
    return qs


def viewer_passes_audience(candidate, viewer):
    """Tinder Gold「Only show me to people in my preferences」.

    When candidate.lifestyle.audience_strict and Gold+, viewer must match
    candidate's discovery filters (age / gender / language / distance).
    """
    if not candidate or not viewer:
        return True
    lifestyle = candidate.lifestyle or {}
    if not lifestyle.get('audience_strict'):
        return True
    if not has_vip_at_least(candidate, 'gold'):
        return True
    try:
        filters = candidate.filters
    except Exception:
        return True
    # gender preference of candidate
    if filters.gender and viewer.gender and filters.gender != viewer.gender:
        return False
    if viewer.birthday and filters.age_min is not None:
        from datetime import date
        today = date.today()
        age = today.year - viewer.birthday.year - (
            (today.month, today.day) < (viewer.birthday.month, viewer.birthday.day)
        )
        if age < int(filters.age_min) or age > int(filters.age_max or 99):
            return False
    if filters.language and viewer.locale and filters.language != viewer.locale:
        return False
    if (
        filters.distance_km
        and candidate.lat is not None and candidate.lng is not None
        and viewer.lat is not None and viewer.lng is not None
    ):
        deg = float(filters.distance_km) / 111.0
        if abs(viewer.lat - candidate.lat) > deg or abs(viewer.lng - candidate.lng) > deg:
            return False
    return True


def validate_social_links(app_id, links):
    """Return (ok, bad_key). Empty whitelist allows all (dev-friendly)."""
    if not links:
        return True, None
    domains = list(DomainWhitelist.objects.filter(app_id=app_id).values_list('domain', flat=True))
    if not domains:
        return True, None
    from urllib.parse import urlparse
    for key, raw in links.items():
        if not raw:
            continue
        value = str(raw).strip()
        # bare handles (@user / username) are allowed; only validate URL/domain forms
        if value.startswith('@') or ('.' not in value and '://' not in value):
            continue
        host = urlparse(value if '://' in value else f'https://{value}').hostname or ''
        host = host.lower()
        allowed = any(host == d.lower() or host.endswith('.' + d.lower()) for d in domains)
        if not allowed:
            return False, key
    return True, None


def serialize_funnel_card(item, blur=False):
    """Serialize a robot funnel card. blur is a client display flag (not a card type)."""
    if item.linked_user_id:
        data = serialize_user_card(item.linked_user, blur=blur)
        data['id'] = f'funnel_{item.id}'
        data['funnel_id'] = item.id
        data['source'] = 'robot'
        if blur:
            data['blur'] = True
        return data
    data = {
        'id': f'funnel_{item.id}',
        'funnel_id': item.id,
        'nickname': item.nickname,
        'age': item.age,
        'job': item.job or '',
        'city': item.city or '',
        'bio': item.bio or '',
        'looking_for': 'Someone sincere and gentle',
        'is_verified': item.is_verified,
        'is_traveling': item.is_traveling,
        'is_online': False,
        'mbti': item.mbti or '',
        'zodiac': item.zodiac or '',
        'relationship': item.relationship or '',
        'interests': item.tags or [],
        'lifestyle': {},
        'social_links': {},
        'photos': [{'id': i, 'url': u, 'sort_order': i} for i, u in enumerate(item.photo_urls or [])],
        'avatar_url': (item.photo_urls or [''])[0] if item.photo_urls else '',
        'vip_tier': 'none',
        'source': 'robot',
    }
    if blur:
        data['blur'] = True
    return data


def region_locale_matches(rule_country, rule_locale, country='*', locale='*'):
    """True if rule country/locale wildcards cover the request scope."""
    country = (country or '*').strip() or '*'
    locale = ((locale or '*').strip() or '*').lower()
    rc = (rule_country or '*').strip() or '*'
    rl = ((rule_locale or '*').strip() or '*').lower()
    country_ok = rc == '*' or rc.lower() == country.lower()
    locale_ok = rl == '*' or rl == locale
    return country_ok and locale_ok


def _config_match_rank(rule_country, rule_locale, priority=0):
    """Sort key: higher priority first; then more specific country/locale."""
    rc = (rule_country or '*').strip() or '*'
    rl = ((rule_locale or '*').strip() or '*').lower()
    specificity = (0 if rc == '*' else 2) + (0 if rl == '*' else 1)
    return (int(priority or 0), specificity)


def get_funnel_abc_rule(app_id, country='*', locale='*'):
    """
    Pick ABC rule by priority (larger wins) among country/locale matches.
    If nothing matches → None (caller should fully randomize feed mix).
    Equal priority: prefer more specific region/language.
    """
    rules = list(FunnelAbcRule.objects.filter(app_id=app_id))
    matched = [r for r in rules if region_locale_matches(r.country, r.locale, country, locale)]
    if not matched:
        return None
    matched.sort(
        key=lambda r: (_config_match_rank(r.country, r.locale, r.priority), r.id),
        reverse=True,
    )
    return matched[0]


def serialize_funnel_abc_rule(rule):
    return {
        'id': rule.id,
        'app_id': rule.app_id,
        'country': rule.country,
        'locale': rule.locale,
        'priority': int(getattr(rule, 'priority', 0) or 0),
        'a_percent': rule.a_percent,
        'b_percent': rule.b_percent,
        'c_percent': rule.c_percent,
        'updated_at': rule.updated_at.isoformat() if rule.updated_at else None,
    }


def ensure_recommend_stat(user):
    stat, _ = UserRecommendStat.objects.get_or_create(
        user=user,
        defaults={'app_id': user.app_id or 'spark_main'},
    )
    return stat


def bump_card_impressions(users):
    """Increment impression_count when cards are shown in feed; bump active boosts."""
    boosted_ids = []
    user_by_id = {}
    for u in users:
        if not u or not getattr(u, 'id', None):
            continue
        if not isinstance(u, User):
            continue
        if getattr(u, 'role', 'user') != 'user':
            continue
        boosted_ids.append(u.id)
        user_by_id[u.id] = u
    if not boosted_ids:
        return
    unique_ids = list(user_by_id.keys())
    existing = set(
        UserRecommendStat.objects.filter(user_id__in=unique_ids).values_list('user_id', flat=True)
    )
    missing = [uid for uid in unique_ids if uid not in existing]
    if missing:
        UserRecommendStat.objects.bulk_create(
            [
                UserRecommendStat(
                    user_id=uid,
                    app_id=getattr(user_by_id[uid], 'app_id', None) or 'spark_main',
                )
                for uid in missing
            ],
            ignore_conflicts=True,
        )
    now = timezone.now()
    UserRecommendStat.objects.filter(user_id__in=unique_ids).update(
        impression_count=F('impression_count') + 1,
        updated_at=now,
    )
    UserRecommendStat.objects.filter(user_id__in=unique_ids, impression_count__gt=0).update(
        rate=Cast(F('right_swipe_count'), FloatField()) / Cast(F('impression_count'), FloatField()),
    )
    bump_boost_metric(boosted_ids, 'impressions', 1)


def bump_right_swipe(target_user):
    if not target_user or getattr(target_user, 'role', 'user') != 'user':
        return
    stat = ensure_recommend_stat(target_user)
    stat.right_swipe_count = int(stat.right_swipe_count or 0) + 1
    if stat.impression_count > 0:
        stat.rate = float(stat.right_swipe_count) / float(stat.impression_count)
    else:
        stat.rate = float(stat.right_swipe_count)
    stat.save(update_fields=['right_swipe_count', 'rate', 'updated_at'])
    bump_boost_metric([target_user.id], 'likes', 1)


def _user_abc_grade(u):
    try:
        return u.recommend_stat.grade or 'C'
    except Exception:
        return 'C'


def pick_users_by_abc_mix(candidates, limit, a_percent=20, b_percent=40, c_percent=40):
    """
    Build a feed mix by A/B/C share. Within each grade, shuffle randomly.
    If a grade bucket is short, randomly fill from leftover candidates.
    """
    import random

    limit = max(0, int(limit or 0))
    if limit <= 0 or not candidates:
        return []

    a_pct = max(0, int(a_percent or 0))
    b_pct = max(0, int(b_percent or 0))
    c_pct = max(0, int(c_percent or 0))
    total_pct = a_pct + b_pct + c_pct
    if total_pct <= 0:
        a_pct, b_pct, c_pct = 20, 40, 40
        total_pct = 100

    want_a = int(round(limit * a_pct / total_pct))
    want_b = int(round(limit * b_pct / total_pct))
    want_c = limit - want_a - want_b
    if want_c < 0:
        want_c = 0
        # trim overflow from B then A
        overflow = want_a + want_b - limit
        if overflow > 0:
            cut_b = min(want_b, overflow)
            want_b -= cut_b
            overflow -= cut_b
            want_a = max(0, want_a - overflow)

    buckets = {'A': [], 'B': [], 'C': []}
    for u in candidates:
        g = _user_abc_grade(u)
        if g not in buckets:
            g = 'C'
        buckets[g].append(u)
    for g in buckets:
        random.shuffle(buckets[g])

    picked = []
    used = set()

    def take_from(grade, n):
        got = []
        for u in buckets.get(grade, []):
            if len(got) >= n:
                break
            if u.id in used:
                continue
            used.add(u.id)
            got.append(u)
        return got

    picked.extend(take_from('A', want_a))
    picked.extend(take_from('B', want_b))
    picked.extend(take_from('C', want_c))

    # Randomly fill shortfall from leftover candidates
    if len(picked) < limit:
        leftovers = [u for u in candidates if u.id not in used]
        random.shuffle(leftovers)
        for u in leftovers:
            if len(picked) >= limit:
                break
            used.add(u.id)
            picked.append(u)

    random.shuffle(picked)
    return picked[:limit]


def recompute_abc_grades(app_id, country='*', locale='*'):
    """
    Rank users by right_swipe / impression within the rule scope.
    Top a% → A, next b% → B, remaining → C.
    Only users with impression_count > 0 are ranked; others stay C.
    """
    rule = get_funnel_abc_rule(app_id, country, locale)
    if not rule:
        return {'total': 0, 'a': 0, 'b': 0, 'c': 0, 'skipped': 'no_matching_rule'}
    a_pct = max(0, int(rule.a_percent or 0))
    b_pct = max(0, int(rule.b_percent or 0))

    qs = UserRecommendStat.objects.filter(app_id=app_id, impression_count__gt=0)
    if country and country != '*':
        qs = qs.filter(user__country__iexact=country)
    if locale and locale != '*':
        qs = qs.filter(user__locale__iexact=locale)
    rows = list(qs.order_by('-rate', '-right_swipe_count', 'user_id'))
    n = len(rows)
    if n == 0:
        zero_qs = UserRecommendStat.objects.filter(app_id=app_id, impression_count=0)
        if country and country != '*':
            zero_qs = zero_qs.filter(user__country__iexact=country)
        if locale and locale != '*':
            zero_qs = zero_qs.filter(user__locale__iexact=locale)
        zero_qs.exclude(grade='C').update(grade='C')
        return {'total': 0, 'a': 0, 'b': 0, 'c': 0}

    a_cut = max(0, int(round(n * a_pct / 100.0)))
    b_cut = a_cut + max(0, int(round(n * b_pct / 100.0)))
    if a_cut + (b_cut - a_cut) > n:
        b_cut = n

    a_n = b_n = c_n = 0
    for idx, row in enumerate(rows):
        if idx < a_cut:
            grade = 'A'
            a_n += 1
        elif idx < b_cut:
            grade = 'B'
            b_n += 1
        else:
            grade = 'C'
            c_n += 1
        if row.grade != grade:
            row.grade = grade
            row.save(update_fields=['grade', 'updated_at'])
    zero_qs = UserRecommendStat.objects.filter(app_id=app_id, impression_count=0)
    if country and country != '*':
        zero_qs = zero_qs.filter(user__country__iexact=country)
    if locale and locale != '*':
        zero_qs = zero_qs.filter(user__locale__iexact=locale)
    zero_qs.exclude(grade='C').update(grade='C')
    return {'total': n, 'a': a_n, 'b': b_n, 'c': c_n}

def resolve_robot_recommend_list(app_id, country='*', locale='*'):
    """
    Active robot lists matching country/locale, highest priority first.
    Equal priority: prefer more specific region/language.
    """
    from models.models import RobotRecommendList

    rows = list(RobotRecommendList.objects.filter(app_id=app_id, is_active=True))
    matched = [r for r in rows if region_locale_matches(r.country, r.locale, country, locale)]
    if not matched:
        return None
    matched.sort(
        key=lambda r: (_config_match_rank(r.country, r.locale, r.priority), r.id),
        reverse=True,
    )
    return matched[0]


def robot_funnel_qs(app_id, country=None, locale=None):
    """
    Prefer robots from the highest-priority matching RobotRecommendList.
    If no list matches → fully random shuffle of active robots for the app.
    """
    import random

    qs = FunnelPool.objects.filter(app_id=app_id, is_active=True).filter(
        Q(pool=FunnelPool.POOL_ROBOT) | Q(pool=FunnelPool.POOL_A) | Q(pool=FunnelPool.POOL_B)
    )
    country = country or '*'
    locale = (locale or '*').lower() or '*'
    cfg = resolve_robot_recommend_list(app_id, country, locale)

    if cfg and cfg.robot_ids:
        ids = []
        for x in (cfg.robot_ids or []):
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        items = list(qs.filter(id__in=ids))
        preserved = {rid: idx for idx, rid in enumerate(ids)}
        items.sort(key=lambda i: preserved.get(i.id, 9999))
        return items

    # No matching config → fully automatic random
    items = list(qs)
    random.shuffle(items)
    return items


def active_boost(user):
    return BoostSession.objects.filter(user=user, is_active=True, end_at__gt=timezone.now()).first()


def consume_ledger(user, kind, amount=1, period_key=None):
    with transaction.atomic():
        if period_key is None and kind == EntitlementLedger.DAILY_LIKE:
            ensure_daily_likes(user)
            ledger = (
                EntitlementLedger.objects.select_for_update()
                .get(user=user, kind=EntitlementLedger.DAILY_LIKE, period_key=period_day_key())
            )
            if ledger.balance < amount:
                return False, ledger
            ledger.balance -= amount
            ledger.save(update_fields=['balance', 'updated_at'])
            return True, ledger

        if period_key is not None:
            pk = period_key or ''
            get_or_create_ledger(user, kind, pk)
            ledger = (
                EntitlementLedger.objects.select_for_update()
                .get(user=user, kind=kind, period_key=pk)
            )
            if ledger.balance < amount:
                return False, ledger
            ledger.balance -= amount
            ledger.save(update_fields=['balance', 'updated_at'])
            return True, ledger

        ensure_vip_grants_consistent(user)

        # Prefer daily free SL → VIP grant → legacy '' → purchased
        if kind == EntitlementLedger.SUPER_LIKE:
            ensure_daily_superlike(user)
            order = (f'daily:{period_day_key()}', 'grant', '', 'purchased')
        elif kind == EntitlementLedger.BOOST:
            order = ('grant', '', 'purchased')
        else:
            order = ('', 'grant', 'purchased')

        for key in order:
            get_or_create_ledger(user, kind, key)
            ledger = (
                EntitlementLedger.objects.select_for_update()
                .get(user=user, kind=kind, period_key=key)
            )
            if ledger.balance >= amount:
                ledger.balance -= amount
                ledger.save(update_fields=['balance', 'updated_at'])
                return True, ledger
        return False, get_or_create_ledger(user, kind, '')


def grant_ledger(user, kind, amount, period_key=''):
    ledger = get_or_create_ledger(user, kind, period_key, 0)
    ledger.balance += amount
    ledger.save(update_fields=['balance', 'updated_at'])
    return ledger
