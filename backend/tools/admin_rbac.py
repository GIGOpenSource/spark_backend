"""Admin RBAC: roles, menu permissions, effective permission resolution."""

KNOWN_APPS = [
    {'app_id': 'spark_main', 'name': 'Spark'},
    {'app_id': 'swipe_main', 'name': 'bee'},
    {'app_id': 'ember_main', 'name': 'Ember'},
    {'app_id': 'matchup_main', 'name': 'MatchUp'},
    {'app_id': 'flick_main', 'name': 'Flick'},
]

ALL_PERMISSIONS = [
    {'key': 'dashboard', 'label': '汇总统计'},
    {'key': 'users', 'label': '用户运营'},
    {'key': 'chats', 'label': '聊天记录'},
    {'key': 'quick_match', 'label': '一键速配'},
    {'key': 'groups', 'label': '群聊管理'},
    {'key': 'community', 'label': '社区内容'},
    {'key': 'funnel', 'label': '推荐漏斗'},
    {'key': 'orders', 'label': '订单 / SKU'},
    {'key': 'firebase', 'label': 'Firebase'},
    {'key': 'ads', 'label': '广告链接'},
    {'key': 'safety', 'label': '内容安全'},
    {'key': 'user_safety', 'label': '用户安全'},
    {'key': 'verify', 'label': '实人核验'},
    {'key': 'match_qa', 'label': 'Match QA'},
    {'key': 'swipe_night', 'label': 'Swipe Night'},
    {'key': 'matchmaker', 'label': 'Matchmaker'},
    {'key': 'campus', 'label': 'Campus'},
    {'key': 'select', 'label': 'Select'},
    {'key': 'face_to_face', 'label': 'Face to Face'},
    {'key': 'ops_banner', 'label': '运营 Banner'},
    {'key': 'matches', 'label': '匹配巡查'},
    {'key': 'ledger', 'label': '额度账本'},
    {'key': 'events', 'label': 'Analytics 埋点'},
    {'key': 'config', 'label': 'App 基础配置'},
    {'key': 'push_configs', 'label': '系统通知'},
    {'key': 'providers', 'label': '三方配置'},
    {'key': 'country', 'label': '国家与法律'},
    {'key': 'review', 'label': '发版审核'},
    {'key': 'admin_members', 'label': '管理员'},
    {'key': 'admin_roles', 'label': '权限管理'},
]

ALL_PERM_KEYS = [p['key'] for p in ALL_PERMISSIONS]

ROLE_DEFS = [
    {
        'key': 'super_admin',
        'label': '超管',
        'description': '组织超管，拥有全部菜单与成员管理',
        'permissions': ['*'],
    },
    {
        'key': 'operator',
        'label': '运营',
        'description': '用户、聊天、漏斗、订单、广告、配置与侧栏功能',
        'permissions': [
            'dashboard', 'users', 'chats', 'quick_match', 'groups', 'community',
            'funnel', 'orders', 'firebase',
            'ads', 'events', 'config', 'push_configs', 'providers', 'country',
            'user_safety', 'verify', 'match_qa', 'swipe_night', 'matchmaker',
            'campus', 'select', 'face_to_face', 'ops_banner', 'matches', 'ledger',
        ],
    },
    {
        'key': 'support',
        'label': '客服',
        'description': '用户查询、聊天记录与内容/用户安全',
        'permissions': [
            'dashboard', 'users', 'chats', 'quick_match', 'groups', 'community',
            'safety', 'user_safety', 'verify', 'match_qa', 'matches', 'ledger',
        ],
    },
    {
        'key': 'finance',
        'label': '财务',
        'description': '订单与支付数据',
        'permissions': ['dashboard', 'orders', 'firebase', 'ledger'],
    },
    {
        'key': 'analyst',
        'label': '分析',
        'description': '看板与埋点只读',
        'permissions': ['dashboard', 'events', 'firebase'],
    },
    {
        'key': 'reviewer',
        'label': '审核员',
        'description': '内容安全、发版审核与校园/Select/核验',
        'permissions': [
            'safety', 'review', 'community', 'user_safety', 'verify',
            'campus', 'select', 'match_qa',
        ],
    },
]

ADMIN_ROLE_KEYS = [r['key'] for r in ROLE_DEFS]


def get_role_def(role_key):
    for r in ROLE_DEFS:
        if r['key'] == role_key:
            return r
    return None


def load_role_overrides(app_id='spark_main'):
    from models.models import AdminRolePermission
    rows = AdminRolePermission.objects.filter(app_id=app_id)
    return {r.role: list(r.permissions or []) for r in rows}


def get_role_permissions(role_key, overrides=None, app_id='spark_main'):
    if overrides is None:
        overrides = load_role_overrides(app_id)
    if overrides and role_key in overrides:
        return list(overrides[role_key] or [])
    role = get_role_def(role_key)
    if not role:
        return []
    return list(role.get('permissions') or [])


def effective_permissions(user, app_id='spark_main', overrides=None):
    """Resolve menu permissions for an admin user."""
    role = getattr(user, 'role', None) or ''
    if role == 'super_admin':
        return ['*']
    if overrides is None:
        overrides = load_role_overrides(app_id if not is_all_app(app_id) else 'spark_main')
    perms = list(get_role_permissions(role, overrides=overrides, app_id=app_id))
    extra = getattr(user, 'admin_permissions', None) or []
    if isinstance(extra, list):
        for p in extra:
            if p and p not in perms:
                perms.append(p)
    if '*' in perms:
        return ['*']
    return perms


def is_all_app(app_id):
    return app_id in ('*', 'ALL', 'all', '', None)


def accessible_app_ids(user):
    ids = getattr(user, 'admin_app_ids', None) or []
    if getattr(user, 'role', None) == 'super_admin' or not ids or '*' in ids:
        return [a['app_id'] for a in KNOWN_APPS]
    return [i for i in ids if i and i != '*']


def can_access_app(user, app_id):
    if not user:
        return False
    if is_all_app(app_id):
        return True
    if getattr(user, 'role', None) == 'super_admin':
        return True
    return app_id in accessible_app_ids(user)


def concrete_app_id(user, app_id, fallback='spark_main'):
    if not is_all_app(app_id):
        return app_id
    ids = accessible_app_ids(user)
    return ids[0] if ids else fallback


def resolve_request_app_id(request, default='spark_main'):
    raw = None
    if hasattr(request, 'query_params'):
        raw = request.query_params.get('app_id')
    if raw is None and hasattr(request, 'data'):
        try:
            raw = request.data.get('app_id')
        except Exception:
            raw = None
    if raw is None or raw == '':
        return default
    return raw


def app_scope_filter(user, app_id, field='app_id'):
    if is_all_app(app_id):
        return {f'{field}__in': accessible_app_ids(user)}
    return {field: app_id}
