"""
Twilio Verify SMS OTP.

Docs: https://www.twilio.com/docs/verify/api
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

E164_RE = re.compile(r'^\+[1-9]\d{6,14}$')


def _cfg() -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('twilio_sms')
    return {
        'enabled': cfg.get('enabled', False),
        'account_sid': get_provider_field('twilio_sms', 'account_sid') or '',
        'auth_token': get_provider_field('twilio_sms', 'auth_token') or '',
        'verify_service_sid': get_provider_field('twilio_sms', 'verify_service_sid') or '',
        'from_number': get_provider_field('twilio_sms', 'from_number') or '',
    }


def sms_configured() -> bool:
    c = _cfg()
    return bool(c['account_sid'] and c['auth_token'] and c['verify_service_sid'])


def allow_sms_mock() -> bool:
    """Align with bootstrap features.sms_mock: USE_SMS_MOCK or Twilio unset."""
    if bool(getattr(settings, 'USE_SMS_MOCK', False)):
        return True
    return not sms_configured()


def normalize_phone(phone: str) -> str:
    p = (phone or '').strip().replace(' ', '').replace('-', '')
    if p.startswith('00'):
        p = '+' + p[2:]
    # Mainland China mobile without country code
    if re.fullmatch(r'1\d{10}', p):
        return f'+86{p}'
    if p and not p.startswith('+') and p.isdigit():
        p = f'+{p}'
    return p


def valid_e164(phone: str) -> bool:
    return bool(E164_RE.match(phone or ''))


def send_otp(phone: str) -> dict[str, Any]:
    phone = normalize_phone(phone)
    if not valid_e164(phone):
        return {'ok': False, 'error': 'invalid_phone'}
    if not sms_configured():
        if allow_sms_mock():
            return {'ok': True, 'mock': True, 'phone': phone, 'message': 'sms_mock_sent'}
        return {'ok': False, 'error': 'sms_not_configured'}
    c = _cfg()
    try:
        url = f"https://verify.twilio.com/v2/Services/{c['verify_service_sid']}/Verifications"
        resp = requests.post(
            url,
            data={'To': phone, 'Channel': 'sms'},
            auth=(c['account_sid'], c['auth_token']),
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {'ok': False, 'error': data.get('message') or resp.text[:300]}
        return {'ok': True, 'mock': False, 'phone': phone, 'sid': data.get('sid') or ''}
    except Exception as exc:
        logger.exception('twilio send otp failed')
        return {'ok': False, 'error': str(exc)[:300]}


def check_otp(phone: str, code: str) -> dict[str, Any]:
    phone = normalize_phone(phone)
    code = (code or '').strip()
    if not valid_e164(phone) or not code:
        return {'ok': False, 'error': 'invalid_phone_or_code'}
    if not sms_configured():
        if allow_sms_mock() and code == '000000':
            return {'ok': True, 'mock': True, 'phone': phone}
        if allow_sms_mock():
            return {'ok': False, 'error': 'invalid_code', 'hint': 'use 000000 in sms mock'}
        return {'ok': False, 'error': 'sms_not_configured'}
    c = _cfg()
    try:
        url = f"https://verify.twilio.com/v2/Services/{c['verify_service_sid']}/VerificationCheck"
        resp = requests.post(
            url,
            data={'To': phone, 'Code': code},
            auth=(c['account_sid'], c['auth_token']),
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {'ok': False, 'error': data.get('message') or resp.text[:300]}
        if (data.get('status') or '') != 'approved':
            return {'ok': False, 'error': 'invalid_code', 'status': data.get('status')}
        return {'ok': True, 'mock': False, 'phone': phone}
    except Exception as exc:
        logger.exception('twilio check otp failed')
        return {'ok': False, 'error': str(exc)[:300]}


def send_sms(to_phone: str, body: str) -> dict[str, Any]:
    """Programmable SMS (Share My Date). Falls back to mock when verify-only or unconfigured."""
    phone = normalize_phone(to_phone)
    if not valid_e164(phone):
        return {'ok': False, 'error': 'invalid_phone'}
    c = _cfg()
    if not (c['account_sid'] and c['auth_token'] and c['from_number']):
        if allow_sms_mock():
            logger.info('sms mock to=%s body=%s', phone, (body or '')[:80])
            return {'ok': True, 'mock': True, 'phone': phone}
        return {'ok': False, 'error': 'sms_not_configured'}
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{c['account_sid']}/Messages.json"
        resp = requests.post(
            url,
            data={'To': phone, 'From': c['from_number'], 'Body': body},
            auth=(c['account_sid'], c['auth_token']),
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {'ok': False, 'error': data.get('message') or resp.text[:300]}
        return {'ok': True, 'mock': False, 'sid': data.get('sid') or ''}
    except Exception as exc:
        logger.exception('twilio sms failed')
        return {'ok': False, 'error': str(exc)[:300]}
