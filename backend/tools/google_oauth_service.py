"""
Google Sign-In ID token verification (backend).

Docs: https://developers.google.com/identity/sign-in/web/backend-auth
"""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _oauth_cfg(app_id: str | None) -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('google_oauth', app_id)
    return {
        'enabled': cfg.get('enabled', True),
        'web_client_id': get_provider_field('google_oauth', 'web_client_id', app_id) or '',
        'android_client_id': get_provider_field('google_oauth', 'android_client_id', app_id) or '',
        'ios_client_id': get_provider_field('google_oauth', 'ios_client_id', app_id) or '',
    }


def google_oauth_configured(app_id: str | None = None) -> bool:
    c = _oauth_cfg(app_id)
    return bool(c['web_client_id'] or c['android_client_id'] or c['ios_client_id'])


def verify_google_id_token(id_token_str: str, app_id: str | None = None) -> dict[str, Any]:
    """
    Verify Google ID token and return profile claims.
    aud must match one of configured client IDs.
    """
    if not id_token_str:
        return {'ok': False, 'error': 'id_token required'}
    cfg = _oauth_cfg(app_id)
    audiences = [x for x in (cfg['web_client_id'], cfg['android_client_id'], cfg['ios_client_id']) if x]
    if not audiences:
        return {'ok': False, 'error': 'google_oauth_not_configured'}

    # Prefer google-auth library
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as ga_requests
        request = ga_requests.Request()
        last_err = None
        for aud in audiences:
            try:
                claims = google_id_token.verify_oauth2_token(id_token_str, request, aud)
                return {
                    'ok': True,
                    'email': (claims.get('email') or '').lower(),
                    'email_verified': bool(claims.get('email_verified')),
                    'sub': claims.get('sub') or '',
                    'name': claims.get('name') or '',
                    'picture': claims.get('picture') or '',
                    'aud': claims.get('aud'),
                    'claims': claims,
                }
            except Exception as exc:
                last_err = str(exc)
        return {'ok': False, 'error': last_err or 'aud_mismatch'}
    except ImportError:
        pass

    # Fallback: tokeninfo endpoint
    try:
        resp = requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': id_token_str},
            timeout=15,
        )
        claims = resp.json() if resp.content else {}
        if resp.status_code >= 400 or claims.get('error'):
            return {'ok': False, 'error': claims.get('error_description') or claims.get('error') or 'tokeninfo_failed'}
        aud = claims.get('aud')
        if aud not in audiences:
            return {'ok': False, 'error': 'aud_mismatch', 'aud': aud}
        return {
            'ok': True,
            'email': (claims.get('email') or '').lower(),
            'email_verified': str(claims.get('email_verified')).lower() in ('true', '1'),
            'sub': claims.get('sub') or '',
            'name': claims.get('name') or '',
            'picture': claims.get('picture') or '',
            'aud': aud,
            'claims': claims,
        }
    except Exception as exc:
        logger.exception('google tokeninfo failed')
        return {'ok': False, 'error': str(exc)[:300]}
