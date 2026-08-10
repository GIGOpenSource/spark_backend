"""
Instagram Basic Display / Spotify OAuth (authorization code).
"""

from __future__ import annotations

import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _ig_cfg() -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('instagram_oauth')
    return {
        'enabled': cfg.get('enabled', False),
        'client_id': get_provider_field('instagram_oauth', 'client_id') or '',
        'client_secret': get_provider_field('instagram_oauth', 'client_secret') or '',
        'redirect_uri': get_provider_field('instagram_oauth', 'redirect_uri') or cfg.get('redirect_uri') or '',
    }


def _spotify_cfg() -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('spotify_oauth')
    return {
        'enabled': cfg.get('enabled', False),
        'client_id': get_provider_field('spotify_oauth', 'client_id') or '',
        'client_secret': get_provider_field('spotify_oauth', 'client_secret') or '',
        'redirect_uri': get_provider_field('spotify_oauth', 'redirect_uri') or cfg.get('redirect_uri') or '',
    }


def instagram_configured() -> bool:
    c = _ig_cfg()
    return bool(c['client_id'] and c['client_secret'] and c['redirect_uri'])


def spotify_configured() -> bool:
    c = _spotify_cfg()
    return bool(c['client_id'] and c['client_secret'] and c['redirect_uri'])


def _state_key(state: str) -> str:
    return f'social_oauth:{state}'


def start_oauth(provider: str, user_id: int) -> dict[str, Any]:
    provider = (provider or '').lower().strip()
    state = secrets.token_urlsafe(24)
    cache.set(_state_key(state), {'provider': provider, 'user_id': user_id}, timeout=600)
    if provider == 'instagram':
        if not instagram_configured():
            return {'ok': False, 'error': 'instagram_oauth_not_configured'}
        c = _ig_cfg()
        qs = urlencode({
            'client_id': c['client_id'],
            'redirect_uri': c['redirect_uri'],
            'scope': 'user_profile,user_media',
            'response_type': 'code',
            'state': state,
        })
        return {
            'ok': True,
            'provider': provider,
            'authorize_url': f'https://api.instagram.com/oauth/authorize?{qs}',
            'state': state,
        }
    if provider == 'spotify':
        if not spotify_configured():
            return {'ok': False, 'error': 'spotify_oauth_not_configured'}
        c = _spotify_cfg()
        qs = urlencode({
            'client_id': c['client_id'],
            'response_type': 'code',
            'redirect_uri': c['redirect_uri'],
            'scope': 'user-read-private user-read-email user-top-read',
            'state': state,
        })
        return {
            'ok': True,
            'provider': provider,
            'authorize_url': f'https://accounts.spotify.com/authorize?{qs}',
            'state': state,
        }
    return {'ok': False, 'error': 'unsupported_provider'}


def finish_oauth(provider: str, code: str, state: str) -> dict[str, Any]:
    provider = (provider or '').lower().strip()
    meta = cache.get(_state_key(state)) or {}
    if not meta or meta.get('provider') != provider:
        return {'ok': False, 'error': 'invalid_state'}
    user_id = meta.get('user_id')
    cache.delete(_state_key(state))
    if provider == 'instagram':
        return _finish_instagram(code, user_id)
    if provider == 'spotify':
        return _finish_spotify(code, user_id)
    return {'ok': False, 'error': 'unsupported_provider'}


def _finish_instagram(code: str, user_id: int) -> dict[str, Any]:
    c = _ig_cfg()
    try:
        token_resp = requests.post(
            'https://api.instagram.com/oauth/access_token',
            data={
                'client_id': c['client_id'],
                'client_secret': c['client_secret'],
                'grant_type': 'authorization_code',
                'redirect_uri': c['redirect_uri'],
                'code': code,
            },
            timeout=20,
        )
        token_data = token_resp.json() if token_resp.content else {}
        if token_resp.status_code >= 400 or not token_data.get('access_token'):
            return {'ok': False, 'error': token_data.get('error_message') or 'token_exchange_failed'}
        access = token_data['access_token']
        me = requests.get(
            'https://graph.instagram.com/me',
            params={'fields': 'id,username', 'access_token': access},
            timeout=15,
        ).json()
        username = me.get('username') or ''
        return {
            'ok': True,
            'user_id': user_id,
            'provider': 'instagram',
            'handle': username,
            'profile_url': f'https://instagram.com/{username}' if username else '',
        }
    except Exception as exc:
        logger.exception('instagram oauth failed')
        return {'ok': False, 'error': str(exc)[:300]}


def _finish_spotify(code: str, user_id: int) -> dict[str, Any]:
    c = _spotify_cfg()
    try:
        token_resp = requests.post(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': c['redirect_uri'],
            },
            auth=(c['client_id'], c['client_secret']),
            timeout=20,
        )
        token_data = token_resp.json() if token_resp.content else {}
        if token_resp.status_code >= 400 or not token_data.get('access_token'):
            return {'ok': False, 'error': token_data.get('error_description') or 'token_exchange_failed'}
        access = token_data['access_token']
        me = requests.get(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': f'Bearer {access}'},
            timeout=15,
        ).json()
        display = me.get('display_name') or me.get('id') or ''
        url = ((me.get('external_urls') or {}).get('spotify')) or ''
        return {
            'ok': True,
            'user_id': user_id,
            'provider': 'spotify',
            'handle': display,
            'profile_url': url,
        }
    except Exception as exc:
        logger.exception('spotify oauth failed')
        return {'ok': False, 'error': str(exc)[:300]}
