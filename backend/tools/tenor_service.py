"""
Tenor GIF search (Google).

Docs: https://developers.google.com/tenor/guides/endpoints
"""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _cfg() -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('tenor')
    return {
        'enabled': cfg.get('enabled', True),
        'api_key': get_provider_field('tenor', 'api_key') or '',
        'client_key': cfg.get('client_key') or 'spark',
    }


def tenor_configured() -> bool:
    return bool(_cfg()['api_key'])


def search_gifs(query: str, limit: int = 20) -> dict[str, Any]:
    q = (query or '').strip()
    if not q:
        return {'ok': False, 'error': 'q required'}
    if not tenor_configured():
        return {'ok': False, 'error': 'tenor_not_configured'}
    c = _cfg()
    try:
        resp = requests.get(
            'https://tenor.googleapis.com/v2/search',
            params={
                'q': q,
                'key': c['api_key'],
                'client_key': c['client_key'],
                'limit': max(1, min(int(limit or 20), 50)),
                'media_filter': 'gif,tinygif',
            },
            timeout=15,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {'ok': False, 'error': data.get('error', {}).get('message') or resp.text[:300]}
        results = []
        for item in data.get('results') or []:
            media = item.get('media_formats') or {}
            gif = media.get('gif') or media.get('tinygif') or {}
            preview = media.get('tinygif') or media.get('nanogif') or gif
            url = gif.get('url') or ''
            if not url:
                continue
            results.append({
                'id': item.get('id') or '',
                'url': url,
                'preview_url': preview.get('url') or url,
                'dims': gif.get('dims') or [],
            })
        return {'ok': True, 'list': results}
    except Exception as exc:
        logger.exception('tenor search failed')
        return {'ok': False, 'error': str(exc)[:300]}
