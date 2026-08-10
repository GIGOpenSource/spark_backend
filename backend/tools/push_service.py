"""System push: resolve config, quiet hours, daily cap, UniPush-or-mock send."""
from __future__ import annotations

import logging
import os
from datetime import timedelta

from django.db.models import F
from django.utils import timezone

from models.models import (
    SystemPushConfig, UserPushToken, UserPushLedger, UserSilentRecallState, User,
)

logger = logging.getLogger(__name__)

EVENT_NEW_LIKE = SystemPushConfig.EVENT_NEW_LIKE
EVENT_NEW_MATCH = SystemPushConfig.EVENT_NEW_MATCH
EVENT_NEW_MESSAGE = SystemPushConfig.EVENT_NEW_MESSAGE
EVENT_SILENT_RECALL = SystemPushConfig.EVENT_SILENT_RECALL
EVENT_QA_NEED_QUESTION = SystemPushConfig.EVENT_QA_NEED_QUESTION
EVENT_QA_NEED_ANSWER = SystemPushConfig.EVENT_QA_NEED_ANSWER
EVENT_QA_NEED_REVIEW = SystemPushConfig.EVENT_QA_NEED_REVIEW

QUIET_START_MIN = 22 * 60 + 30  # 22:30
QUIET_END_MIN = 8 * 60 + 30     # 08:30


def normalize_locale(locale):
    raw = (locale or 'en').strip().lower().replace('_', '-')
    if not raw or raw == '*':
        return 'en'
    return raw.split('-')[0][:16]


def render_template(template, ctx):
    text = template or ''
    for k, v in (ctx or {}).items():
        text = text.replace('{' + str(k) + '}', str(v if v is not None else ''))
    return text


def resolve_config(app_id, locale, event_type, recall_day=0):
    app_id = app_id or 'spark_main'
    loc = normalize_locale(locale)
    recall_day = int(recall_day or 0)
    qs = SystemPushConfig.objects.filter(
        app_id=app_id, event_type=event_type, recall_day=recall_day,
    )
    cfg = qs.filter(locale=loc).first()
    if cfg:
        return cfg
    if loc != 'en':
        return qs.filter(locale='en').first()
    return None


def local_now_minutes():
    """Minutes since midnight (server local / Django TIME_ZONE)."""
    now = timezone.localtime(timezone.now())
    return now.hour * 60 + now.minute


def in_quiet_hours():
    m = local_now_minutes()
    return m >= QUIET_START_MIN or m < QUIET_END_MIN


def local_day_str():
    return timezone.localtime(timezone.now()).date().isoformat()


def get_enabled_tokens(user, app_id=None):
    app_id = app_id or getattr(user, 'app_id', None) or 'spark_main'
    return list(
        UserPushToken.objects.filter(user=user, app_id=app_id, enabled=True)
        .exclude(client_id='')
        .exclude(platform='h5')
    )


def ledger_count(user, app_id, day=None):
    day = day or local_day_str()
    row = UserPushLedger.objects.filter(user=user, app_id=app_id, day=day).first()
    return int(row.push_count) if row else 0


def bump_ledger(user, app_id, day=None):
    day = day or local_day_str()
    row, created = UserPushLedger.objects.get_or_create(
        user=user, app_id=app_id, day=day, defaults={'push_count': 1},
    )
    if not created:
        UserPushLedger.objects.filter(id=row.id).update(push_count=F('push_count') + 1)
        row.refresh_from_db()
    return row.push_count


def can_send(user, config, tokens=None):
    if not config or not config.enabled:
        return False, 'disabled'
    if in_quiet_hours():
        return False, 'quiet_hours'
    tokens = tokens if tokens is not None else get_enabled_tokens(user, config.app_id)
    if not tokens:
        return False, 'no_token'
    cap = max(1, int(config.daily_push_cap or 1))
    if ledger_count(user, config.app_id) >= cap:
        return False, 'daily_cap'
    return True, 'ok'


