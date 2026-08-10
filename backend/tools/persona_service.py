"""
Persona Identity verification (hosted Inquiry).

Docs: https://docs.withpersona.com/api-keys
"""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

PERSONA_API = 'https://withpersona.com/api/v1'


def _cfg() -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('persona')
    return {
        'enabled': cfg.get('enabled', False),
        'api_key': get_provider_field('persona', 'api_key') or '',
        'inquiry_template_id': get_provider_field('persona', 'inquiry_template_id') or cfg.get('inquiry_template_id') or '',
        'api_version': cfg.get('api_version') or '2025-10-27',
        'webhook_secret': get_provider_field('persona', 'webhook_secret') or '',
        'environment': cfg.get('environment') or 'sandbox',
    }


def persona_configured() -> bool:
    c = _cfg()
    return bool(c['api_key'] and c['inquiry_template_id'])


def create_inquiry(reference_id: str, note: str = '') -> dict[str, Any]:
    c = _cfg()
    if not persona_configured():
        # Capability stub: return sandbox-style local inquiry id for FE flow testing
        return {
            'ok': True,
            'mock': True,
            'inquiry_id': f'inq_mock_{reference_id}',
            'status': 'created',
            'template_id': c.get('inquiry_template_id') or 'itmpl_mock',
            'hosted_url': '',
            'inquiry_session_token': '',
        }
    try:
        resp = requests.post(
            f'{PERSONA_API}/inquiries',
            headers={
                'Authorization': f'Bearer {c["api_key"]}',
                'Persona-Version': c['api_version'],
                'Content-Type': 'application/json',
            },
            json={
                'data': {
                    'attributes': {
                        'inquiry-template-id': c['inquiry_template_id'],
                        'reference-id': str(reference_id),
                        'note': note or '',
                    }
                }
            },
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            err = (data.get('errors') or [{}])[0]
            return {'ok': False, 'error': err.get('title') or resp.text[:300]}
        inq = data.get('data') or {}
        attrs = inq.get('attributes') or {}
        return {
            'ok': True,
            'mock': False,
            'inquiry_id': inq.get('id') or '',
            'status': attrs.get('status') or 'created',
            'template_id': c['inquiry_template_id'],
            'hosted_url': f"https://withpersona.com/verify?inquiry-id={inq.get('id') or ''}",
            'inquiry_session_token': attrs.get('session-token') or attrs.get('session_token') or '',
        }
    except Exception as exc:
        logger.exception('persona create inquiry failed')
        return {'ok': False, 'error': str(exc)[:300]}


def parse_webhook_event(payload: dict) -> dict[str, Any]:
    """Extract inquiry id + status from Persona webhook payload."""
    data = (payload or {}).get('data') or payload or {}
    attrs = data.get('attributes') or {}
    name = (payload or {}).get('name') or attrs.get('name') or ''
    inquiry_id = data.get('id') or attrs.get('inquiry-id') or attrs.get('inquiry_id') or ''
    status = attrs.get('status') or ''
    # common events: inquiry.completed / inquiry.approved / inquiry.failed
    approved = status in ('approved', 'completed') or 'approved' in name or 'completed' in name
    declined = status in ('failed', 'declined', 'needs_review') or 'failed' in name
    return {
        'inquiry_id': inquiry_id,
        'status': status or name,
        'approved': approved and not declined,
        'declined': declined,
        'reference_id': attrs.get('reference-id') or attrs.get('reference_id') or '',
    }
