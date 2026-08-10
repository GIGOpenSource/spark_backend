from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.utils import ApiResponse
from tools.spark_helpers import get_effective_config, check_review_mode, get_product_profile, list_active_ops_banners
from tools.app_modules import get_enabled_modules
from tools.maps_helpers import build_bootstrap_maps
from tools.iap_service import apple_configured, play_configured
from tools.google_oauth_service import google_oauth_configured
from tools.persona_service import persona_configured
from tools.apple_signin_service import apple_signin_configured
from tools.sms_service import sms_configured
from tools.tenor_service import tenor_configured
from tools.agora_service import agora_configured
from tools.social_oauth_service import instagram_configured, spotify_configured
from tools.ga4_service import analytics_feature_flags
from models.models import AppConfig, DiscoverParam
from django.conf import settings


@extend_schema(tags=[_('Bootstrap')])
class BootstrapViewSet(viewsets.ViewSet):
    @extend_schema(summary=_('获取启动配置'))
    @action(detail=False, methods=['get'], url_path='config')
    def config(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        country = request.query_params.get('country') or '*'
        platform = request.query_params.get('platform') or 'h5'
        package_name = request.query_params.get('package_name') or ''
        version = request.query_params.get('app_version') or '1.0.0'
        app = AppConfig.objects.filter(app_id=app_id).first()
        if app and app.package_name:
            if not package_name or package_name != app.package_name:
                return ApiResponse(
                    code=403,
                    message='package_name 与 APP 配置不匹配',
                    data={'expected_package': app.package_name},
                )
        review_mode = check_review_mode(app_id, platform, package_name or 'app.spark', version)
        param = DiscoverParam.objects.filter(app_id=app_id, country=country).first()
        if not param:
            param = DiscoverParam.objects.filter(app_id=app_id, country='*').first()
        product_profile = get_product_profile(app_id)
        enabled_modules = get_enabled_modules(app_id)
        effective_config = get_effective_config(app_id, country)
        iap_ready = apple_configured(app_id) or play_configured(app_id)
        oauth_ready = google_oauth_configured(app_id)
        # Mock flags: env force-mock OR credentials missing
        iap_mock = bool(getattr(settings, 'USE_IAP_MOCK', False)) or not iap_ready
        firebase_mock = bool(getattr(settings, 'USE_FIREBASE_MOCK', False)) or not oauth_ready
        data = {
            'app_id': app_id,
            'app_name': app.name if app else 'SPARK',
            'package_name': (app.package_name if app else None) or package_name,
            'tos_url': app.tos_url if app else 'https://spark.app/tos',
            'privacy_url': app.privacy_url if app else 'https://spark.app/privacy',
            'community_guidelines_url': (app.config or {}).get('community_guidelines_url') if app else None,
            'review_mode': review_mode,
            'effective_config': effective_config,
            'product_profile': product_profile,
            'enabled_modules': enabled_modules,
            'maps': build_bootstrap_maps(request, effective_config),
            'discover': {
                'daily_like_limit': param.daily_like_limit if param else 50,
                'match_expire_days': param.match_expire_days if param else 7,
                'match_open_hours': product_profile.get('match_open_hours'),
                'daily_feed_cap': product_profile.get('daily_feed_cap'),
                'daily_feed_vip_bonus': product_profile.get('daily_feed_vip_bonus'),
            },
            'features': {
                'iap_mock': iap_mock,
                'firebase_mock': firebase_mock,
                'sms_mock': bool(getattr(settings, 'USE_SMS_MOCK', False)) or not sms_configured(),
                'agora_mock': bool(getattr(settings, 'USE_AGORA_MOCK', False)) or not agora_configured(),
                'iap_configured': iap_ready,
                'google_oauth_configured': oauth_ready,
                'apple_signin_configured': apple_signin_configured(app_id),
                'sms_configured': sms_configured(),
                'persona_configured': persona_configured(),
                'tenor_configured': tenor_configured(),
                'agora_configured': agora_configured(),
                'instagram_oauth_configured': instagram_configured(),
                'spotify_oauth_configured': spotify_configured(),
                'extend_enabled': bool(product_profile.get('extend_enabled')),
                'compliment_enabled': bool(product_profile.get('compliment_enabled')),
                'qa_gate_enabled': bool(
                    product_profile.get('qa_gate_enabled')
                    or product_profile.get('messaging_mode') == 'qa_gate'
                ),
                'enabled_modules': enabled_modules,
                'pay_channel': product_profile.get('pay_channel') or ('cn' if app_id == 'matchup_main' else 'iap'),
                'social_providers': product_profile.get('social_providers') or [],
                'analytics': analytics_feature_flags(app_id),
            },
            'pay_channel': product_profile.get('pay_channel') or ('cn' if app_id == 'matchup_main' else 'iap'),
            'ops_banners': list_active_ops_banners(app_id),
            'banners': list_active_ops_banners(app_id),
        }
        return ApiResponse(data=data, message='ok')
