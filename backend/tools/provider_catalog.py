"""
Third-party provider catalog — field schemas aligned with official docs.

Docs referenced (do not invent fields):
- Apple App Store Server API (JWT): key_id, issuer_id, bundle_id, private_key (.p8),
  environment, app_apple_id
  https://developer.apple.com/documentation/appstoreserverapi
- Google Play Developer API: package_name + service account JSON
  https://developers.google.com/android-publisher
- Google Sign-In / ID token verify: web_client_id (+ optional android/ios client ids)
  https://developers.google.com/identity/sign-in/web/backend-auth
- 高德 Web 服务 Key + Android/iOS SDK Key
  https://lbs.amap.com/api/webservice/create-project-and-key
- Google Maps Platform: server key + Android/iOS SDK keys
  https://developers.google.com/maps/documentation/geocoding
- UniPush 2.0: DCloud appId + URL-ized uni-cloud-push endpoint (no MasterSecret)
  https://uniapp.dcloud.net.cn/unipush-v2.html
- Google Cloud Translation API: API key
  https://cloud.google.com/translate/docs/reference/rest
- Persona Identity: API key + inquiry template id
  https://docs.withpersona.com/api-keys
"""

from copy import deepcopy

GLOBAL_APP_ID = '_global_'

# Field types: text | password | textarea | switch | select
# secret=True → masked on GET unless reveal=1

