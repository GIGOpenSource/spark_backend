"""
Google Cloud Translation API v2 (Basic).

Official docs:
https://cloud.google.com/translate/docs/reference/rest/v2/translate

POST https://translation.googleapis.com/language/translate/v2?key=API_KEY
Body (JSON): q, target, source?, format=text
"""

from __future__ import annotations

import html
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

TRANSLATE_URL = 'https://translation.googleapis.com/language/translate/v2'

# Map app locale prefs → BCP-47 codes Google Translate accepts
_LOCALE_ALIAS = {
    'zh': 'zh-CN',
    'zh-hans': 'zh-CN',
    'zh-cn': 'zh-CN',
    'zh-hant': 'zh-TW',
    'zh-tw': 'zh-TW',
    'zh-hk': 'zh-TW',
    'en-us': 'en',
    'en-gb': 'en',
    'pt-br': 'pt',
    'pt-pt': 'pt',
}


def normalize_lang(code: str | None, default: str = 'en') -> str:
    raw = (code or default or 'en').strip().replace('_', '-')
    if not raw or raw.lower() in ('auto', '*', 'device'):
        return default
    lower = raw.lower()
    if lower in _LOCALE_ALIAS:
        return _LOCALE_ALIAS[lower]
    # zh-CN / en keep as-is with proper casing for region
    parts = raw.split('-')
    if len(parts) == 1:
        return parts[0].lower()
    return f'{parts[0].lower()}-{parts[1].upper()}'


def get_translate_credentials() -> dict:
    from tools.provider_helpers import get_raw_provider_config, google_translate_api_key, provider_enabled

    cfg = get_raw_provider_config('google_translate')
    enabled = provider_enabled('google_translate', default=True)
    api_key = google_translate_api_key() if enabled else ''
    # If explicitly disabled, ignore key
    if cfg.get('enabled') is False:
        api_key = ''
        enabled = False
    return {
        'enabled': enabled and bool(api_key),
        'api_key': api_key,
        'configured': bool(api_key),
    }


def translate_text(
    text: str,
    target: str = 'en',
    source: str = 'auto',
    *,
    allow_mock: bool = True,
) -> dict[str, Any]:
    """
    Translate plain text via Google Translation API v2.

    Returns:
      {
        translated, target, source, detected_source?, mock, provider
      }
    """
    text = (text or '').strip()
    if not text:
        return {
            'translated': '',
            'target': target,
            'source': source,
            'mock': False,
            'provider': 'none',
            'error': 'empty_text',
        }

    target_lang = normalize_lang(target, default='en')
    source_lang = (source or 'auto').strip()
    if source_lang.lower() in ('', 'auto', '*'):
        source_lang = 'auto'
    else:
        source_lang = normalize_lang(source_lang, default=source_lang)

    creds = get_translate_credentials()
    if not creds['api_key']:
        if not allow_mock:
            return {
                'translated': '',
                'target': target_lang,
                'source': source_lang,
                'mock': True,
                'provider': 'none',
                'error': 'not_configured',
            }
        return {
            'translated': f'[{target_lang}] {text}',
            'target': target_lang,
            'source': source_lang,
            'mock': True,
            'provider': 'mock',
        }

    body: dict[str, Any] = {
        'q': text,
        'target': target_lang,
        'format': 'text',
    }
    if source_lang != 'auto':
        body['source'] = source_lang

    try:
        resp = requests.post(
            TRANSLATE_URL,
            params={'key': creds['api_key']},
            json=body,
            timeout=5,
        )
        # Surface Google error body for ops
        if resp.status_code >= 400:
            detail = ''
            try:
                err = resp.json().get('error') or {}
                detail = err.get('message') or resp.text[:300]
            except Exception:
                detail = resp.text[:300]
            logger.warning('google translate http=%s detail=%s', resp.status_code, detail)
            return {
                'translated': '',
                'target': target_lang,
                'source': source_lang,
                'mock': False,
                'provider': 'google',
                'error': detail or f'http_{resp.status_code}',
            }

        data = resp.json().get('data') or {}
        rows = data.get('translations') or []
        if not rows:
            return {
                'translated': '',
                'target': target_lang,
                'source': source_lang,
                'mock': False,
                'provider': 'google',
                'error': 'empty_response',
            }
        row = rows[0]
        translated = row.get('translatedText') or ''
        # Google may HTML-escape entities even with format=text
        translated = html.unescape(translated)
        detected = row.get('detectedSourceLanguage') or None
        return {
            'translated': translated,
            'target': target_lang,
            'source': source_lang,
            'detected_source': detected,
            'mock': False,
            'provider': 'google',
        }
    except requests.Timeout:
        logger.exception('google translate timeout')
        return {
            'translated': '',
            'target': target_lang,
            'source': source_lang,
            'mock': False,
            'provider': 'google',
            'error': 'timeout',
        }
    except Exception as exc:
        logger.exception('google translate failed')
        return {
            'translated': '',
            'target': target_lang,
            'source': source_lang,
            'mock': False,
            'provider': 'google',
            'error': str(exc)[:300],
        }


def test_connection(sample: str = 'Hello') -> dict[str, Any]:
    """Admin connectivity check — never falls back to mock."""
    result = translate_text(sample, target='zh-CN', source='en', allow_mock=False)
    ok = bool(result.get('translated')) and not result.get('mock') and not result.get('error')
    return {
        'ok': ok,
        'sample': sample,
        **result,
    }