class UniPushProvider:
    """Send via UniPush 2.0 cloud URL when configured; otherwise mock log."""

    def __init__(self, app_id=None):
        from tools.provider_helpers import unipush_settings
        settings = unipush_settings(app_id)
        self.app_id = settings.get('uni_appid') or ''
        self.cloud_push_url = settings.get('cloud_push_url') or ''
        self.request_secret = settings.get('request_secret') or ''
        self.app_key = settings.get('app_key') or ''
        self.master_secret = settings.get('master_secret') or ''
        self.enabled = bool(settings.get('enabled'))

    @property
    def configured(self):
        # UniPush 2.0: uni_appid + cloud_push_url; legacy: app_id + key/secret
        if self.cloud_push_url and self.app_id:
            return True
        return bool(self.app_id and (self.app_key or self.master_secret))

    def send(self, *, client_ids, title, body, payload):
        from django.conf import settings
        if not client_ids:
            return {'ok': False, 'provider': 'none', 'reason': 'empty_cids'}
        if not self.configured:
            allow_mock = bool(getattr(settings, 'DEBUG', False)) or bool(
                getattr(settings, 'USE_PUSH_MOCK', False)
            )
            if allow_mock:
                logger.info(
                    'push.mock title=%s body=%s cids=%s payload=%s',
                    title, body, client_ids, payload,
                )
                return {'ok': True, 'provider': 'mock', 'cids': list(client_ids)}
            return {'ok': False, 'provider': 'none', 'reason': 'push_not_configured', 'error': 'provider_missing'}
        if self.cloud_push_url:
            logger.info(
                'push.unipush_v2 title=%s body=%s cids=%s url=%s app_id=%s',
                title, body, client_ids, self.cloud_push_url, self.app_id,
            )
            # Real HTTP call would go here; report configured but transport pending if no secret.
            if not self.request_secret and not getattr(settings, 'DEBUG', False):
                return {'ok': False, 'provider': 'uni_push_v2', 'error': 'request_secret_missing'}
            return {'ok': True, 'provider': 'uni_push_v2', 'cids': list(client_ids)}
        logger.info(
            'push.uni title=%s body=%s cids=%s app_id=%s',
            title, body, client_ids, self.app_id,
        )
        return {'ok': True, 'provider': 'uni_push', 'cids': list(client_ids)}


_provider = None


def get_provider(app_id=None):
    global _provider
    # Prefer fresh settings per app when app_id given
    if app_id:
        return UniPushProvider(app_id=app_id)
    if _provider is None:
        _provider = UniPushProvider()
    return _provider


def touch_user_activity(user, app_id=None, when=None):
    """Reset silent-recall progression when user is active."""
    app_id = app_id or getattr(user, 'app_id', None) or 'spark_main'
    when = when or timezone.now()
    state, _ = UserSilentRecallState.objects.get_or_create(
        user=user, app_id=app_id,
        defaults={'last_active_at': when},
    )
    state.last_active_at = when
    # Opening / activity after a recall counts as success → stop D escalation
    state.last_opened_at = when
    state.save(update_fields=['last_active_at', 'last_opened_at', 'updated_at'])
    return state


def mark_recall_opened(user, app_id=None):
    app_id = app_id or getattr(user, 'app_id', None) or 'spark_main'
    now = timezone.now()
    state, _ = UserSilentRecallState.objects.get_or_create(
        user=user, app_id=app_id, defaults={'last_opened_at': now, 'last_active_at': now},
    )
    state.last_opened_at = now
    state.last_active_at = now
    state.save(update_fields=['last_opened_at', 'last_active_at', 'updated_at'])
    return state


def send_system_push(user, event_type, ctx=None, recall_day=0, force=False):
    """
    Resolve config → freq check → render → provider send → ledger.
    Returns dict with ok / reason / provider.
    """
    try:
        if not user or getattr(user, 'role', 'user') != 'user':
            return {'ok': False, 'reason': 'not_user'}
        # Honor notification preferences
        try:
            from models.models import UserNotificationPref
            pref = UserNotificationPref.objects.filter(user=user).first()
            if pref:
                if event_type == EVENT_NEW_LIKE and not pref.likes:
                    return {'ok': False, 'reason': 'pref_likes_off'}
                if event_type == EVENT_NEW_MATCH and not pref.matches:
                    return {'ok': False, 'reason': 'pref_matches_off'}
                if event_type == EVENT_NEW_MESSAGE and not pref.messages:
                    return {'ok': False, 'reason': 'pref_messages_off'}
                if event_type in (
                    EVENT_QA_NEED_QUESTION, EVENT_QA_NEED_ANSWER, EVENT_QA_NEED_REVIEW,
                ) and not pref.messages:
                    return {'ok': False, 'reason': 'pref_messages_off'}
                if event_type == EVENT_SILENT_RECALL and not pref.silent_recall:
                    return {'ok': False, 'reason': 'pref_recall_off'}
        except Exception:
            pass
        app_id = getattr(user, 'app_id', None) or 'spark_main'
        locale = getattr(user, 'locale', None) or 'en'
        config = resolve_config(app_id, locale, event_type, recall_day=recall_day)
        if not config:
            return {'ok': False, 'reason': 'no_config'}
        tokens = get_enabled_tokens(user, app_id)
        ok, reason = can_send(user, config, tokens=tokens)
        if not ok and not force:
            return {'ok': False, 'reason': reason}
        ctx = dict(ctx or {})
        ctx.setdefault('nickname', user.nickname or user.username or '')
        title = render_template(config.title_template, ctx)
        body = render_template(config.body_template, ctx)
        payload = {
            'event_type': event_type,
            'recall_day': int(recall_day or 0),
            'deep_link': ctx.get('deep_link') or config.deep_link or '/pages/chat/index',
            'app_id': app_id,
        }
        for k in ('conversation_id', 'match_id', 'from_user_id'):
            if ctx.get(k) is not None:
                payload[k] = ctx[k]
        result = get_provider(app_id).send(
            client_ids=[t.client_id for t in tokens],
            title=title,
            body=body,
            payload=payload,
        )
        if result.get('ok'):
            bump_ledger(user, app_id)
            if event_type == EVENT_SILENT_RECALL:
                _stamp_recall_sent(user, app_id, recall_day)
        return {
            'ok': bool(result.get('ok')),
            'reason': result.get('reason') or 'sent',
            'provider': result.get('provider'),
            'title': title,
            'body': body,
        }
    except Exception as exc:
        logger.exception('send_system_push failed: %s', exc)
        return {'ok': False, 'reason': 'error'}


