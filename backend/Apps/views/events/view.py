from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import RequireAppModule
from tools.utils import ApiResponse
from tools.rate_limit import rate_limit
from models.models import AnalyticsEvent

# Align client short names with PRD event dictionary where possible
EVENT_ALIASES = {
    'auth_welcome_view': 'welcome_view',
    'auth_login_ok': 'auth_result',
    'auth_register_ok': 'auth_result',
    'auth_google_ok': 'auth_result',
    'auth_apple_ok': 'auth_result',
    'auth_facebook_ok': 'auth_result',
    'auth_wechat_ok': 'auth_result',
    'auth_phone_ok': 'auth_result',
    'auth_sms_ok': 'auth_result',
    'app_launch': 'app_first_open',
    'onboarding_done': 'onboarding_complete',
    'paywall_open': 'paywall_show',
    'purchase': 'pay_success',
    'purchase_cn': 'pay_success',
}

# Known commercial / product events (O-08). Soft allow-list for docs + future gates;
# batch ingest still accepts other names but prefers these canonical ones.
ALLOWED_EVENT_NAMES = frozenset({
    'app_first_open', 'app_launch', 'install', 'deep_link_open',
    'welcome_view', 'auth_result', 'onboarding_complete',
    'page_view', 'btn_click', 'swipe', 'match', 'say_hi', 'sos',
    'paywall_show', 'pay_success', 'attribution', 'ad_click', 'campaign_open',
    # Commercial funnel
    'feed_exhausted', 'like_limit_hit', 'boost_impression', 'boost_start', 'boost_end',
    'super_like', 'rewind', 'unlock_like',
})

_ATTR_EVENTS = {
    'app_first_open', 'app_launch', 'install', 'deep_link_open',
    'attribution', 'ad_click', 'campaign_open',
}


@extend_schema(tags=[_('埋点')])
class EventsViewSet(viewsets.ViewSet):
    permission_classes = [RequireAppModule]

    @extend_schema(summary=_('批量上报'))
    @action(detail=False, methods=['post'], url_path='batch')
    @rate_limit('events_batch', rate=2.0, capacity=10.0, by='user')
    def batch(self, request):
        events = request.data.get('events') or []
        app_id = request.data.get('app_id') or 'spark_main'
        user = getattr(request, 'user', None)
        uid = user.id if user and getattr(user, 'id', None) else None
        rows = []
        attr_payloads = []
        forward_payloads = []
        from tools.event_dict import label_zh_for_event
        for e in events[:100]:
            if not isinstance(e, dict):
                continue
            raw_name = e.get('event') or e.get('name') or 'unknown'
            name = EVENT_ALIASES.get(str(raw_name), str(raw_name))
            props = dict(e.get('props') or {})
            if e.get('ts') is not None:
                props.setdefault('ts', e.get('ts'))
            if name != raw_name:
                props.setdefault('client_event', raw_name)
            if not props.get('event_zh'):
                props['event_zh'] = label_zh_for_event(name, props)
            rows.append(AnalyticsEvent(
                app_id=app_id,
                user_id=uid,
                event=str(name)[:64],
                props=props,
                app_version=e.get('app_version'),
                device_locale=e.get('device_locale'),
            ))
            forward_payloads.append({
                'event': str(name)[:64],
                'props': props,
                'app_version': e.get('app_version'),
                'device_locale': e.get('device_locale'),
            })
            if (
                name in _ATTR_EVENTS
                or props.get('fbclid')
                or props.get('gclid')
                or props.get('utm_source')
                or props.get('campaign_id')
            ):
                attr_payloads.append(props)
        if rows:
            AnalyticsEvent.objects.bulk_create(rows)
        if attr_payloads:
            try:
                from tools.attribution_service import ingest_attribution
                for props in attr_payloads:
                    ingest_attribution(
                        app_id=app_id,
                        user=user if uid else None,
                        data={**props, 'deep_link': props.get('deep_link') or props.get('url')},
                        auto_match=True,
                    )
            except Exception:
                pass
        # Dual channel: forward to GA4 when Provider enabled (best-effort)
        if forward_payloads:
            try:
                from tools.ga4_service import forward_events_to_ga4
                forward_events_to_ga4(app_id, forward_payloads, user_id=uid)
            except Exception:
                pass
        return ApiResponse(data={'accepted': len(rows)}, message='ok')

    @extend_schema(summary=_('上报广告归因'))
    @action(detail=False, methods=['post'], url_path='attribution')
    def attribution(self, request):
        """Client reports fbclid/gclid/utm/campaign for admin resolution."""
        from tools.attribution_service import ingest_attribution, serialize_attribution
        app_id = request.data.get('app_id') or getattr(request.user, 'app_id', None) or 'spark_main'
        user = getattr(request, 'user', None)
        row = ingest_attribution(
            app_id=app_id,
            user=user if getattr(user, 'id', None) else None,
            data=request.data,
            auto_match=True,
        )
        if not row:
            return ApiResponse(code=400, message='empty attribution payload')
        return ApiResponse(data=serialize_attribution(row), message='ok', code=201)
