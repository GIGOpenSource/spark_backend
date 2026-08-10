"""
Agora RTC token builder.

Docs: https://docs.agora.io/en/video-calling/develop/authentication-workflow
Uses agora-token package when available; otherwise returns not_configured / mock.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _cfg() -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('agora')
    return {
        'enabled': cfg.get('enabled', False),
        'app_id': get_provider_field('agora', 'app_id') or cfg.get('app_id') or '',
        'app_certificate': get_provider_field('agora', 'app_certificate') or '',
        'token_expire_sec': int(cfg.get('token_expire_sec') or 3600),
    }


def agora_configured() -> bool:
    c = _cfg()
    return bool(c['app_id'] and c['app_certificate'])


def build_rtc_token(channel: str, uid: int, role: str = 'publisher') -> dict[str, Any]:
    channel = str(channel or '').strip()
    if not channel:
        return {'ok': False, 'error': 'channel required'}
    c = _cfg()
    allow_mock = bool(getattr(settings, 'USE_AGORA_MOCK', False))
    if not agora_configured():
        if allow_mock:
            return {
                'ok': True,
                'mock': True,
                'app_id': c['app_id'] or 'mock_agora_app',
                'channel': channel,
                'uid': int(uid),
                'token': f'mock_token_{channel}_{uid}',
                'expire_at': int(time.time()) + 3600,
            }
        return {'ok': False, 'error': 'agora_not_configured'}
    try:
        from agora_token_builder import RtcTokenBuilder  # type: ignore
        # Role_Publisher = 1, Role_Subscriber = 2
        role_int = 1 if role != 'subscriber' else 2
        expire = int(time.time()) + int(c['token_expire_sec'])
        token = RtcTokenBuilder.buildTokenWithUid(
            c['app_id'], c['app_certificate'], channel, int(uid), role_int, expire,
        )
        return {
            'ok': True,
            'mock': False,
            'app_id': c['app_id'],
            'channel': channel,
            'uid': int(uid),
            'token': token,
            'expire_at': expire,
        }
    except ImportError:
        try:
            # Alternative package name used in some projects
            from agora_token.RtcTokenBuilder import RtcTokenBuilder, Role_Publisher, Role_Subscriber  # type: ignore
            role_const = Role_Publisher if role != 'subscriber' else Role_Subscriber
            expire = int(time.time()) + int(c['token_expire_sec'])
            token = RtcTokenBuilder.buildTokenWithUid(
                c['app_id'], c['app_certificate'], channel, int(uid), role_const, expire,
            )
            return {
                'ok': True,
                'mock': False,
                'app_id': c['app_id'],
                'channel': channel,
                'uid': int(uid),
                'token': token,
                'expire_at': expire,
            }
        except Exception as exc:
            logger.exception('agora token build failed')
            return {'ok': False, 'error': f'agora_sdk_missing:{exc}'[:300]}
    except Exception as exc:
        logger.exception('agora token build failed')
        return {'ok': False, 'error': str(exc)[:300]}