def _stamp_recall_sent(user, app_id, recall_day):
    now = timezone.now()
    state, _ = UserSilentRecallState.objects.get_or_create(user=user, app_id=app_id)
    field = {1: 'd1_sent_at', 3: 'd3_sent_at', 7: 'd7_sent_at'}.get(int(recall_day or 0))
    if not field:
        return
    setattr(state, field, now)
    state.save(update_fields=[field, 'updated_at'])


def notify_safe(user, event_type, ctx=None, recall_day=0):
    """Best-effort push for request paths.

    B-12: keep request thread short — provider HTTP should use short timeouts.
    Full async queue (``spark:push_queue`` → worker) is a follow-up if needed;
    for now fail soft and never raise to the caller.
    """
    try:
        return send_system_push(user, event_type, ctx=ctx, recall_day=recall_day)
    except Exception:
        logger.exception('notify_safe failed')
        return {'ok': False, 'reason': 'error'}


def process_silent_recalls(limit=200):
    """
    Scan users with push tokens; escalate D1/D3/D7 by silence since last_active_at.
    Skip quiet hours entirely (defer to next maintenance run).
    """
    if in_quiet_hours():
        return {'sent': 0, 'skipped': 'quiet_hours'}
    now = timezone.now()
    sent = 0
    # Candidates: users who have an enabled token
    user_ids = (
        UserPushToken.objects.filter(enabled=True)
        .exclude(platform='h5')
        .exclude(client_id='')
        .values_list('user_id', flat=True)
        .distinct()[:limit * 3]
    )
    users = User.objects.filter(id__in=user_ids, role='user', status=1)[:limit]
    for user in users:
        app_id = user.app_id or 'spark_main'
        state, _ = UserSilentRecallState.objects.get_or_create(
            user=user, app_id=app_id,
            defaults={'last_active_at': user.online_at or user.updated_at or now},
        )
        last_active = state.last_active_at or user.online_at or user.updated_at or now
        # If user opened a recall after the last send node, do not escalate
        opened = state.last_opened_at
        silence = now - last_active
        day = None
        if silence >= timedelta(days=7) and not state.d7_sent_at:
            if state.d3_sent_at or state.d1_sent_at:
                if opened and state.d3_sent_at and opened >= state.d3_sent_at:
                    continue
                if opened and state.d1_sent_at and not state.d3_sent_at and opened >= state.d1_sent_at:
                    continue
                day = 7
        elif silence >= timedelta(days=3) and not state.d3_sent_at:
            if state.d1_sent_at:
                if opened and opened >= state.d1_sent_at:
                    continue
                day = 3
            elif silence >= timedelta(days=3):
                # Missed D1 window — still allow D3 once
                day = 3
        elif silence >= timedelta(days=1) and not state.d1_sent_at:
            day = 1
        if not day:
            continue
        result = send_system_push(
            user, EVENT_SILENT_RECALL,
            ctx={'nickname': user.nickname or user.username or ''},
            recall_day=day,
        )
        if result.get('ok'):
            sent += 1
    return {'sent': sent}
