"""
Google Analytics 4 Measurement Protocol forwarder.

Admin Providers → ga4 (per-app): enabled + measurement_id + api_secret.
Called best-effort after self-built t_event ingest; never blocks client response.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

GA4_MP_URL = 'https://www.google-analytics.com/mp/collect'


def ga4_configured(app_id: str | None = None) -> bool:
    from tools.provider_helpers import provider_enabled, get_provider_field
    if not provider_enabled('ga4', app_id, default=False):
        return False
    mid = get_provider_field('ga4', 'measurement_id', app_id)
    secret = get_provider_field('ga4', 'api_secret', app_id)
    return bool(mid and secret)


def analytics_feature_flags(app_id: str | None = None) -> dict:
    """Bootstrap payload for client analytics toggles."""
    from tools.app_modules import is_module_enabled
    self_enabled = is_module_enabled(app_id or 'spark_main', 'events')
    forward = ga4_configured(app_id)
    return {
        'self_enabled': self_enabled,
        'third_party': 'ga4' if forward else None,
        'ga4_forward': forward,
    }


def _client_id_for(user_id, props: dict) -> str:
    if props.get('device_id'):
        return str(props['device_id'])[:64]
    if props.get('session_id'):
        return str(props['session_id'])[:64]
    if user_id:
        return f'uid.{user_id}'
    return 'anon.unknown'


def _sanitize_event_name(name: str) -> str:
    # GA4 event names: [a-zA-Z][a-zA-Z0-9_]{0,39}
    out = []
    for i, ch in enumerate(str(name or 'event')[:40]):
        if ch.isalnum() or ch == '_':
            out.append(ch)
        else:
            out.append('_')
    s = ''.join(out) or 'event'
    if s[0].isdigit():
        s = 'e_' + s[:38]
    return s[:40]


def _params_from_props(props: dict) -> dict:
    params = {}
    for k, v in (props or {}).items():
        if k in ('ts',):
            continue
        key = str(k)[:40]
        if isinstance(v, (str, int, float, bool)):
            params[key] = v if not isinstance(v, str) else v[:100]
        elif v is None:
            continue
        else:
            params[key] = json.dumps(v, ensure_ascii=False)[:100]
    return params


def build_ga4_payload(events: list[dict], *, user_id=None) -> dict | None:
    """
    events: list of {event, props, app_version?, device_locale?}
    """
    if not events:
        return None
    props0 = dict(events[0].get('props') or {})
    client_id = _client_id_for(user_id, props0)
    ga_events = []
    for e in events[:25]:
        name = _sanitize_event_name(e.get('event') or e.get('name') or 'event')
        params = _params_from_props(dict(e.get('props') or {}))
        if e.get('app_version'):
            params.setdefault('app_version', str(e['app_version'])[:40])
        if e.get('device_locale'):
            params.setdefault('device_locale', str(e['device_locale'])[:40])
        ga_events.append({'name': name, 'params': params})
    payload: dict[str, Any] = {
        'client_id': client_id,
        'events': ga_events,
    }
    if user_id:
        payload['user_id'] = str(user_id)
    return payload


def forward_events_to_ga4(app_id: str, events: list[dict], *, user_id=None) -> dict:
    """
    Best-effort HTTP post to GA4 MP. Returns {ok, reason?, status?}.
    """
    from tools.provider_helpers import get_provider_field, provider_enabled

    if not provider_enabled('ga4', app_id, default=False):
        return {'ok': False, 'reason': 'disabled'}
    measurement_id = get_provider_field('ga4', 'measurement_id', app_id)
    api_secret = get_provider_field('ga4', 'api_secret', app_id)
    if not measurement_id or not api_secret:
        return {'ok': False, 'reason': 'missing_credentials'}

    payload = build_ga4_payload(events, user_id=user_id)
    if not payload:
        return {'ok': False, 'reason': 'empty'}

    url = f'{GA4_MP_URL}?measurement_id={measurement_id}&api_secret={api_secret}'
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            status = getattr(resp, 'status', 204) or 204
            return {'ok': status < 300, 'status': status}
    except urllib.error.HTTPError as e:
        logger.warning('ga4 forward HTTPError %s', e.code)
        return {'ok': False, 'status': e.code, 'reason': 'http_error'}
    except Exception as e:
        logger.warning('ga4 forward failed: %s', e)
        return {'ok': False, 'reason': str(e)[:120]}
