"""
Meta Marketing API (Facebook Ads) — campaigns + insights.

Official:
https://developers.facebook.com/docs/marketing-api/reference/ad-account/campaigns/

GET https://graph.facebook.com/{version}/act_{AD_ACCOUNT_ID}/campaigns
  ?fields=id,name,status,effective_status,objective,insights{...}
  &access_token=TOKEN
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = 'v21.0'
GRAPH_HOST = 'https://graph.facebook.com'

CAMPAIGN_FIELDS = (
    'id,name,status,effective_status,objective,'
    'insights.date_preset(last_30d){impressions,clicks,spend,ctr,cpc,actions,reach}'
)


def _act_id(value: str | None) -> str:
    raw = re.sub(r'\s+', '', str(value or ''))
    if not raw:
        return ''
    if raw.startswith('act_'):
        return raw
    digits = re.sub(r'\D', '', raw)
    return f'act_{digits}' if digits else ''


def get_facebook_ads_config(app_id: str | None = None) -> dict:
    from tools.provider_helpers import get_raw_provider_config, get_provider_field, provider_enabled
    from tools.tools import getEnvConfig

    cfg = get_raw_provider_config('facebook_ads', app_id)
    enabled = provider_enabled('facebook_ads', app_id, default=False)
    if cfg.get('enabled') is False:
        enabled = False

    return {
        'enabled': enabled,
        'access_token': get_provider_field(
            'facebook_ads', 'access_token', app_id, env_keys=('FACEBOOK_ADS_ACCESS_TOKEN', 'META_ADS_ACCESS_TOKEN'),
        ),
        'ad_account_id': _act_id(
            get_provider_field(
                'facebook_ads', 'ad_account_id', app_id,
                env_keys=('FACEBOOK_ADS_ACCOUNT_ID', 'META_ADS_ACCOUNT_ID'),
            )
            or cfg.get('ad_account_id')
        ),
        'pixel_id': get_provider_field(
            'facebook_ads', 'pixel_id', app_id, env_keys=('FACEBOOK_PIXEL_ID',),
        ),
        'api_version': (
            (cfg.get('api_version') or getEnvConfig('FACEBOOK_ADS_API_VERSION') or DEFAULT_API_VERSION)
            .strip()
            or DEFAULT_API_VERSION
        ),
    }


def is_configured(app_id: str | None = None) -> bool:
    c = get_facebook_ads_config(app_id)
    return bool(c.get('access_token') and c.get('ad_account_id'))


def _parse_insight(insights_block: dict | None) -> dict:
    data = (insights_block or {}).get('data') or []
    if not data:
        return {
            'impressions': 0, 'clicks': 0, 'spend': 0.0, 'ctr': 0.0, 'cpc': 0.0,
            'conversions': 0.0, 'reach': 0,
        }
    row = data[0] or {}
    conversions = 0.0
    for action in row.get('actions') or []:
        at = (action.get('action_type') or '').lower()
        if at in ('offsite_conversion.fb_pixel_purchase', 'purchase', 'omni_purchase', 'lead'):
            try:
                conversions += float(action.get('value') or 0)
            except (TypeError, ValueError):
                pass
    return {
        'impressions': int(float(row.get('impressions') or 0)),
        'clicks': int(float(row.get('clicks') or 0)),
        'spend': float(row.get('spend') or 0),
        'ctr': float(row.get('ctr') or 0) / 100.0 if row.get('ctr') and float(row.get('ctr') or 0) > 1 else float(row.get('ctr') or 0),
        'cpc': float(row.get('cpc') or 0),
        'conversions': conversions,
        'reach': int(float(row.get('reach') or 0)),
    }


def fetch_campaigns(app_id: str | None = None) -> dict:
    cfg = get_facebook_ads_config(app_id)
    if not is_configured(app_id):
        return {'ok': False, 'error': 'not_configured', 'campaigns': []}

    version = cfg['api_version']
    if not version.startswith('v'):
        version = f'v{version}'
    act = cfg['ad_account_id']
    campaigns = []
    next_url = f'{GRAPH_HOST}/{version}/{act}/campaigns'
    params: dict[str, Any] | None = {
        'access_token': cfg['access_token'],
        'fields': CAMPAIGN_FIELDS,
        'limit': 100,
        'effective_status': '["ACTIVE","PAUSED","ARCHIVED"]',
    }

    try:
        while next_url:
            if params is not None:
                resp = requests.get(next_url, params=params, timeout=45)
            else:
                resp = requests.get(next_url, timeout=45)
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400 or data.get('error'):
                err = (data.get('error') or {}).get('message') or resp.text[:400]
                logger.warning('facebook ads campaigns http=%s err=%s', resp.status_code, err)
                return {'ok': False, 'error': err or f'http_{resp.status_code}', 'campaigns': campaigns}

            for item in data.get('data') or []:
                insight = _parse_insight(item.get('insights'))
                campaigns.append({
                    'campaign_id': str(item.get('id') or ''),
                    'name': item.get('name') or '',
                    'status': item.get('effective_status') or item.get('status') or '',
                    'objective': item.get('objective') or '',
                    'impressions': insight['impressions'],
                    'clicks': insight['clicks'],
                    'spend': insight['spend'],
                    'cost': insight['spend'],
                    'ctr': insight['ctr'],
                    'cpc': insight['cpc'],
                    'conversions': insight['conversions'],
                    'reach': insight['reach'],
                    'raw': item,
                })

            next_url = (data.get('paging') or {}).get('next')
            params = None
            if len(campaigns) >= 500:
                break

        return {
            'ok': True,
            'campaigns': campaigns,
            'ad_account_id': act,
            'count': len(campaigns),
        }
    except Exception as exc:
        logger.exception('facebook ads fetch failed')
        return {'ok': False, 'error': str(exc)[:300], 'campaigns': campaigns}


def sync_campaigns_to_db(app_id: str) -> dict:
    from models.models import FacebookAdsCampaign

    fetched = fetch_campaigns(app_id=app_id)
    if not fetched.get('ok'):
        return fetched

    act = fetched.get('ad_account_id') or ''
    now = timezone.now()
    upserted = 0
    for c in fetched.get('campaigns') or []:
        FacebookAdsCampaign.objects.update_or_create(
            app_id=app_id,
            ad_account_id=act,
            campaign_id=str(c['campaign_id']),
            defaults={
                'name': (c.get('name') or '')[:256],
                'status': (c.get('status') or '')[:64],
                'objective': (c.get('objective') or '')[:64],
                'impressions': int(c.get('impressions') or 0),
                'clicks': int(c.get('clicks') or 0),
                'spend': float(c.get('spend') or 0),
                'conversions': float(c.get('conversions') or 0),
                'ctr': float(c.get('ctr') or 0),
                'cpc': float(c.get('cpc') or 0),
                'reach': int(c.get('reach') or 0),
                'metrics_window': 'last_30d',
                'raw': c.get('raw') or {},
                'synced_at': now,
            },
        )
        upserted += 1

    return {
        'ok': True,
        'synced': upserted,
        'ad_account_id': act,
        'synced_at': now.isoformat(),
    }


def test_connection(app_id: str | None = None) -> dict:
    cfg = get_facebook_ads_config(app_id)
    if not is_configured(app_id):
        return {'ok': False, 'error': 'not_configured'}
    version = cfg['api_version']
    if not version.startswith('v'):
        version = f'v{version}'
    # Lightweight: read account name
    url = f'{GRAPH_HOST}/{version}/{cfg["ad_account_id"]}'
    try:
        resp = requests.get(
            url,
            params={'access_token': cfg['access_token'], 'fields': 'id,name,account_status,currency'},
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400 or data.get('error'):
            err = (data.get('error') or {}).get('message') or resp.text[:300]
            return {'ok': False, 'error': err}
        fetched = fetch_campaigns(app_id)
        sample = (fetched.get('campaigns') or [{}])[0] if fetched.get('ok') else {}
        return {
            'ok': True,
            'ad_account_id': data.get('id') or cfg['ad_account_id'],
            'ad_account_name': data.get('name'),
            'currency': data.get('currency'),
            'campaign_count': len(fetched.get('campaigns') or []) if fetched.get('ok') else 0,
            'sample_campaign_id': sample.get('campaign_id'),
            'sample_campaign_name': sample.get('name'),
            'fetch_error': None if fetched.get('ok') else fetched.get('error'),
        }
    except Exception as exc:
        logger.exception('facebook ads test failed')
        return {'ok': False, 'error': str(exc)[:300]}


def serialize_campaign_row(row) -> dict:
    return {
        'id': row.id,
        'app_id': row.app_id,
        'ad_account_id': row.ad_account_id,
        'campaign_id': row.campaign_id,
        'name': row.name,
        'status': row.status,
        'objective': row.objective,
        'impressions': row.impressions,
        'clicks': row.clicks,
        'spend': float(row.spend or 0),
        'cost': float(row.spend or 0),
        'conversions': float(row.conversions or 0),
        'ctr': float(row.ctr or 0),
        'cpc': float(row.cpc or 0),
        'reach': row.reach,
        'metrics_window': row.metrics_window,
        'synced_at': row.synced_at.isoformat() if row.synced_at else None,
        'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        'platform': 'facebook',
    }
