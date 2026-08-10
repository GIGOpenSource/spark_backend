"""APP feature modules: catalog, path mapping, enablement checks."""

from models.models import AppConfig

# Dating core — default-on for apps without explicit enabled_modules.
CORE_MODULES = [
    {'key': 'recommend', 'label': 'Discover 推荐', 'path_prefix': '/api/recommend/', 'optional': False},
    {'key': 'likes', 'label': 'Likes 喜欢', 'path_prefix': '/api/likes/', 'optional': False},
    {'key': 'profile', 'label': 'Profile 资料', 'path_prefix': '/api/profile/', 'optional': False},
    {'key': 'match', 'label': 'Match 匹配', 'path_prefix': '/api/match/', 'optional': False},
    {'key': 'chat', 'label': 'Chat 聊天', 'path_prefix': '/api/chat/', 'optional': False},
    {'key': 'vip', 'label': 'VIP 会员', 'path_prefix': '/api/vip/', 'optional': False},
    {'key': 'translate', 'label': 'Translate 翻译', 'path_prefix': '/api/translate/', 'optional': False},
    {'key': 'events', 'label': 'Events 埋点', 'path_prefix': '/api/events/', 'optional': False},
    {'key': 'push', 'label': 'Push 系统通知', 'path_prefix': '/api/push/', 'optional': False},
    {'key': 'verify', 'label': 'Verify 身份核验', 'path_prefix': '/api/verify/', 'optional': False},
]

# Social parallel domains — opt-in via AppConfig.enabled_modules.
OPTIONAL_MODULES = [
    {'key': 'quick_match', 'label': '一键速配', 'path_prefix': '/api/quick-match/', 'optional': True},
    {'key': 'group', 'label': '群聊', 'path_prefix': '/api/group/', 'optional': True},
    {'key': 'community', 'label': '社区', 'path_prefix': '/api/community/', 'optional': True},
    {'key': 'moments', 'label': 'Moment 朋友圈', 'path_prefix': '/api/moments/', 'optional': True},
    {'key': 'short_video', 'label': '短视频', 'path_prefix': '/api/videos/', 'optional': True},
    {'key': 'swipe_night', 'label': 'Swipe Night', 'path_prefix': '/api/swipe-night/', 'optional': True},
    {'key': 'matchmaker', 'label': 'Matchmaker', 'path_prefix': '/api/matchmaker/', 'optional': True},
    {'key': 'campus', 'label': 'Tinder U / Campus', 'path_prefix': '/api/campus/', 'optional': True},
    {'key': 'select', 'label': 'Select', 'path_prefix': '/api/select/', 'optional': True},
    {'key': 'face_to_face', 'label': 'Face to Face', 'path_prefix': '/api/face-to-face/', 'optional': True},
    {'key': 'safety', 'label': 'Safety 安全中心', 'path_prefix': '/api/safety/', 'optional': False},
]

APP_MODULES = CORE_MODULES + OPTIONAL_MODULES
ALL_MODULE_KEYS = [m['key'] for m in APP_MODULES]
CORE_MODULE_KEYS = [m['key'] for m in CORE_MODULES]
OPTIONAL_MODULE_KEYS = [m['key'] for m in OPTIONAL_MODULES]

# Fine-grained product switches (product_profile), for admin form metadata.
PRODUCT_FLAG_DEFS = [
    {'key': 'messaging_mode', 'label': '消息模式', 'type': 'select', 'options': ['any', 'women_first', 'qa_gate']},
    {'key': 'match_open_hours', 'label': '匹配开放小时', 'type': 'number'},
    {'key': 'feed_same_app_only', 'label': '仅同 App Feed', 'type': 'bool'},
    {'key': 'extend_enabled', 'label': '延长匹配', 'type': 'bool'},
    {'key': 'compliment_enabled', 'label': '赞美/超级喜欢', 'type': 'bool'},
    {'key': 'qa_gate_enabled', 'label': '问答门禁', 'type': 'bool'},
    {'key': 'daily_feed_cap', 'label': '每日推荐上限', 'type': 'number'},
    {'key': 'daily_feed_vip_bonus', 'label': 'VIP 推荐加量', 'type': 'tiers'},
    {'key': 'display_tiers', 'label': 'VIP 展示名', 'type': 'tiers'},
]

