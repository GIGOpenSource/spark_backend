"""
IAP verification — App Store Server API + Google Play Developer API.

Docs:
- https://developer.apple.com/documentation/appstoreserverapi
- https://developers.google.com/android-publisher/api-ref/rest/v3/purchases.subscriptionsv2/get

Uses ProviderConfig apple_iap / google_play (admin 三方配置).
When credentials missing and allow_mock=True, returns mock_ok for controlled demos.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

APPLE_PROD = 'https://api.storekit.itunes.apple.com'
APPLE_SANDBOX = 'https://api.storekit-sandbox.itunes.apple.com'


def _apple_cfg(app_id: str | None) -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('apple_iap', app_id)
    return {
        'enabled': cfg.get('enabled', True),
        'environment': (cfg.get('environment') or 'Sandbox').strip(),
        'bundle_id': get_provider_field('apple_iap', 'bundle_id', app_id) or cfg.get('bundle_id') or '',
        'issuer_id': get_provider_field('apple_iap', 'issuer_id', app_id) or '',
        'key_id': get_provider_field('apple_iap', 'key_id', app_id) or '',
        'private_key': get_provider_field('apple_iap', 'private_key', app_id) or '',
        'app_apple_id': get_provider_field('apple_iap', 'app_apple_id', app_id) or cfg.get('app_apple_id') or '',
    }


def _play_cfg(app_id: str | None) -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field
    cfg = get_raw_provider_config('google_play', app_id)
    return {
        'enabled': cfg.get('enabled', True),
        'package_name': get_provider_field('google_play', 'package_name', app_id) or cfg.get('package_name') or '',
        'service_account_json': get_provider_field('google_play', 'service_account_json', app_id) or '',
    }


def apple_configured(app_id: str | None = None) -> bool:
    c = _apple_cfg(app_id)
    return bool(c['issuer_id'] and c['key_id'] and c['private_key'] and c['bundle_id'])


def play_configured(app_id: str | None = None) -> bool:
    c = _play_cfg(app_id)
    return bool(c['package_name'] and c['service_account_json'])


def _apple_bearer(cfg: dict) -> str | None:
    """Create ES256 JWT for App Store Server API."""
    try:
        import jwt
    except ImportError:
        logger.error('PyJWT not installed')
        return None
    now = int(time.time())
    payload = {
        'iss': cfg['issuer_id'],
        'iat': now,
        'exp': now + 3500,
        'aud': 'appstoreconnect-v1',
        'bid': cfg['bundle_id'],
    }
    headers = {'alg': 'ES256', 'kid': cfg['key_id'], 'typ': 'JWT'}
    key = cfg['private_key']
    if '\\n' in key:
        key = key.replace('\\n', '\n')
    try:
        return jwt.encode(payload, key, algorithm='ES256', headers=headers)
    except Exception:
        logger.exception('apple jwt encode failed')
        return None


def verify_apple_transaction(app_id: str | None, transaction_id: str) -> dict[str, Any]:
    cfg = _apple_cfg(app_id)
    if not apple_configured(app_id):
        return {'ok': False, 'error': 'apple_iap_not_configured'}
    token = _apple_bearer(cfg)
    if not token:
        return {'ok': False, 'error': 'apple_jwt_failed'}
    env = (cfg.get('environment') or 'Sandbox').lower()
    bases = [APPLE_SANDBOX, APPLE_PROD] if env == 'sandbox' else [APPLE_PROD, APPLE_SANDBOX]
    last_err = ''
    for base in bases:
        url = f'{base}/inApps/v1/transactions/{transaction_id}'
        try:
            resp = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=20)
            if resp.status_code == 404:
                last_err = 'transaction_not_found'
                continue
            if resp.status_code >= 400:
                last_err = resp.text[:300]
                continue
            data = resp.json()
            # signedTransactionInfo is JWS — decode payload without verify of Apple root for capability layer
            signed = data.get('signedTransactionInfo') or ''
            info = _decode_jws_payload(signed) if signed else data
            bundle = info.get('bundleId') or info.get('bundle_id')
            if bundle and cfg['bundle_id'] and bundle != cfg['bundle_id']:
                return {'ok': False, 'error': 'bundle_mismatch', 'info': info}
            return {
                'ok': True,
                'platform': 'ios',
                'transaction_id': str(info.get('transactionId') or transaction_id),
                'original_transaction_id': str(info.get('originalTransactionId') or ''),
                'product_id': info.get('productId') or info.get('product_id') or '',
                'environment': info.get('environment') or cfg['environment'],
                'info': info,
            }
        except Exception as exc:
            last_err = str(exc)[:300]
            logger.exception('apple verify failed')
    return {'ok': False, 'error': last_err or 'apple_verify_failed'}


def _decode_jws_payload(jws: str) -> dict:
    try:
        import jwt
        # App Store Server API returns ES256 JWS; verify with Apple certs in full prod.
        # Capability layer: decode without signature verify, then re-check via getTransactionInfo API path.
        return jwt.decode(jws, options={'verify_signature': False}) or {}
    except Exception:
        parts = (jws or '').split('.')
        if len(parts) < 2:
            return {}
        import base64
        pad = '=' * (-len(parts[1]) % 4)
        try:
            return json.loads(base64.urlsafe_b64decode(parts[1] + pad).decode('utf-8'))
        except Exception:
            return {}


def _play_access_token(sa_json: str) -> str | None:
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests as ga_requests
        info = json.loads(sa_json) if isinstance(sa_json, str) else sa_json
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/androidpublisher'],
        )
        creds.refresh(ga_requests.Request())
        return creds.token
    except Exception:
        logger.exception('play access token failed')
        return None


def verify_google_purchase(
    app_id: str | None,
    *,
    product_id: str,
    purchase_token: str,
    subscription: bool = True,
) -> dict[str, Any]:
    cfg = _play_cfg(app_id)
    if not play_configured(app_id):
        return {'ok': False, 'error': 'google_play_not_configured'}
    token = _play_access_token(cfg['service_account_json'])
    if not token:
        return {'ok': False, 'error': 'play_token_failed'}
    pkg = cfg['package_name']
    if subscription:
        url = (
            f'https://androidpublisher.googleapis.com/androidpublisher/v3/'
            f'applications/{pkg}/purchases/subscriptionsv2/tokens/{purchase_token}'
        )
    else:
        url = (
            f'https://androidpublisher.googleapis.com/androidpublisher/v3/'
            f'applications/{pkg}/purchases/products/{product_id}/tokens/{purchase_token}'
        )
    try:
        resp = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=20)
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            return {'ok': False, 'error': (data.get('error') or {}).get('message') or resp.text[:300]}
        # subscriptionsv2: lineItems[0].productId
        pid = product_id
        if subscription:
            items = data.get('lineItems') or []
            if items:
                pid = items[0].get('productId') or product_id
        else:
            # products API uses productId in path; purchaseState 0 = purchased
            if data.get('purchaseState') not in (0, '0', None):
                if data.get('purchaseState') == 1:
                    return {'ok': False, 'error': 'purchase_canceled', 'info': data}
        return {
            'ok': True,
            'platform': 'android',
            'product_id': pid,
            'purchase_token': purchase_token,
            'order_id': data.get('orderId') or data.get('latestOrderId') or '',
            'info': data,
        }
    except Exception as exc:
        logger.exception('play verify failed')
        return {'ok': False, 'error': str(exc)[:300]}


def verify_purchase_payload(app_id: str | None, data: dict, *, allow_mock: bool = True) -> dict[str, Any]:
    """
    Normalize client purchase payload and verify.

    Expected fields:
      platform: ios|android|mock
      product_id
      transaction_id (ios) OR purchase_token (android)
      subscription: bool (android)
    """
    platform = (data.get('platform') or 'mock').strip().lower()
    product_id = (data.get('product_id') or '').strip()
    if not product_id:
        return {'ok': False, 'error': 'product_id required'}

    if platform in ('mock', 'h5', 'web'):
        if not allow_mock:
            return {'ok': False, 'error': 'mock_not_allowed'}
        return {
            'ok': True,
            'mock': True,
            'platform': 'mock',
            'product_id': product_id,
            'transaction_id': data.get('transaction_id') or f'mock_{int(time.time())}',
        }

    if platform in ('ios', 'apple'):
        tid = (data.get('transaction_id') or data.get('transactionId') or '').strip()
        if not tid:
            return {'ok': False, 'error': 'transaction_id required'}
        if not apple_configured(app_id):
            if allow_mock:
                return {'ok': True, 'mock': True, 'platform': 'ios', 'product_id': product_id,
                        'transaction_id': tid, 'warning': 'apple_iap_not_configured_fallback_mock'}
            return {'ok': False, 'error': 'apple_iap_not_configured'}
        result = verify_apple_transaction(app_id, tid)
        if result.get('ok') and result.get('product_id') and result['product_id'] != product_id:
            # prefer store product id
            result['client_product_id'] = product_id
            product_id = result['product_id']
            result['product_id'] = product_id
        return result

    if platform in ('android', 'google', 'play'):
        ptoken = (data.get('purchase_token') or data.get('purchaseToken') or '').strip()
        if not ptoken:
            return {'ok': False, 'error': 'purchase_token required'}
        if not play_configured(app_id):
            if allow_mock:
                return {'ok': True, 'mock': True, 'platform': 'android', 'product_id': product_id,
                        'purchase_token': ptoken, 'warning': 'google_play_not_configured_fallback_mock'}
            return {'ok': False, 'error': 'google_play_not_configured'}
        is_sub = data.get('subscription')
        if is_sub is None:
            is_sub = True
        return verify_google_purchase(
            app_id, product_id=product_id, purchase_token=ptoken, subscription=bool(is_sub),
        )

    return {'ok': False, 'error': f'unsupported_platform:{platform}'}
