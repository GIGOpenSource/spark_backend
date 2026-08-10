from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action

from models.models import SelectQueue, User
from tools.permissions import IsTokenValid, RequireAppModule
from tools.spark_helpers import blocked_ids, has_vip_at_least, serialize_user_card
from tools.utils import ApiResponse


@extend_schema(tags=[_('Select')])
class SelectViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @action(detail=False, methods=['post'], url_path='apply')
    def apply(self, request):
        row, created = SelectQueue.objects.get_or_create(
            user=request.user, app_id=request.user.app_id or 'spark_main',
            defaults={'note': (request.data.get('note') or '')[:256]},
        )
        return ApiResponse(data={'id': row.id, 'status': row.status, 'created': created}, message='ok',
                           code=201 if created else 200)

    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        row = SelectQueue.objects.filter(user=request.user, app_id=request.user.app_id or 'spark_main').first()
        return ApiResponse(data={'status': row.status if row else None, 'id': row.id if row else None}, message='ok')

    @action(detail=False, methods=['get'], url_path='feed')
    def feed(self, request):
        user = request.user
        selected = SelectQueue.objects.filter(
            user=user, app_id=user.app_id or 'spark_main', status=SelectQueue.STATUS_SELECTED,
        ).exists()
        if not selected and not has_vip_at_least(user, 'gold'):
            return ApiResponse(code=403, message='select_or_gold_required', data={'need_vip': True})
        ids = SelectQueue.objects.filter(
            app_id=user.app_id or 'spark_main', status=SelectQueue.STATUS_SELECTED,
        ).exclude(user=user).values_list('user_id', flat=True)
        rows = User.objects.filter(id__in=ids, discovery_enabled=True, status=1).exclude(
            id__in=blocked_ids(user)
        ).order_by('-online_at', '-id')[:50]
        return ApiResponse(data={'list': [serialize_user_card(row) for row in rows]}, message='ok')
