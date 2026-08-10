import math
from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action

from models.models import FaceToFaceSession
from tools.permissions import IsTokenValid, RequireAppModule
from tools.spark_helpers import blocked_ids, serialize_user_card
from tools.utils import ApiResponse


def _distance_km(lat1, lng1, lat2, lng2):
    radius = 6371.0
    dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


@extend_schema(tags=[_('Face to Face')])
class FaceToFaceViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        try:
            lat, lng = float(request.data.get('lat')), float(request.data.get('lng'))
            radius = max(0.1, min(float(request.data.get('radius_km') or 2), 50))
            minutes = max(1, min(int(request.data.get('minutes') or 30), 120))
        except (TypeError, ValueError):
            return ApiResponse(code=400, message='valid lat and lng required')
        FaceToFaceSession.objects.filter(user=request.user, is_active=True).update(
            is_active=False, end_at=timezone.now(),
        )
        # Expire stale sessions globally for this app
        FaceToFaceSession.objects.filter(
            user__app_id=request.user.app_id, is_active=True, end_at__lte=timezone.now(),
        ).update(is_active=False)
        row = FaceToFaceSession.objects.create(
            user=request.user, lat=lat, lng=lng, radius_km=radius,
            end_at=timezone.now() + timedelta(minutes=minutes),
        )
        return ApiResponse(data={'id': row.id, 'end_at': row.end_at.isoformat(), 'radius_km': row.radius_km}, message='ok', code=201)

    @action(detail=False, methods=['get'], url_path='feed')
    def feed(self, request):
        current = FaceToFaceSession.objects.filter(
            user=request.user, is_active=True, end_at__gt=timezone.now(),
        ).order_by('-id').first()
        if not current:
            return ApiResponse(code=400, message='start face_to_face first')
        rows = FaceToFaceSession.objects.filter(
            is_active=True, end_at__gt=timezone.now(), user__app_id=request.user.app_id,
        ).exclude(user=request.user).select_related('user').order_by('-id')
        blocked = blocked_ids(request.user)
        items = []
        for row in rows:
            if row.user_id in blocked or not row.user.discovery_enabled or row.user.status != 1:
                continue
            distance = _distance_km(current.lat, current.lng, row.lat, row.lng)
            if distance <= min(current.radius_km, row.radius_km):
                card = serialize_user_card(row.user)
                card['distance_km'] = round(distance, 2)
                card['session_id'] = row.id
                items.append(card)
        return ApiResponse(data={'list': items}, message='ok')

    @action(detail=False, methods=['post'], url_path='stop')
    def stop(self, request):
        updated = FaceToFaceSession.objects.filter(user=request.user, is_active=True).update(
            is_active=False, end_at=timezone.now(),
        )
        return ApiResponse(data={'stopped': updated}, message='ok')
