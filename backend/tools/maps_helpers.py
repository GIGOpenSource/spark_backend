"""Maps provider selection (CN mainland → Amap, else Google) + geocode helpers."""

import ipaddress
import logging
from typing import Any, Optional

import requests

from tools.tools import getEnvConfig

logger = logging.getLogger(__name__)

PROVIDER_AMAP = 'amap'
PROVIDER_GOOGLE = 'google'


def get_client_ip(request) -> str:
    forwarded = (request.META.get('HTTP_X_FORWARDED_FOR') or '').strip()
    if forwarded:
        return forwarded.split(',')[0].strip()
    real = (request.META.get('HTTP_X_REAL_IP') or '').strip()
    if real:
        return real
    return (request.META.get('REMOTE_ADDR') or '').strip()


def _country_from_cdn_headers(request) -> Optional[str]:
    for header in (
        'HTTP_CF_IPCOUNTRY',
        'HTTP_CLOUDFRONT_VIEWER_COUNTRY',
        'HTTP_X_COUNTRY_CODE',
        'HTTP_X_GEO_COUNTRY',
        'HTTP_X_APPENGINE_COUNTRY',
    ):
        code = (request.META.get(header) or '').strip().upper()
        if code and code not in ('XX', 'T1', 'ZZ'):
            return code
    return None


def _country_from_geoip_db(ip: str) -> Optional[str]:
    db_path = (getEnvConfig('GEOIP_DB_PATH') or '').strip()
    if not db_path or not ip:
        return None
    try:
        import geoip2.database  # optional dependency
        with geoip2.database.Reader(db_path) as reader:
            return (reader.country(ip).country.iso_code or '').upper() or None
    except Exception:
        logger.debug('geoip lookup failed for %s', ip, exc_info=True)
        return None


def is_private_or_local_ip(ip: str) -> bool:
    if not ip:
        return True
    try:
        obj = ipaddress.ip_address(ip)
        return bool(obj.is_private or obj.is_loopback or obj.is_link_local)
    except ValueError:
        return True


def is_china_mainland_request(request) -> bool:
    """
    China mainland only (CN). HK / MO / TW are not mainland → Google.
    Priority: CDN country header → optional MaxMind DB → fallback env.
    """
    code = _country_from_cdn_headers(request)
    if code:
        return code == 'CN'

    ip = get_client_ip(request)
    if not is_private_or_local_ip(ip):
        geo = _country_from_geoip_db(ip)
        if geo:
            return geo == 'CN'

    # Unknown (local/dev without headers): default overseas → Google unless forced
    forced = (getEnvConfig('MAPS_FORCE_PROVIDER') or '').strip().lower()
    if forced in (PROVIDER_AMAP, PROVIDER_GOOGLE):
        return forced == PROVIDER_AMAP
    fallback = (getEnvConfig('MAPS_FALLBACK_PROVIDER') or PROVIDER_GOOGLE).strip().lower()
    return fallback == PROVIDER_AMAP


def normalize_maps_config(raw: Any) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    amap = raw.get('amap') if isinstance(raw.get('amap'), dict) else {}
    google = raw.get('google') if isinstance(raw.get('google'), dict) else {}
    return {
        'auto_rule': raw.get('auto_rule') or 'ip_cn_amap_else_google',
        'amap': {
            'enabled': amap.get('enabled', True) is not False,
            'android_key': (amap.get('android_key') or '').strip(),
            'ios_key': (amap.get('ios_key') or '').strip(),
        },
        'google': {
            'enabled': google.get('enabled', True) is not False,
            'android_key': (google.get('android_key') or '').strip(),
            'ios_key': (google.get('ios_key') or '').strip(),
        },
    }


def resolve_map_provider(request, maps_config: Optional[dict] = None) -> str:
    cfg = normalize_maps_config(maps_config or {})
    want_amap = is_china_mainland_request(request)
    if want_amap and cfg['amap']['enabled']:
        return PROVIDER_AMAP
    if (not want_amap) and cfg['google']['enabled']:
        return PROVIDER_GOOGLE
    # Prefer the other if preferred is disabled
    if cfg['amap']['enabled']:
        return PROVIDER_AMAP
    if cfg['google']['enabled']:
        return PROVIDER_GOOGLE
    return PROVIDER_GOOGLE if not want_amap else PROVIDER_AMAP


def build_bootstrap_maps(request, effective_config: Optional[dict] = None) -> dict:
    cfg_src = {}
    if isinstance(effective_config, dict) and isinstance(effective_config.get('maps'), dict):
        cfg_src = effective_config.get('maps')
    maps_cfg = normalize_maps_config(cfg_src)
    provider = resolve_map_provider(request, maps_cfg)
    return {
        'provider': provider,
        'coord_type': 'gcj02' if provider == PROVIDER_AMAP else 'wgs84',
        'auto_rule': maps_cfg['auto_rule'],
        'amap': {
            'enabled': maps_cfg['amap']['enabled'],
            # Public app keys are already bound to package; expose for ops/debug only when set
            'android_key': maps_cfg['amap']['android_key'],
            'ios_key': maps_cfg['amap']['ios_key'],
        },
        'google': {
            'enabled': maps_cfg['google']['enabled'],
            'android_key': maps_cfg['google']['android_key'],
            'ios_key': maps_cfg['google']['ios_key'],
        },
    }


def _mock_geocode(q: str) -> dict:
    return {
        'provider': 'mock',
        'mock': True,
        'results': [
            {
                'name': q or 'Shanghai',
                'city': q or 'Shanghai',
                'address': q or 'Shanghai, China',
                'lat': 31.2304,
                'lng': 121.4737,
            }
        ],
    }