PROVIDER_CATALOG = [
    {
        'key': 'apple_iap',
        'category': 'billing',
        'name': 'Apple IAP',
        'name_zh': 'Apple 内购',
        'scope': 'per_app',
        'docs_url': 'https://developer.apple.com/documentation/appstoreserverapi',
        'docs_note': 'App Store Server API (StoreKit 2). verifyReceipt 已弃用；用 Key ID / Issuer ID / .p8 签发 JWT。',
        'icon': 'apple',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'environment', 'label': 'Environment', 'label_zh': '环境', 'type': 'select',
             'options': [{'value': 'Sandbox', 'label': 'Sandbox'}, {'value': 'Production', 'label': 'Production'}],
             'default': 'Sandbox'},
            {'key': 'bundle_id', 'label': 'Bundle ID', 'label_zh': 'Bundle ID', 'type': 'text', 'required': True,
             'placeholder': 'app.spark'},
            {'key': 'app_apple_id', 'label': 'App Apple ID', 'label_zh': 'App Apple ID', 'type': 'text',
             'placeholder': '数字 App ID（App Store Connect）'},
            {'key': 'issuer_id', 'label': 'Issuer ID', 'label_zh': 'Issuer ID', 'type': 'text', 'required': True,
             'placeholder': 'UUID from Users and Access → Integrations'},
            {'key': 'key_id', 'label': 'Key ID', 'label_zh': 'Key ID', 'type': 'text', 'required': True},
            {'key': 'private_key', 'label': 'Private Key (.p8)', 'label_zh': '私钥 (.p8)', 'type': 'textarea',
             'required': True, 'secret': True, 'placeholder': '-----BEGIN PRIVATE KEY-----'},
            {'key': 'notification_url', 'label': 'Server Notifications URL', 'label_zh': '服务端通知 URL',
             'type': 'text', 'placeholder': 'https://api.example.com/api/vip/webhook/'},
        ],
    },
    {
        'key': 'google_play',
        'category': 'billing',
        'name': 'Google Play Billing',
        'name_zh': 'Google Play 内购',
        'scope': 'per_app',
        'docs_url': 'https://developers.google.com/android-publisher/api-ref/rest/v3/purchases.subscriptionsv2/get',
        'docs_note': '用服务账号调用 purchases.subscriptionsv2.get / productsv2；scope=androidpublisher。',
        'icon': 'google',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'package_name', 'label': 'Package name', 'label_zh': '包名', 'type': 'text', 'required': True,
             'placeholder': 'app.spark'},
            {'key': 'service_account_json', 'label': 'Service account JSON', 'label_zh': '服务账号 JSON',
             'type': 'textarea', 'required': True, 'secret': True,
             'placeholder': '{"type":"service_account",...}'},
        ],
    },
    {
        'key': 'google_oauth',
        'category': 'auth',
        'name': 'Google OAuth',
        'name_zh': 'Google 登录',
        'scope': 'per_app',
        'docs_url': 'https://developers.google.com/identity/sign-in/web/backend-auth',
        'docs_note': '后端必须校验 ID token 的 aud 等于 Client ID；推荐 google-auth 库。',
        'icon': 'google',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'web_client_id', 'label': 'Web Client ID', 'label_zh': 'Web Client ID', 'type': 'text',
             'required': True, 'placeholder': '...apps.googleusercontent.com'},
            {'key': 'android_client_id', 'label': 'Android Client ID', 'label_zh': 'Android Client ID', 'type': 'text'},
            {'key': 'ios_client_id', 'label': 'iOS Client ID', 'label_zh': 'iOS Client ID', 'type': 'text'},
            {'key': 'client_secret', 'label': 'Client secret (web)', 'label_zh': 'Web Client Secret',
             'type': 'password', 'secret': True},
        ],
    },
    {
        'key': 'amap',
        'category': 'maps',
        'name': 'Amap (Gaode)',
        'name_zh': '高德地图',
        'scope': 'per_app',
        'docs_url': 'https://lbs.amap.com/api/webservice/create-project-and-key',
        'docs_note': 'Web 服务 Key 用于服务端 geocode；Android/iOS Key 写入客户端 manifest。',
        'icon': 'map',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': True},
            {'key': 'rest_key', 'label': 'Web Service Key', 'label_zh': 'Web 服务 Key', 'type': 'password',
             'required': True, 'secret': True},
            {'key': 'android_key', 'label': 'Android SDK Key', 'label_zh': 'Android SDK Key', 'type': 'text',
             'secret': True},
            {'key': 'ios_key', 'label': 'iOS SDK Key', 'label_zh': 'iOS SDK Key', 'type': 'text', 'secret': True},
        ],
    },
    {
        'key': 'google_maps',
        'category': 'maps',
        'name': 'Google Maps',
        'name_zh': 'Google 地图',
        'scope': 'per_app',
        'docs_url': 'https://developers.google.com/maps/documentation/geocoding/overview',
        'docs_note': 'Geocoding API server key；客户端用 Maps SDK Android/iOS key。',
        'icon': 'map',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': True},
            {'key': 'server_key', 'label': 'Server API Key', 'label_zh': '服务端 API Key', 'type': 'password',
             'required': True, 'secret': True},
            {'key': 'android_key', 'label': 'Android SDK Key', 'label_zh': 'Android SDK Key', 'type': 'text',
             'secret': True},
            {'key': 'ios_key', 'label': 'iOS SDK Key', 'label_zh': 'iOS SDK Key', 'type': 'text', 'secret': True},
        ],
    },
    {
        'key': 'unipush',
        'category': 'push',
        'name': 'UniPush 2.0',
        'name_zh': 'UniPush 推送',
        'scope': 'per_app',
        'docs_url': 'https://uniapp.dcloud.net.cn/unipush-v2.html',
        'docs_note': 'UniPush 2.0 无 MasterSecret；业务服调用 URL 化后的 uni-cloud-push 云对象。',
        'icon': 'bell',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'uni_appid', 'label': 'DCloud AppID', 'label_zh': 'DCloud AppID', 'type': 'text',
             'required': True, 'placeholder': '__UNI__XXXXXX'},
            {'key': 'cloud_push_url', 'label': 'Cloud push URL', 'label_zh': '云对象 URL 化地址',
             'type': 'text', 'required': True,
             'placeholder': 'https://xxx.bspapp.com/http/uni-push-co'},
            {'key': 'request_secret', 'label': 'Request secret (optional)', 'label_zh': '请求鉴权 Secret（可选）',
             'type': 'password', 'secret': True},
        ],
    },
    {
        'key': 'google_ads',
        'category': 'ads',
        'name': 'Google Ads',
        'name_zh': 'Google Ads 投放',
        'scope': 'per_app',
        'docs_url': 'https://developers.google.com/google-ads/api/docs/start',
        'docs_note': '需 Developer Token + OAuth2 refresh token + Customer ID。MCC 场景填 login-customer-id。用于拉取广告系列 ID 与投放指标。',
        'icon': 'ads',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'developer_token', 'label': 'Developer token', 'label_zh': 'Developer Token',
             'type': 'password', 'required': True, 'secret': True,
             'placeholder': 'API Center → Developer token'},
            {'key': 'client_id', 'label': 'OAuth Client ID', 'label_zh': 'OAuth Client ID',
             'type': 'text', 'required': True, 'placeholder': '...apps.googleusercontent.com'},
            {'key': 'client_secret', 'label': 'OAuth Client Secret', 'label_zh': 'OAuth Client Secret',
             'type': 'password', 'required': True, 'secret': True},
            {'key': 'refresh_token', 'label': 'Refresh token', 'label_zh': 'Refresh Token',
             'type': 'password', 'required': True, 'secret': True},
            {'key': 'customer_id', 'label': 'Customer ID', 'label_zh': '客户 ID（广告账号）',
             'type': 'text', 'required': True, 'placeholder': '123-456-7890 或纯数字'},
            {'key': 'login_customer_id', 'label': 'Login customer ID (MCC)', 'label_zh': 'MCC 登录客户 ID',
             'type': 'text', 'placeholder': '经理账号 ID，可选'},
            {'key': 'api_version', 'label': 'API version', 'label_zh': 'API 版本',
             'type': 'text', 'default': 'v19', 'placeholder': 'v19'},
        ],
    },
    {
        'key': 'facebook_ads',
        'category': 'ads',
        'name': 'Facebook Ads (Meta)',
        'name_zh': 'Facebook Ads 投放',
        'scope': 'per_app',
        'docs_url': 'https://developers.facebook.com/docs/marketing-api/reference/ad-account/campaigns/',
        'docs_note': 'Marketing API：System User Access Token + Ad Account ID（act_…）。用于拉取广告系列 ID / Insights，并支撑后台归因解算。',
        'icon': 'ads',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'access_token', 'label': 'Access Token', 'label_zh': 'Access Token',
             'type': 'password', 'required': True, 'secret': True,
             'placeholder': 'System User token（ads_read）'},
            {'key': 'ad_account_id', 'label': 'Ad Account ID', 'label_zh': '广告账户 ID',
             'type': 'text', 'required': True, 'placeholder': 'act_1234567890 或纯数字'},
            {'key': 'pixel_id', 'label': 'Pixel ID (optional)', 'label_zh': 'Pixel ID（可选）',
             'type': 'text', 'placeholder': '用于转化归因对照'},
            {'key': 'api_version', 'label': 'Graph API version', 'label_zh': 'Graph API 版本',
             'type': 'text', 'default': 'v21.0', 'placeholder': 'v21.0'},
        ],
    },
    {
        'key': 'ga4',
        'category': 'analytics',
        'name': 'Google Analytics 4',
        'name_zh': 'Google Analytics 4',
        'scope': 'per_app',
        'docs_url': 'https://developers.google.com/analytics/devguides/collection/protocol/ga4',
        'docs_note': 'Measurement ID + Measurement Protocol API Secret；客户端 SDK 与服务端补报共用。后台 Analytics 面板仍读自研 t_event。',
        'icon': 'analytics',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'measurement_id', 'label': 'Measurement ID', 'label_zh': 'Measurement ID',
             'type': 'text', 'required': True, 'placeholder': 'G-XXXXXXXX'},
            {'key': 'api_secret', 'label': 'API Secret', 'label_zh': 'Measurement Protocol Secret',
             'type': 'password', 'secret': True, 'required': True},
            {'key': 'firebase_app_id', 'label': 'Firebase App ID (optional)', 'label_zh': 'Firebase App ID（可选）',
             'type': 'text'},
        ],
    },
    {
        'key': 'google_translate',
        'category': 'ai',
        'name': 'Google Translate',
        'name_zh': 'Google 翻译',
        'scope': 'global',
        'docs_url': 'https://cloud.google.com/translate/docs/reference/rest/v2/translate',
        'docs_note': 'Cloud Translation API v2；未配置时聊天翻译走 mock 前缀。',
        'icon': 'translate',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': True},
            {'key': 'api_key', 'label': 'API Key', 'label_zh': 'API Key', 'type': 'password',
             'required': True, 'secret': True},
        ],
    },
    {
        'key': 'persona',
        'category': 'trust',
        'name': 'Persona Verification',
        'name_zh': 'Persona 实名认证',
        'scope': 'global',
        'docs_url': 'https://docs.withpersona.com/api-keys',
        'docs_note': 'API Key + Inquiry Template ID (itmpl_…)；用于人脸/证件核身。',
        'icon': 'shield',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'environment', 'label': 'Environment', 'label_zh': '环境', 'type': 'select',
             'options': [
                 {'value': 'sandbox', 'label': 'Sandbox'},
                 {'value': 'production', 'label': 'Production'},
             ], 'default': 'sandbox'},
            {'key': 'api_key', 'label': 'API Key', 'label_zh': 'API Key', 'type': 'password',
             'required': True, 'secret': True, 'placeholder': 'persona_sandbox_… / persona_production_…'},
            {'key': 'inquiry_template_id', 'label': 'Inquiry template ID', 'label_zh': 'Inquiry 模板 ID',
             'type': 'text', 'required': True, 'placeholder': 'itmpl_…'},
            {'key': 'api_version', 'label': 'Persona-Version header', 'label_zh': 'API Version',
             'type': 'text', 'default': '2025-10-27'},
            {'key': 'webhook_secret', 'label': 'Webhook secret', 'label_zh': 'Webhook Secret',
             'type': 'password', 'secret': True},
        ],
    },
    {
        'key': 'apple_signin',
        'category': 'auth',
        'name': 'Apple Sign-In',
        'name_zh': 'Apple 登录',
        'scope': 'per_app',
        'docs_url': 'https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_rest_api/verifying_a_user',
        'docs_note': 'Services ID / Bundle ID 作为 aud；后端用 Apple JWKS 验 identityToken。',
        'icon': 'apple',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'client_id', 'label': 'Client ID (aud)', 'label_zh': 'Client ID (aud)', 'type': 'text',
             'required': True, 'placeholder': 'com.example.app 或 Services ID'},
            {'key': 'team_id', 'label': 'Team ID', 'label_zh': 'Team ID', 'type': 'text'},
            {'key': 'key_id', 'label': 'Key ID', 'label_zh': 'Key ID', 'type': 'text'},
            {'key': 'private_key', 'label': 'Private Key (.p8)', 'label_zh': '私钥 (.p8)', 'type': 'textarea',
             'secret': True},
        ],
    },
    {
        'key': 'twilio_sms',
        'category': 'auth',
        'name': 'Twilio SMS / Verify',
        'name_zh': 'Twilio 短信',
        'scope': 'global',
        'docs_url': 'https://www.twilio.com/docs/verify/api',
        'docs_note': 'Verify Service 用于 OTP；From Number 用于 Share My Date 短信。',
        'icon': 'sms',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'account_sid', 'label': 'Account SID', 'label_zh': 'Account SID', 'type': 'text',
             'required': True},
            {'key': 'auth_token', 'label': 'Auth Token', 'label_zh': 'Auth Token', 'type': 'password',
             'required': True, 'secret': True},
            {'key': 'verify_service_sid', 'label': 'Verify Service SID', 'label_zh': 'Verify Service SID',
             'type': 'text', 'required': True, 'placeholder': 'VA…'},
            {'key': 'from_number', 'label': 'From number (E.164)', 'label_zh': '发送号码', 'type': 'text',
             'placeholder': '+1…'},
        ],
    },
    {
        'key': 'tenor',
        'category': 'media',
        'name': 'Tenor GIF',
        'name_zh': 'Tenor 动图',
        'scope': 'global',
        'docs_url': 'https://developers.google.com/tenor/guides/endpoints',
        'docs_note': 'Google Cloud API Key with Tenor API enabled.',
        'icon': 'gif',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': True},
            {'key': 'api_key', 'label': 'API Key', 'label_zh': 'API Key', 'type': 'password',
             'required': True, 'secret': True},
            {'key': 'client_key', 'label': 'Client key', 'label_zh': 'Client key', 'type': 'text',
             'default': 'spark'},
        ],
    },
    {
        'key': 'agora',
        'category': 'realtime',
        'name': 'Agora RTC',
        'name_zh': '声网 Agora',
        'scope': 'global',
        'docs_url': 'https://docs.agora.io/en/video-calling/develop/authentication-workflow',
        'docs_note': 'App ID + App Certificate 用于签发 RTC Token。',
        'icon': 'video',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'app_id', 'label': 'App ID', 'label_zh': 'App ID', 'type': 'text', 'required': True},
            {'key': 'app_certificate', 'label': 'App Certificate', 'label_zh': 'App Certificate',
             'type': 'password', 'required': True, 'secret': True},
            {'key': 'token_expire_sec', 'label': 'Token TTL (sec)', 'label_zh': 'Token 有效期(秒)',
             'type': 'text', 'default': '3600'},
        ],
    },
    {
        'key': 'instagram_oauth',
        'category': 'social',
        'name': 'Instagram OAuth',
        'name_zh': 'Instagram 授权',
        'scope': 'global',
        'docs_url': 'https://developers.facebook.com/docs/instagram-basic-display-api',
        'docs_note': 'Basic Display / Graph：client_id + secret + redirect_uri。',
        'icon': 'instagram',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'client_id', 'label': 'Client ID', 'label_zh': 'Client ID', 'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'label_zh': 'Client Secret',
             'type': 'password', 'required': True, 'secret': True},
            {'key': 'redirect_uri', 'label': 'Redirect URI', 'label_zh': '回调 URL', 'type': 'text',
             'required': True, 'placeholder': 'https://api.example.com/api/auth/oauth/instagram/callback/'},
        ],
    },
    {
        'key': 'spotify_oauth',
        'category': 'social',
        'name': 'Spotify OAuth',
        'name_zh': 'Spotify 授权',
        'scope': 'global',
        'docs_url': 'https://developer.spotify.com/documentation/web-api/tutorials/code-flow',
        'docs_note': 'Authorization Code；redirect_uri 必须与控制台一致。',
        'icon': 'spotify',
        'fields': [
            {'key': 'enabled', 'label': 'Enabled', 'label_zh': '启用', 'type': 'switch', 'default': False},
            {'key': 'client_id', 'label': 'Client ID', 'label_zh': 'Client ID', 'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'label_zh': 'Client Secret',
             'type': 'password', 'required': True, 'secret': True},
            {'key': 'redirect_uri', 'label': 'Redirect URI', 'label_zh': '回调 URL', 'type': 'text',
             'required': True, 'placeholder': 'https://api.example.com/api/auth/oauth/spotify/callback/'},
        ],
    },
]


