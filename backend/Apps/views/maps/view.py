from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid
from tools.utils import ApiResponse
from tools.spark_helpers import get_effective_config
from tools.maps_helpers import (
    build_bootstrap_maps,
    resolve_map_provider,
    normalize_maps_config,
    geocode_places,
    reverse_geocode,
)
from tools.app_modules import resolve_request_app_id_for_module


@extend_schema(tags=[_('Maps')])
class MapsViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid]

    def _app_id(self, request):
        return resolve_request_app_id_for_module(request) or getattr(request.user, 'app_id', None) or 'spark_main'

    def _provider(self, request):
        app_id = self._app_id(request)
        country = request.query_params.get('country') or getattr(request.user, 'country', None) or '*'
        effective = get_effective_config(app_id, country)
        maps_cfg = normalize_maps_config((effective or {}).get('maps'))
        forced = (request.query_params.get('provider') or '').strip().lower()
        if forced in ('amap', 'google'):
            return forced
        return resolve_map_provider(request, maps_cfg)

    @extend_schema(summary=_('城市/地址地理编码搜索'))
    @action(detail=False, methods=['get'], url_path='geocode')
    def geocode(self, request):
        q = request.query_params.get('q') or request.query_params.get('address') or ''
        provider = self._provider(request)
        data = geocode_places(q, provider, app_id=self._app_id(request))
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('逆地理编码'))
    @action(detail=False, methods=['get'], url_path='regeo')
    def regeo(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
        except (TypeError, ValueError):
            return ApiResponse(code=400, message='lat and lng required')
        provider = self._provider(request)
        data = reverse_geocode(lat, lng, provider, app_id=self._app_id(request))
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('当前地图 provider（调试）'))
    @action(detail=False, methods=['get'], url_path='provider')
    def provider(self, request):
        app_id = resolve_request_app_id_for_module(request) or getattr(request.user, 'app_id', None) or 'spark_main'
        country = request.query_params.get('country') or getattr(request.user, 'country', None) or '*'
        effective = get_effective_config(app_id, country)
        return ApiResponse(data=build_bootstrap_maps(request, effective), message='ok')