def _mock_regeo(lat: float, lng: float) -> dict:
    return {
        'provider': 'mock',
        'mock': True,
        'city': 'Shanghai',
        'address': 'Shanghai',
        'lat': lat,
        'lng': lng,
    }


def _key_missing(provider: str, q: str = '', lat=None, lng=None) -> dict:
    from django.conf import settings
    if getattr(settings, 'MAPS_ALLOW_MOCK', False):
        if lat is not None and lng is not None:
            return _mock_regeo(lat, lng)
        return _mock_geocode(q)
    out = {'provider': provider, 'mock': False, 'error': f'{provider}_key_missing', 'results': []}
    if lat is not None:
        out.update({'city': '', 'address': '', 'lat': lat, 'lng': lng})
    return out


def geocode_places(q: str, provider: str, app_id: str | None = None) -> dict:
    q = (q or '').strip()
    if not q:
        return {'provider': provider, 'results': []}

    if provider == PROVIDER_AMAP:
        from tools.provider_helpers import amap_rest_key
        key = amap_rest_key(app_id)
        if not key:
            return _key_missing(PROVIDER_AMAP, q=q)
        try:
            resp = requests.get(
                'https://restapi.amap.com/v3/geocode/geo',
                params={'address': q, 'key': key},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get('geocodes') or []:
                loc = (item.get('location') or '').split(',')
                if len(loc) != 2:
                    continue
                lng, lat = float(loc[0]), float(loc[1])
                city = item.get('city') or item.get('province') or item.get('formatted_address') or q
                if isinstance(city, list):
                    city = city[0] if city else q
                results.append({
                    'name': item.get('formatted_address') or city,
                    'city': city,
                    'address': item.get('formatted_address') or city,
                    'lat': lat,
                    'lng': lng,
                })
            return {'provider': PROVIDER_AMAP, 'mock': False, 'results': results}
        except Exception:
            logger.exception('amap geocode failed')
            return {'provider': PROVIDER_AMAP, 'mock': False, 'error': 'amap_geocode_failed', 'results': []}

    from tools.provider_helpers import google_maps_server_key
    key = google_maps_server_key(app_id)
    if not key:
        return _key_missing(PROVIDER_GOOGLE, q=q)
    try:
        resp = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={'address': q, 'key': key},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get('results') or []:
            loc = (item.get('geometry') or {}).get('location') or {}
            lat, lng = loc.get('lat'), loc.get('lng')
            if lat is None or lng is None:
                continue
            city = ''
            for comp in item.get('address_components') or []:
                types = comp.get('types') or []
                if 'locality' in types or 'administrative_area_level_1' in types:
                    city = comp.get('long_name') or ''
                    if 'locality' in types:
                        break
            city = city or item.get('formatted_address') or q
            results.append({
                'name': item.get('formatted_address') or city,
                'city': city,
                'address': item.get('formatted_address') or city,
                'lat': float(lat),
                'lng': float(lng),
            })
        return {'provider': PROVIDER_GOOGLE, 'mock': False, 'results': results}
    except Exception:
        logger.exception('google geocode failed')
        return {'provider': PROVIDER_GOOGLE, 'mock': False, 'error': 'google_geocode_failed', 'results': []}


def reverse_geocode(lat: float, lng: float, provider: str, app_id: str | None = None) -> dict:
    if provider == PROVIDER_AMAP:
        from tools.provider_helpers import amap_rest_key
        key = amap_rest_key(app_id)
        if not key:
            return _key_missing(PROVIDER_AMAP, lat=lat, lng=lng)
        try:
            resp = requests.get(
                'https://restapi.amap.com/v3/geocode/regeo',
                params={'location': f'{lng},{lat}', 'key': key},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            regeo = data.get('regeocode') or {}
            addr = regeo.get('addressComponent') or {}
            city = addr.get('city') or addr.get('province') or ''
            if isinstance(city, list):
                city = city[0] if city else ''
            if not city:
                city = regeo.get('formatted_address') or ''
            return {
                'provider': PROVIDER_AMAP,
                'mock': False,
                'city': city,
                'address': regeo.get('formatted_address') or city,
                'lat': lat,
                'lng': lng,
            }
        except Exception:
            logger.exception('amap regeo failed')
            return {'provider': PROVIDER_AMAP, 'mock': False, 'error': 'amap_regeo_failed',
                    'city': '', 'address': '', 'lat': lat, 'lng': lng}

    from tools.provider_helpers import google_maps_server_key
    key = google_maps_server_key(app_id)
    if not key:
        return _key_missing(PROVIDER_GOOGLE, lat=lat, lng=lng)
    try:
        resp = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={'latlng': f'{lat},{lng}', 'key': key},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get('results') or []
        if not results:
            return {'provider': PROVIDER_GOOGLE, 'mock': False, 'city': '', 'address': '', 'lat': lat, 'lng': lng}
        top = results[0]
        city = ''
        for comp in top.get('address_components') or []:
            types = comp.get('types') or []
            if 'locality' in types:
                city = comp.get('long_name') or ''
                break
            if not city and 'administrative_area_level_1' in types:
                city = comp.get('long_name') or ''
        address = top.get('formatted_address') or city
        return {
            'provider': PROVIDER_GOOGLE,
            'mock': False,
            'city': city or address,
            'address': address,
            'lat': lat,
            'lng': lng,
        }
    except Exception:
        logger.exception('google regeo failed')
        return {'provider': PROVIDER_GOOGLE, 'mock': False, 'error': 'google_regeo_failed',
                'city': '', 'address': '', 'lat': lat, 'lng': lng}