def get_provider_def(key: str):
    for p in PROVIDER_CATALOG:
        if p['key'] == key:
            return deepcopy(p)
    return None


def catalog_list():
    return deepcopy(PROVIDER_CATALOG)


def secret_field_keys(provider_key: str):
    p = get_provider_def(provider_key)
    if not p:
        return set()
    return {f['key'] for f in p['fields'] if f.get('secret')}


def mask_value(val: str) -> str:
    if not val:
        return ''
    s = str(val)
    if len(s) <= 8:
        return '••••••••'
    return s[:4] + '••••' + s[-4:]


def serialize_config_for_admin(provider_key: str, config: dict, reveal: bool = False) -> dict:
    """Return config with secrets masked unless reveal."""
    cfg = dict(config or {})
    secrets = secret_field_keys(provider_key)
    out = {}
    for k, v in cfg.items():
        if k in secrets and v and not reveal:
            out[k] = mask_value(str(v))
            out[f'_{k}_set'] = True
        else:
            out[k] = v
    return out


def merge_config_update(provider_key: str, existing: dict, patch: dict) -> dict:
    """Merge patch into existing; keep old secret if patch sends masked or empty."""
    secrets = secret_field_keys(provider_key)
    merged = dict(existing or {})
    for k, v in (patch or {}).items():
        if k.startswith('_'):
            continue
        if k in secrets:
            if v is None or v == '':
                continue
            if isinstance(v, str) and '••••' in v:
                continue
        merged[k] = v
    return merged


def config_status(provider_key: str, config: dict, enabled_override=None) -> str:
    """configured | partial | missing | disabled"""
    p = get_provider_def(provider_key)
    if not p:
        return 'missing'
    cfg = config or {}
    enabled = cfg.get('enabled') if enabled_override is None else enabled_override
    required = [f['key'] for f in p['fields'] if f.get('required')]
    filled = [k for k in required if cfg.get(k)]
    if enabled is False:
        return 'disabled'
    if not filled and not any(cfg.get(f['key']) for f in p['fields'] if f['key'] != 'enabled'):
        return 'missing'
    if len(filled) < len(required):
        return 'partial'
    if enabled:
        return 'configured'
    return 'partial'
