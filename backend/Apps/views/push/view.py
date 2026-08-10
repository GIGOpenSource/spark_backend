from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.push_service import mark_recall_opened, touch_user_activity
from models.models import UserPushToken, UserNotificationPref


@extend_schema(tags=[_('推送')])
class PushViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('上报 Push ClientId'))
    @action(detail=False, methods=['post'], url_path='token')
    def token(self, request):
        user = request.user
        client_id = (request.data.get('client_id') or '').strip()
        platform = (request.data.get('platform') or 'android').strip().lower()[:16]
        enabled = request.data.get('enabled')
        if enabled is None:
            enabled = True
        enabled = bool(enabled)
        if platform not in ('ios', 'android', 'h5'):
            platform = 'android'
        if not client_id and enabled and platform != 'h5':
            return ApiResponse(code=400, message='client_id required')
        app_id = getattr(user, 'app_id', None) or 'spark_main'
        if not client_id:
            # disable existing token for platform
            UserPushToken.objects.filter(user=user, app_id=app_id, platform=platform).update(enabled=False)
            return ApiResponse(data={'enabled': False}, message='ok')
        obj, _ = UserPushToken.objects.update_or_create(
            user=user, app_id=app_id, platform=platform,
            defaults={'client_id': client_id[:256], 'enabled': enabled},
        )
        touch_user_activity(user, app_id=app_id)
        return ApiResponse(data={
            'id': obj.id,
            'platform': obj.platform,
            'enabled': obj.enabled,
            'client_id': obj.client_id,
        }, message='ok')

    @extend_schema(summary=_('召回 Push 打开回执'))
    @action(detail=False, methods=['post'], url_path='opened')
    def opened(self, request):
        user = request.user
        app_id = getattr(user, 'app_id', None) or 'spark_main'
        mark_recall_opened(user, app_id=app_id)
        return ApiResponse(message='ok')

    def _pref_payload(self, pref):
        return {
            'likes': bool(pref.likes),
            'matches': bool(pref.matches),
            'messages': bool(pref.messages),
            'marketing': bool(pref.marketing),
            'silent_recall': bool(pref.silent_recall),
        }

    @extend_schema(summary=_('通知偏好'))
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='prefs')
    def prefs(self, request):
        user = request.user
        pref, _ = UserNotificationPref.objects.get_or_create(user=user)
        if request.method in ('PUT', 'PATCH'):
            data = request.data or {}
            for key in ('likes', 'matches', 'messages', 'marketing', 'silent_recall'):
                if key in data:
                    setattr(pref, key, bool(data.get(key)))
            pref.save()
        return ApiResponse(data=self._pref_payload(pref), message='ok')
