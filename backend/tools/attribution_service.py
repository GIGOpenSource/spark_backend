"""
Ad attribution: ingest click/install params and resolve against AdLink / campaign caches.

Supports Facebook (fbclid, campaign_id, adset_id, ad_id) and Google (gclid, campaign_id)
plus UTM params. Admin can list / auto-match / manually resolve.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

from django.utils import timezone

logger = logging.getLogger(__name__)

PLATFORM_FACEBOOK = 'facebook'
PLATFORM_GOOGLE = 'google'
PLATFORM_OTHER = 'other'

STATUS_PENDING = 'pending'
STATUS_MATCHED = 'matched'
STATUS_RESOLVED = 'resolved'
STATUS_DISCARDED = 'discarded'


def detect_platform(payload: dict) -> str:
    platform = (payload.get('platform') or payload.get('network') or '').strip().lower()
    if platform in ('facebook', 'fb', 'meta', 'instagram'):
        return PLATFORM_FACEBOOK
    if platform in ('google', 'google_ads', 'adwords', 'gads'):
        return PLATFORM_GOOGLE
    if payload.get('fbclid') or payload.get('fb_campaign_id'):
        return PLATFORM_FACEBOOK
    if payload.get('gclid') or payload.get('gbraid') or payload.get('wbraid'):
        return PLATFORM_GOOGLE
    src = (payload.get('utm_source') or '').lower()
    if 'facebook' in src or 'fb' == src or 'instagram' in src or 'meta' in src:
        return PLATFORM_FACEBOOK
    if 'google' in src:
        return PLATFORM_GOOGLE
    return PLATFORM_OTHER


def parse_deep_link_params(deep_link: str | None) -> dict:
    if not deep_link:
        return {}
    try:
        parsed = urlparse(deep_link)
        qs = parse_qs(parsed.query)
        # also support hash query
        if parsed.fragment and '=' in parsed.fragment:
            frag = parsed.fragment
            if '?' in frag:
                frag = frag.split('?', 1)[1]
            qs.update(parse_qs(frag))
        out = {}
        for k, vals in qs.items():
            if vals:
                out[k] = vals[0]
        return out
    except Exception:
        return {}


def normalize_attribution_payload(data: dict) -> dict:
    """Merge explicit fields + deep_link query into a flat attribution dict."""
    data = dict(data or {})
    from_link = parse_deep_link_params(data.get('deep_link') or data.get('url'))
    merged = {**from_link, **{k: v for k, v in data.items() if v not in (None, '')}}

    campaign_id = (
        merged.get('campaign_id')
        or merged.get('utm_campaign')
        or merged.get('campaignid')
        or merged.get('fb_campaign_id')
        or ''
    )
    adset_id = merged.get('adset_id') or merged.get('adsetid') or merged.get('fb_adset_id') or ''
    ad_id = merged.get('ad_id') or merged.get('adid') or merged.get('fb_ad_id') or ''
    click_id = merged.get('fbclid') or merged.get('gclid') or merged.get('click_id') or ''

    return {
        'platform': detect_platform(merged),
        'campaign_id': str(campaign_id)[:64],
        'adset_id': str(adset_id)[:64],
        'ad_id': str(ad_id)[:64],
        'click_id': str(click_id)[:256],
        'utm_source': str(merged.get('utm_source') or '')[:128],
        'utm_medium': str(merged.get('utm_medium') or '')[:128],
        'utm_campaign': str(merged.get('utm_campaign') or '')[:128],
        'utm_content': str(merged.get('utm_content') or '')[:128],
        'utm_term': str(merged.get('utm_term') or '')[:128],
        'deep_link': str(merged.get('deep_link') or merged.get('url') or '')[:512],
        'tag': str(merged.get('tag') or '')[:64],
        'device_id': str(merged.get('device_id') or merged.get('idfa') or merged.get('gaid') or '')[:128],
        'props': merged,
    }


def ingest_attribution(
    *,
    app_id: str,
    user=None,
    data: dict | None = None,
    auto_match: bool = True,
) -> Any:
    from models.models import AdAttribution

    norm = normalize_attribution_payload(data or {})
    # Skip empty noise
    if not any([
        norm['campaign_id'], norm['click_id'], norm['deep_link'],
        norm['utm_source'], norm['utm_campaign'], norm['tag'],
    ]):
        return None

    row = AdAttribution.objects.create(
        app_id=app_id or 'spark_main',
        user=user if getattr(user, 'id', None) else None,
        platform=norm['platform'],
        status=STATUS_PENDING,
        campaign_id=norm['campaign_id'] or None,
        adset_id=norm['adset_id'] or None,
        ad_id=norm['ad_id'] or None,
        click_id=norm['click_id'] or None,
        utm_source=norm['utm_source'] or None,
        utm_medium=norm['utm_medium'] or None,
        utm_campaign=norm['utm_campaign'] or None,
        utm_content=norm['utm_content'] or None,
        utm_term=norm['utm_term'] or None,
        deep_link=norm['deep_link'] or None,
        tag=norm['tag'] or None,
        device_id=norm['device_id'] or None,
        props=norm.get('props') or {},
    )
    if auto_match:
        try_auto_match(row)
    return row


def try_auto_match(row) -> bool:
    """Match against AdLink / Facebook/Google campaign caches."""
    from models.models import AdLink, FacebookAdsCampaign, GoogleAdsCampaign

    app_id = row.app_id
    matched = False
    campaign_name = ''
    ad_link = None

    if row.campaign_id:
        ad_link = (
            AdLink.objects.filter(app_id=app_id, campaign_id=row.campaign_id, is_active=True)
            .order_by('-id')
            .first()
        )
        if not ad_link and row.tag:
            ad_link = AdLink.objects.filter(app_id=app_id, tag=row.tag, is_active=True).order_by('-id').first()

        if row.platform == PLATFORM_FACEBOOK:
            camp = FacebookAdsCampaign.objects.filter(app_id=app_id, campaign_id=row.campaign_id).first()
            if camp:
                campaign_name = camp.name
                matched = True
        elif row.platform == PLATFORM_GOOGLE:
            camp = GoogleAdsCampaign.objects.filter(app_id=app_id, campaign_id=row.campaign_id).first()
            if camp:
                campaign_name = camp.name
                matched = True
        else:
            # try both
            camp = (
                FacebookAdsCampaign.objects.filter(app_id=app_id, campaign_id=row.campaign_id).first()
                or GoogleAdsCampaign.objects.filter(app_id=app_id, campaign_id=row.campaign_id).first()
            )
            if camp:
                campaign_name = camp.name
                matched = True
                if not row.platform or row.platform == PLATFORM_OTHER:
                    if isinstance(camp, FacebookAdsCampaign):
                        row.platform = PLATFORM_FACEBOOK
                    else:
                        row.platform = PLATFORM_GOOGLE

    if not matched and row.tag:
        ad_link = ad_link or AdLink.objects.filter(app_id=app_id, tag=row.tag, is_active=True).order_by('-id').first()
        if ad_link and ad_link.campaign_id:
            row.campaign_id = row.campaign_id or ad_link.campaign_id
            matched = True
            campaign_name = ad_link.name or ''

    if ad_link:
        row.ad_link_id = ad_link.id
        if not row.campaign_id and ad_link.campaign_id:
            row.campaign_id = ad_link.campaign_id
        matched = True
        if not campaign_name:
            campaign_name = ad_link.name or ''

    if matched:
        row.status = STATUS_MATCHED
        row.campaign_name = (campaign_name or row.campaign_name or '')[:256]
        row.matched_at = timezone.now()
        row.save(update_fields=[
            'status', 'campaign_id', 'campaign_name', 'ad_link_id', 'platform',
            'matched_at', 'updated_at',
        ])
        return True
    return False


def resolve_attribution(row, *, admin_user=None, status=STATUS_RESOLVED, note='',
                        campaign_id=None, platform=None, user_id=None) -> Any:
    if campaign_id is not None:
        row.campaign_id = str(campaign_id)[:64] or None
    if platform:
        row.platform = platform
    if user_id is not None:
        from models.models import User
        row.user = User.objects.filter(id=user_id).first()
    if campaign_id or row.campaign_id:
        try_auto_match(row)
        row.refresh_from_db()
    row.status = status if status in (
        STATUS_PENDING, STATUS_MATCHED, STATUS_RESOLVED, STATUS_DISCARDED,
    ) else STATUS_RESOLVED
    row.resolve_note = (note or '')[:512]
    row.resolved_at = timezone.now()
    if admin_user and getattr(admin_user, 'id', None):
        row.resolved_by_id = admin_user.id
    row.save()
    return row


def serialize_attribution(row) -> dict:
    return {
        'id': row.id,
        'app_id': row.app_id,
        'user_id': row.user_id,
        'platform': row.platform,
        'status': row.status,
        'campaign_id': row.campaign_id or '',
        'campaign_name': row.campaign_name or '',
        'adset_id': row.adset_id or '',
        'ad_id': row.ad_id or '',
        'click_id': row.click_id or '',
        'utm_source': row.utm_source or '',
        'utm_medium': row.utm_medium or '',
        'utm_campaign': row.utm_campaign or '',
        'utm_content': row.utm_content or '',
        'utm_term': row.utm_term or '',
        'deep_link': row.deep_link or '',
        'tag': row.tag or '',
        'ad_link_id': row.ad_link_id,
        'device_id': row.device_id or '',
        'resolve_note': row.resolve_note or '',
        'matched_at': row.matched_at.isoformat() if row.matched_at else None,
        'resolved_at': row.resolved_at.isoformat() if row.resolved_at else None,
        'resolved_by_id': row.resolved_by_id,
        'created_at': row.created_at.isoformat() if row.created_at else None,
        'props': row.props or {},
    }


def batch_auto_match(app_id: str, limit: int = 200) -> dict:
    from models.models import AdAttribution
    rows = list(
        AdAttribution.objects.filter(app_id=app_id, status=STATUS_PENDING).order_by('-id')[:limit]
    )
    matched = 0
    for row in rows:
        if try_auto_match(row):
            matched += 1
    return {'ok': True, 'scanned': len(rows), 'matched': matched}
