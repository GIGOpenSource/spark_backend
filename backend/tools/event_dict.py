"""
Authoritative English ↔ Chinese analytics event dictionary.

Client utils/eventDict.js mirrors this; server is source of truth for admin display
and for filling props.event_zh on ingest when the client omits it.
"""

from __future__ import annotations

# Canonical / client event names → Chinese labels
EVENT_LABELS_ZH: dict[str, str] = {
    # Lifecycle / funnel
    'app_launch': 'App 启动',
    'app_first_open': '首次打开',
    'welcome_view': '欢迎页曝光',
    'auth_welcome_view': '欢迎页曝光',
    'auth_result': '登录/注册成功',
    'auth_login_ok': '账号登录成功',
    'auth_register_ok': '注册成功',
    'auth_google_ok': 'Google 登录成功',
    'auth_apple_ok': 'Apple 登录成功',
    'auth_facebook_ok': 'Facebook 登录成功',
    'auth_wechat_ok': '微信登录成功',
    'auth_phone_ok': '手机号登录成功',
    'auth_sms_ok': '短信验证成功',
    'onboarding_done': '完成引导',
    'onboarding_complete': '完成引导',
    'paywall_open': '付费墙打开',
    'paywall_show': '付费墙曝光',
    'purchase': '支付成功',
    'purchase_cn': '国内支付成功',
    'pay_success': '支付成功',
    # Core product
    'swipe': '滑动',
    'match': '匹配成功',
    'say_hi': '打招呼',
    'sos': '紧急求助',
    'attribution': '广告归因',
    # Commercial / fatigue
    'feed_exhausted': '推荐用尽',
    'like_limit_hit': '喜欢次数用尽',
    'boost_impression': 'Boost 曝光',
    'boost_start': 'Boost 开始',
    'boost_end': 'Boost 结束',
    'super_like': '超级喜欢',
    'rewind': '撤销划卡',
    'unlock_like': '解锁喜欢',
    # PV / UV
    'page_view': '页面浏览',
    'btn_click': '按钮点击',
}

# page_view props.page route → Chinese page name
PAGE_LABELS_ZH: dict[str, str] = {
    'pages/auth/welcome': '欢迎页',
    'pages/auth/login': '登录',
    'pages/auth/phone': '手机号登录',
    'pages/auth/forgot': '忘记密码',
    'pages/auth/register': '注册',
    'pages/auth/onboarding': '完善资料',
    'pages/discover/index': '发现',
    'pages/likes/index': '喜欢',
    'pages/chat/index': '消息列表',
    'pages/me/index': '我的',
    'pagesA/profile/detail': '资料详情',
    'pagesA/chat/room': '聊天室',
    'pagesA/chat/call': '通话',
    'pagesA/me/edit': '编辑资料',
    'pagesA/me/preview': '资料预览',
    'pagesA/me/settings': '设置',
    'pagesA/me/notifications': '通知设置',
    'pagesA/me/verify': '身份核验',
    'pagesA/me/legal': '法律条款',
    'pagesA/me/safety': '安全中心',
    'pagesA/features/swipe-night': 'Swipe Night',
    'pagesA/features/matchmaker': '红娘',
    'pagesA/features/campus': '校园',
    'pagesA/features/select': 'Select',
    'pagesA/features/face-to-face': '面对面',
    'pagesA/likes/sent': '已送出',
}

# btn_click props.btn → Chinese button name
BTN_LABELS_ZH: dict[str, str] = {
    'tab_discover': 'Tab-发现',
    'tab_likes': 'Tab-喜欢',
    'tab_chat': 'Tab-消息',
    'tab_me': 'Tab-我的',
    'auth_continue': '继续',
    'auth_google': 'Google 登录',
    'auth_apple': 'Apple 登录',
    'auth_facebook': 'Facebook 登录',
    'auth_wechat': '微信登录',
    'auth_phone': '手机号登录',
    'auth_sms_send': '发送验证码',
    'auth_login_submit': '提交登录',
    'auth_register_submit': '提交注册',
    'swipe_like': '喜欢',
    'swipe_pass': '跳过',
    'swipe_super': '超级喜欢',
    'swipe_boost': 'Boost',
    'swipe_rewind': '撤销',
    'filter_open': '打开筛选',
    'filter_apply': '应用筛选',
    'passport_open': '打开护照',
    'passport_apply': '应用护照',
    'say_hi': '打招呼',
    'like_back': '回赞',
    'open_vip': '打开会员',
    'open_room': '打开会话',
    'send_message': '发送消息',
    'start_call': '发起通话',
    'edit_profile': '编辑资料',
    'open_settings': '打开设置',
    'open_notifications': '通知设置',
    'open_verify': '身份核验',
    'open_legal': '法律条款',
    'open_safety': '安全中心',
    'open_preview': '预览资料',
    'vip_tier': '选择会员档位',
    'vip_period': '选择订阅周期',
    'vip_buy': '购买会员',
    'match_send': '匹配后发消息',
    'match_keep_swiping': '继续滑动',
    'compliment_send': '发送赞美',
    'settings_language': '语言',
    'settings_theme': '外观',
    'settings_logout': '退出登录',
    'settings_delete': '注销账号',
    'settings_privacy': '隐私',
    'settings_accounts': '关联账号',
    'feature_swipe_night': 'Swipe Night',
    'feature_matchmaker': '红娘',
    'feature_campus': '校园',
    'feature_select': 'Select',
    'feature_face_to_face': '面对面',
}


def label_zh_for_event(event: str, props: dict | None = None) -> str:
    """Resolve Chinese label for an event, optionally using page/btn props."""
    props = props or {}
    name = str(event or '')
    if name == 'page_view':
        page = str(props.get('page') or props.get('page_path') or '')
        page_zh = PAGE_LABELS_ZH.get(page) or PAGE_LABELS_ZH.get(page.lstrip('/'))
        if page_zh:
            return f'页面浏览 · {page_zh}'
        return EVENT_LABELS_ZH.get('page_view', '页面浏览')
    if name == 'btn_click':
        btn = str(props.get('btn') or props.get('button') or '')
        btn_zh = BTN_LABELS_ZH.get(btn)
        if btn_zh:
            return f'按钮点击 · {btn_zh}'
        return EVENT_LABELS_ZH.get('btn_click', '按钮点击')
    return EVENT_LABELS_ZH.get(name) or name


def enrich_list_with_labels(rows: list[dict]) -> list[dict]:
    """Attach label_zh to breakdown rows."""
    out = []
    for r in rows or []:
        item = dict(r)
        item['label_zh'] = label_zh_for_event(item.get('event') or '')
        out.append(item)
    return out


def full_dictionary() -> list[dict]:
    """Static catalog for admin reference (events + pages + buttons)."""
    rows = []
    for en, zh in sorted(EVENT_LABELS_ZH.items()):
        rows.append({'event': en, 'label_zh': zh, 'kind': 'event'})
    for en, zh in sorted(PAGE_LABELS_ZH.items()):
        rows.append({'event': f'page:{en}', 'label_zh': zh, 'kind': 'page'})
    for en, zh in sorted(BTN_LABELS_ZH.items()):
        rows.append({'event': f'btn:{en}', 'label_zh': zh, 'kind': 'btn'})
    return rows
