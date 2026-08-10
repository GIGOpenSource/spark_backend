"""
Apple Sign-In identity token verification.

Docs: https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_rest_api/verifying_a_user
"""

from __future__ import annotations

import logging
from typing import Any

import jwt
import requests
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

APPLE_JWKS_URL = 'https://appleid.apple.com/auth/keys'
APPLE_ISSUER = 'https://appleid.apple.com'


def _cfg(app_id: str | None) -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('apple_signin', app_id)
    return {
        'enabled': cfg.get('enabled', True),
        'client_id': get_provider_field('apple_signin', 'client_id', app_id) or cfg.get('client_id') or '',
        'team_id': get_provider_field('apple_signin', 'team_id', app_id) or '',
        'key_id': get_provider_field('apple_signin', 'key_id', app_id) or '',
        'private_key': get_provider_field('apple_signin', 'private_key', app_id) or '',
    }


def apple_signin_configured(app_id: str | None = None) -> bool:
    c = _cfg(app_id)
    return bool(c['client_id'])


def verify_apple_identity_token(identity_token: str, app_id: str | None = None) -> dict[str, Any]:
    if not identity_token:
        return {'ok': False, 'error': 'identity_token required'}
    cfg = _cfg(app_id)
    client_id = cfg['client_id']
    if not client_id:
        return {'ok': False, 'error': 'apple_signin_not_configured'}
    try:
        jwks = PyJWKClient(APPLE_JWKS_URL)
        signing_key = jwks.get_signing_key_from_jwt(identity_token)
        claims = jwt.decode(
            identity_token,
            signing_key.key,
            algorithms=['RS256'],
            audience=client_id,
            issuer=APPLE_ISSUER,
        )
        email = (claims.get('email') or '').lower()
        sub = claims.get('sub') or ''
        return {
            'ok': True,
            'email': email,
            'email_verified': str(claims.get('email_verified', True)).lower() in ('true', '1'),
            'sub': sub,
            'name': '',
            'claims': claims,
        }
    except Exception as exc:
        logger.warning('apple identity token verify failed: %s', exc)
        return {'ok': False, 'error': str(exc)[:300]}
