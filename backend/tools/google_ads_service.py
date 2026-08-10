"""
Google Ads API (REST) — list campaigns + performance metrics.

Official docs:
- Auth headers: https://developers.google.com/google-ads/api/rest/auth
- Search: POST https://googleads.googleapis.com/{version}/customers/{cid}/googleAds:search
- Get campaigns sample:
  https://developers.google.com/google-ads/api/samples/get-campaigns

Required credentials (admin「三方配置 → Google Ads」):
  developer_token, client_id, client_secret, refresh_token, customer_id
  optional: login_customer_id (MCC), api_version (default v19)
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

TOKEN_URL = 'https://oauth2.googleapis.com/token'
DEFAULT_API_VERSION = 'v19'

CAMPAIGN_QUERY = """
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type,
  campaign.bidding_strategy_type,
  metrics.impressions,
  metrics.clicks,
  metrics.cost_micros,
  metrics.conversions,
  metrics.ctr,
  metrics.average_cpc
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
ORDER BY campaign.id
""".strip()

CAMPAIGN_QUERY_LIGHT = """
SELECT
  campaign.id,
  campaign.name,
  campaign.status,
  campaign.advertising_channel_type
FROM campaign
ORDER BY campaign.id
""".strip()


def _digits(value: str | None) -> str:
    return re.sub(r'\D', '', str(value or ''))


def get_google_ads_config(app_id: str | None = None) -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field, provider_enabled
    from tools.tools import getEnvConfig

    cfg = get_raw_provider_config('google_ads', app_id)
    enabled = provider_enabled('google_ads', app_id, default=False)
    if cfg.get('enabled') is False:
        enabled = False

    return {
        'enabled': enabled,
        'developer_token': get_provider_field(
            'google_ads', 'developer_token', app_id, env_keys=('GOOGLE_ADS_DEVELOPER_TOKEN',),
        ),
        'client_id': get_provider_field(
            'google_ads', 'client_id', app_id, env_keys=('GOOGLE_ADS_CLIENT_ID',),
        ),
        'client_secret': get_provider_field(
            'google_ads', 'client_secret', app_id, env_keys=('GOOGLE_ADS_CLIENT_SECRET',),
        ),
        'refresh_token': get_provider_field(
            'google_ads', 'refresh_token', app_id, env_keys=('GOOGLE_ADS_REFRESH_TOKEN',),
        ),
        'customer_id': _digits(
            get_provider_field('google_ads', 'customer_id', app_id, env_keys=('GOOGLE_ADS_CUSTOMER_ID',))
            or cfg.get('customer_id')
        ),
        'login_customer_id': _digits(
            get_provider_field(
                'google_ads', 'login_customer_id', app_id, env_keys=('GOOGLE_ADS_LOGIN_CUSTOMER_ID',),
            )
            or cfg.get('login_customer_id')
        ),
        'api_version': (
            (cfg.get('api_version') or getEnvConfig('GOOGLE_ADS_API_VERSION') or DEFAULT_API_VERSION)
            .strip()
            or DEFAULT_API_VERSION
        ),
    }


def is_configured(app_id: str | None = None) -> bool:
    c = get_google_ads_config(app_id)
    return bool(
        c['developer_token'] and c['client_id'] and c['client_secret']
        and c['refresh_token'] and c['customer_id']
    )


def refresh_access_token(cfg: dict | None = None, app_id: str | None = None) -> dict:
    cfg = cfg or get_google_ads_config(app_id)
    if not (cfg.get('client_id') and cfg.get('client_secret') and cfg.get('refresh_token')):
        return {'ok': False, 'error': 'oauth_not_configured'}
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                'grant_type': 'refresh_token',
                'client_id': cfg['client_id'],
                'client_secret': cfg['client_secret'],
                'refresh_token': cfg['refresh_token'],
            },
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400 or not data.get('access_token'):
            err = data.get('error_description') or data.get('error') or f'http_{resp.status_code}'
            return {'ok': False, 'error': str(err)}
        return {
            'ok': True,
            'access_token': data['access_token'],
            'expires_in': data.get('expires_in'),
            'token_type': data.get('token_type') or 'Bearer',
        }
    except Exception as exc:
        logger.exception('google ads token refresh failed')
        return {'ok': False, 'error': str(exc)[:300]}


def _ads_headers(cfg: dict, access_token: str) -> dict:
    headers = {
        'Authorization': f'Bearer {access_token}',
        'developer-token': cfg['developer_token'],
        'Content-Type': 'application/json',
    }
    if cfg.get('login_customer_id'):
        headers['login-customer-id'] = cfg['login_customer_id']
    return headers


def search_google_ads(query: str, app_id: str | None = None, page_size: int = 1000) -> dict:
    """Execute GAQL via googleAds:search. Returns {ok, rows, error?}."""
    cfg = get_google_ads_config(app_id)
    if not is_configured(app_id):
        return {'ok': False, 'error': 'not_configured', 'rows': []}
    if cfg.get('enabled') is False and not cfg.get('developer_token'):
        return {'ok': False, 'error': 'disabled', 'rows': []}

    token = refresh_access_token(cfg, app_id)
    if not token.get('ok'):
        return {'ok': False, 'error': token.get('error') or 'token_failed', 'rows': []}

    version = cfg.get('api_version') or DEFAULT_API_VERSION
    if not version.startswith('v'):
        version = f'v{version}'
    customer_id = cfg['customer_id']
    url = f'https://googleads.googleapis.com/{version}/customers/{customer_id}/googleAds:search'

    rows: list[dict] = []
    page_token = None
    try:
        while True:
            body: dict[str, Any] = {'query': query, 'pageSize': min(page_size, 10000)}
            if page_token:
                body['pageToken'] = page_token
            resp = requests.post(
                url,
                headers=_ads_headers(cfg, token['access_token']),
                json=body,
                timeout=60,
            )
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                err = ''
                try:
                    err = (
                        (data.get('error') or {}).get('message')
                        or (data.get('error') or {}).get('status')
                        or resp.text[:400]
                    )
                except Exception:
                    err = resp.text[:400]
                logger.warning('google ads search http=%s err=%s', resp.status_code, err)
                return {'ok': False, 'error': err or f'http_{resp.status_code}', 'rows': rows}

            for r in data.get('results') or []:
                rows.append(r)
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        return {
            'ok': True,
            'rows': rows,
            'customer_id': customer_id,
            'count': len(rows),
        }
    except Exception as exc:
        logger.exception('google ads search failed')
        return {'ok': False, 'error': str(exc)[:300], 'rows': rows}


def _parse_campaign_row(row: dict) -> dict:
    camp = row.get('campaign') or {}
    metrics = row.get('metrics') or {}
    campaign_id = str(camp.get('id') or '')
    cost_micros = int(metrics.get('costMicros') or metrics.get('cost_micros') or 0)
    return {
        'campaign_id': campaign_id,
        'name': camp.get('name') or '',
        'status': camp.get('status') or '',
        'channel_type': camp.get('advertisingChannelType') or camp.get('advertising_channel_type') or '',
        'bidding_strategy_type': (
            camp.get('biddingStrategyType') or camp.get('bidding_strategy_type') or ''
        ),
        'impressions': int(metrics.get('impressions') or 0),
        'clicks': int(metrics.get('clicks') or 0),
        'cost_micros': cost_micros,
        'cost': round(cost_micros / 1_000_000, 4) if cost_micros else 0.0,
        'conversions': float(metrics.get('conversions') or 0),
        'ctr': float(metrics.get('ctr') or 0),
        'average_cpc': float(metrics.get('averageCpc') or metrics.get('average_cpc') or 0),
        'raw': row,
    }


def fetch_campaigns(app_id: str | None = None, with_metrics: bool = True) -> dict:
    query = CAMPAIGN_QUERY if with_metrics else CAMPAIGN_QUERY_LIGHT
    result = search_google_ads(query, app_id=app_id)
    if not result.get('ok'):
        # Fallback: light query without metrics (some accounts / access levels)
        if with_metrics and result.get('error') and 'not_configured' not in str(result.get('error')):
            light = search_google_ads(CAMPAIGN_QUERY_LIGHT, app_id=app_id)
            if light.get('ok'):
                campaigns = [_parse_campaign_row(r) for r in light.get('rows') or []]
                # Deduplicate by campaign_id (metrics query can duplicate across date segments)
                campaigns = _dedupe_campaigns(campaigns)
                return {
                    'ok': True,
                    'campaigns': campaigns,
                    'customer_id': light.get('customer_id'),
                    'metrics': False,
                    'warning': result.get('error'),
                }
        return {
            'ok': False,
            'error': result.get('error'),
            'campaigns': [],
            'customer_id': result.get('customer_id'),
        }

    campaigns = _dedupe_campaigns([_parse_campaign_row(r) for r in result.get('rows') or []])
    return {
        'ok': True,
        'campaigns': campaigns,
        'customer_id': result.get('customer_id'),
        'metrics': with_metrics,
        'count': len(campaigns),
    }


def _dedupe_campaigns(items: list[dict]) -> list[dict]:
    """Merge metric rows that share campaign_id (date-segmented search)."""
    by_id: dict[str, dict] = {}
    for item in items:
        cid = item.get('campaign_id') or ''
        if not cid:
            continue
        if cid not in by_id:
            by_id[cid] = dict(item)
            continue
        cur = by_id[cid]
        cur['impressions'] = int(cur.get('impressions') or 0) + int(item.get('impressions') or 0)
        cur['clicks'] = int(cur.get('clicks') or 0) + int(item.get('clicks') or 0)
        cur['cost_micros'] = int(cur.get('cost_micros') or 0) + int(item.get('cost_micros') or 0)
        cur['conversions'] = float(cur.get('conversions') or 0) + float(item.get('conversions') or 0)
        cur['cost'] = round(cur['cost_micros'] / 1_000_000, 4) if cur['cost_micros'] else 0.0
        if cur['impressions']:
            cur['ctr'] = cur['clicks'] / cur['impressions']
        if cur['clicks']:
            cur['average_cpc'] = cur['cost_micros'] / cur['clicks']
    return sorted(by_id.values(), key=lambda x: x.get('campaign_id') or '')


def sync_campaigns_to_db(app_id: str, with_metrics: bool = True) -> dict:
    """Fetch from Google Ads API and upsert GoogleAdsCampaign rows."""
    from models.models import GoogleAdsCampaign

    fetched = fetch_campaigns(app_id=app_id, with_metrics=with_metrics)
    if not fetched.get('ok'):
        return fetched

    customer_id = fetched.get('customer_id') or ''
    now = timezone.now()
    upserted = 0
    for c in fetched.get('campaigns') or []:
        obj, _ = GoogleAdsCampaign.objects.update_or_create(
            app_id=app_id,
            customer_id=customer_id,
            campaign_id=str(c['campaign_id']),
            defaults={
                'name': (c.get('name') or '')[:256],
                'status': (c.get('status') or '')[:32],
                'channel_type': (c.get('channel_type') or '')[:64],
                'bidding_strategy_type': (c.get('bidding_strategy_type') or '')[:64],
                'impressions': int(c.get('impressions') or 0),
                'clicks': int(c.get('clicks') or 0),
                'cost_micros': int(c.get('cost_micros') or 0),
                'conversions': float(c.get('conversions') or 0),
                'ctr': float(c.get('ctr') or 0),
                'average_cpc': float(c.get('average_cpc') or 0),
                'metrics_window': 'LAST_30_DAYS',
                'raw': c.get('raw') or {},
                'synced_at': now,
            },
        )
        upserted += 1

    return {
        'ok': True,
        'synced': upserted,
        'customer_id': customer_id,
        'metrics': fetched.get('metrics', True),
        'warning': fetched.get('warning'),
        'synced_at': now.isoformat(),
    }


def test_connection(app_id: str | None = None) -> dict:
    """Admin connectivity: refresh token + light campaign list."""
    cfg = get_google_ads_config(app_id)
    if not is_configured(app_id):
        return {'ok': False, 'error': 'not_configured', 'sample': None}
    token = refresh_access_token(cfg, app_id)
    if not token.get('ok'):
        return {'ok': False, 'error': token.get('error') or 'token_failed'}
    fetched = fetch_campaigns(app_id=app_id, with_metrics=False)
    if not fetched.get('ok'):
        return {'ok': False, 'error': fetched.get('error') or 'search_failed', 'token_ok': True}
    sample = (fetched.get('campaigns') or [{}])[0] if fetched.get('campaigns') else {}
    return {
        'ok': True,
        'token_ok': True,
        'customer_id': fetched.get('customer_id'),
        'campaign_count': len(fetched.get('campaigns') or []),
        'sample_campaign_id': sample.get('campaign_id'),
        'sample_campaign_name': sample.get('name'),
    }


def serialize_campaign_row(row) -> dict:
    return {
        'id': row.id,
        'app_id': row.app_id,
        'customer_id': row.customer_id,
        'campaign_id': row.campaign_id,
        'name': row.name,
        'status': row.status,
        'channel_type': row.channel_type,
        'bidding_strategy_type': row.bidding_strategy_type,
        'impressions': row.impressions,
        'clicks': row.clicks,
        'cost_micros': row.cost_micros,
        'cost': round((row.cost_micros or 0) / 1_000_000, 4),
        'conversions': float(row.conversions or 0),
        'ctr': float(row.ctr or 0),
        'average_cpc': float(row.average_cpc or 0),
        'metrics_window': row.metrics_window,
        'synced_at': row.synced_at.isoformat() if row.synced_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
    }