DEFAULT_PACKAGE_BY_APP = {
    'spark_main': 'app.spark',
    'swipe_main': 'app.bee',
    'ember_main': 'app.ember',
    'matchup_main': 'app.matchup',
    'flick_main': 'app.flick',
}


def default_enabled_modules():
    """Legacy-safe default: dating core + safety + Tinder greenfield MVPs. Social still opt-in."""
    return list(CORE_MODULE_KEYS) + [
        'safety', 'swipe_night', 'matchmaker', 'campus', 'select', 'face_to_face',
    ]


def path_to_module(path):
    """Map request path to module key; None means ungated (bootstrap/auth/admin/...)."""
    if not path:
        return None
    # Normalize without query string
    path = path.split('?', 1)[0]
    for m in APP_MODULES:
        prefix = m['path_prefix']
        if path == prefix.rstrip('/') or path.startswith(prefix):
            return m['key']
    return None


def get_enabled_modules(app_id):
    """
    Return enabled module keys for an app.
    - Missing AppConfig or missing enabled_modules key → all modules (legacy safe default).
    - Explicit list (including empty) → that list.
    """
    app = AppConfig.objects.filter(app_id=app_id).first()
    if not app or not isinstance(app.config, dict):
        return default_enabled_modules()
    if 'enabled_modules' not in app.config:
        return default_enabled_modules()
    raw = app.config.get('enabled_modules')
    if not isinstance(raw, list):
        return default_enabled_modules()
    return [k for k in raw if k in ALL_MODULE_KEYS]


def is_module_enabled(app_id, module_key):
    if not module_key:
        return True
    return module_key in get_enabled_modules(app_id)


def set_enabled_modules(app_id, modules, *, name=None, package_name=None, create=True):
    """Upsert enabled_modules on AppConfig.config."""
    defaults = {'name': name or app_id, 'config': {}}
    if package_name is not None:
        defaults['package_name'] = package_name
    if create:
        app, _ = AppConfig.objects.get_or_create(app_id=app_id, defaults=defaults)
    else:
        app = AppConfig.objects.filter(app_id=app_id).first()
        if not app:
            return None
    if name is not None:
        app.name = name
    if package_name is not None:
        app.package_name = package_name
    cfg = dict(app.config or {})
    cleaned = []
    seen = set()
    for k in modules or []:
        if k in ALL_MODULE_KEYS and k not in seen:
            cleaned.append(k)
            seen.add(k)
    cfg['enabled_modules'] = cleaned
    app.config = cfg
    update_fields = ['config']
    if name is not None:
        update_fields.append('name')
    if package_name is not None:
        update_fields.append('package_name')
    app.save(update_fields=update_fields)
    return get_enabled_modules(app_id)


def resolve_request_app_id_for_module(request, default='spark_main'):
    """Prefer authenticated user.app_id, then body/query app_id."""
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        uid_app = getattr(user, 'app_id', None)
        if uid_app:
            return uid_app
    app_id = None
    try:
        app_id = request.data.get('app_id')
    except Exception:
        app_id = None
    if not app_id:
        app_id = request.query_params.get('app_id')
    return app_id or default


def serialize_app_config_row(app):
    """Admin list row."""
    cfg = app.config if isinstance(app.config, dict) else {}
    modules = cfg.get('enabled_modules')
    if not isinstance(modules, list):
        modules = default_enabled_modules()
    from tools.spark_helpers import get_product_profile
    from tools.maps_helpers import normalize_maps_config
    return {
        'id': app.id,
        'app_id': app.app_id,
        'name': app.name,
        'package_name': app.package_name or DEFAULT_PACKAGE_BY_APP.get(app.app_id, ''),
        'tos_url': app.tos_url or '',
        'privacy_url': app.privacy_url or '',
        'enabled_modules': [k for k in modules if k in ALL_MODULE_KEYS],
        'product_profile': get_product_profile(app.app_id),
        'maps': normalize_maps_config(cfg.get('maps')),
        'created_at': app.created_at.isoformat() if app.created_at else None,
    }


def modules_catalog_payload():
    return {
        'modules': list(APP_MODULES),
        'product_flags': list(PRODUCT_FLAG_DEFS),
    }
