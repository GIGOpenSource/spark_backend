"""Resolve third-party credentials: admin ProviderConfig first, then env."""

from __future__ import annotations

from tools.provider_catalog import GLOBAL_APP_ID, get_provider_def, config_status
from tools.tools import getEnvConfig


def resolve_storage_app_id(provider_key: str, app_id: str | None = None) -> str:
    pdef = get_provider_def(provider_key)
    if pdef and pdef.get('scope') == 'global':
        return GLOBAL_APP_ID
    return (app_id or 'spark_main').strip() or 'spark_main'


def get_raw_provider_config(provider_key: str, app_id: str | None = None) -> dict:
    from models.models import ProviderConfig

    storage_app = resolve_storage_app_id(provider_key, app_id)
    row = ProviderConfig.objects.filter(provider_key=provider_key, app_id=storage_app).first()
    return dict(row.config or {}) if row else {}


def get_provider_field(
    provider_key: str,
    field_key: str,
    app_id: str | None = None,
    env_keys: list | tuple | None = None,
) -> str:
    """Prefer DB config value; fall back to env keys (first non-empty)."""
    cfg = get_raw_provider_config(provider_key, app_id)
    val = cfg.get(field_key)
    if val is not None and str(val).strip():
        return str(val).strip()
    for ek in env_keys or ():
        ev = (getEnvConfig(ek) or '').strip()
        if ev:
            return ev
    return ''


def provider_enabled(provider_key: str, app_id: str | None = None, default: bool = True) -> bool:
    cfg = get_raw_provider_config(provider_key, app_id)
    if 'enabled' not in cfg:
        return default
    return bool(cfg.get('enabled'))


def amap_rest_key(app_id: str | None = None) -> str:
    return get_provider_field('amap', 'rest_key', app_id, env_keys=('AMAP_REST_KEY',))


def google_maps_server_key(app_id: str | None = None) -> str:
    return get_provider_field('google_maps', 'server_key', app_id, env_keys=('GOOGLE_MAPS_SERVER_KEY',))


def google_translate_api_key() -> str:
    """Return API key only when provider is enabled (or never configured → allow env)."""
    cfg = get_raw_provider_config('google_translate')
    if cfg and cfg.get('enabled') is False:
        return ''
    return get_provider_field(
        'google_translate', 'api_key', None, env_keys=('GOOGLE_TRANSLATE_API_KEY',),
    )


def unipush_settings(app_id: str | None = None) -> dict:
    cfg = get_raw_provider_config('unipush', app_id)
    return {
        'enabled': cfg.get('enabled', False),
        'uni_appid': (cfg.get('uni_appid') or getEnvConfig('UNI_PUSH_APP_ID') or '').strip(),
        'cloud_push_url': (cfg.get('cloud_push_url') or getEnvConfig('UNI_PUSH_CLOUD_URL') or '').strip(),
        'request_secret': (
            cfg.get('request_secret')
            or getEnvConfig('UNI_PUSH_REQUEST_SECRET')
            or getEnvConfig('UNI_PUSH_MASTER_SECRET')
            or ''
        ).strip(),
        # legacy v1 fields (env only)
        'app_key': (getEnvConfig('UNI_PUSH_KEY') or getEnvConfig('UNI_PUSH_APP_KEY') or '').strip(),
        'master_secret': (getEnvConfig('UNI_PUSH_MASTER_SECRET') or '').strip(),
    }


def sync_maps_client_keys_to_app(app_id: str, provider_key: str, config: dict) -> None:
    """Keep AppConfig.config.maps SDK keys in sync for mobile bootstrap."""
    if provider_key not in ('amap', 'google_maps'):
        return
    from models.models import AppConfig
    from tools.maps_helpers import normalize_maps_config

    obj = AppConfig.objects.filter(app_id=app_id).first()
    if not obj:
        return
    cfg = dict(obj.config or {})
    maps = normalize_maps_config(cfg.get('maps'))
    if provider_key == 'amap':
        maps['amap'] = {
            **maps.get('amap', {}),
            'enabled': bool(config.get('enabled', True)),
            'android_key': (config.get('android_key') or maps.get('amap', {}).get('android_key') or '').strip(),
            'ios_key': (config.get('ios_key') or maps.get('amap', {}).get('ios_key') or '').strip(),
        }
    else:
        maps['google'] = {
            **maps.get('google', {}),
            'enabled': bool(config.get('enabled', True)),
            'android_key': (config.get('android_key') or maps.get('google', {}).get('android_key') or '').strip(),
            'ios_key': (config.get('ios_key') or maps.get('google', {}).get('ios_key') or '').strip(),
        }
    cfg['maps'] = maps
    obj.config = cfg
    obj.save(update_fields=['config'])


def list_provider_statuses(app_id: str) -> list:
    """Catalog entries + status for admin list."""
    from tools.provider_catalog import catalog_list

    out = []
    for p in catalog_list():
        storage = resolve_storage_app_id(p['key'], app_id)
        cfg = get_raw_provider_config(p['key'], app_id if p.get('scope') != 'global' else None)
        status = config_status(p['key'], cfg)
        out.append({
            **p,
            'app_id': storage,
            'status': status,
            'has_config': bool(cfg),
            'enabled': cfg.get('enabled') if 'enabled' in cfg else None,
            'updated_at': None,
        })
    # attach updated_at
    from models.models import ProviderConfig
    keys = [x['key'] for x in out]
    rows = {
        (r.provider_key, r.app_id): r
        for r in ProviderConfig.objects.filter(provider_key__in=keys)
    }
    for item in out:
        row = rows.get((item['key'], item['app_id']))
        if row:
            item['updated_at'] = row.updated_at.isoformat() if row.updated_at else None
            item['notes'] = row.notes or ''
        else:
            item['notes'] = ''
    return out
