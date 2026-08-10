import secrets
from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from models.models import AnalyticsEvent, DateShare, EmergencyContact, UserSafetyPref
from tools.permissions import IsTokenValid, RequireAppModule
from tools.sms_service import normalize_phone, send_sms
from tools.utils import ApiResponse


def _emergency_phone(user):
    row = EmergencyContact.objects.filter(user=user).first()
    phone = (row.phone if row else '') or ''
    if phone:
        return phone
    pref = UserSafetyPref.objects.filter(user=user).first()
    return ((pref.emergency_contact or {}).get('phone') if pref else '') or ''


def _sync_emergency(user, name, phone):
    row, _ = EmergencyContact.objects.get_or_create(user=user)
    row.name = name
    row.phone = phone
    row.save()
    pref, _ = UserSafetyPref.objects.get_or_create(user=user)
    pref.emergency_contact = {'name': name, 'phone': phone}
    pref.save(update_fields=['emergency_contact', 'updated_at'])
    return row


def _create_date_share(request, *, notify_sms=False):
    user = request.user
    data = request.data
    peer_name = (data.get('peer_name') or data.get('with') or '')[:64]
    place = (data.get('place') or '')[:256]
    venue = (data.get('venue') or place or '')[:256]
    when_text = (data.get('when_text') or data.get('when') or '')[:128]
    note = (data.get('note') or '')[:2000]
    token = secrets.token_urlsafe(32)
    share = DateShare.objects.create(
        user=user,
        peer_name=peer_name,
        place=place,
        venue=venue,
        when_text=when_text,
        lat=data.get('lat') or None,
        lng=data.get('lng') or None,
        note=note,
        share_token=token,
        expires_at=timezone.now() + timedelta(hours=24),
        sms_sent=False,
    )
    share_url = request.build_absolute_uri(f'/api/safety/date-share/{token}/')
    share_text = (
        f"{user.nickname or user.username} shared a date plan: "
        f"{share.venue or share.place}. {share_url}"
    )
    sms_ok = False
    sms_result = {}
    if notify_sms:
        phone = _emergency_phone(user)
        body = (
            f"{user.nickname or user.username} is on a date"
            + (f" with {peer_name}" if peer_name else "")
            + (f" at {venue or place}" if (venue or place) else "")
            + (f" ({when_text})" if when_text else "")
            + (f". Note: {note}" if note else "")
            + f". {share_url}"
        )
        if phone:
            sms_result = send_sms(phone, body)
            sms_ok = bool(sms_result.get('ok'))
            share.sms_sent = sms_ok
            share.save(update_fields=['sms_sent'])
        share_text = body
    return share, share_url, share_text, sms_ok, sms_result


@extend_schema(tags=[_('安全中心')])
class SafetyViewSet(viewsets.ViewSet):
    """Merged safety APIs: client contract + legacy aliases."""

    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('安全偏好'))
    @action(detail=False, methods=['get', 'put'], url_path='pref')
    def pref(self, request):
        pref, _ = UserSafetyPref.objects.get_or_create(user=request.user)
        if request.method == 'PUT':
            contact = request.data.get('emergency_contact', pref.emergency_contact or {})
            if not isinstance(contact, dict):
                return ApiResponse(code=400, message='emergency_contact must be an object')
            words = request.data.get('blocked_words', pref.blocked_words or [])
            if not isinstance(words, list):
                return ApiResponse(code=400, message='blocked_words must be a list')
            name = str(contact.get('name') or '')[:64]
            phone = str(contact.get('phone') or '')[:32]
            pref.emergency_contact = {'name': name, 'phone': phone}
            pref.blocked_words = [str(word).strip()[:128] for word in words if str(word).strip()][:100]
            pref.save(update_fields=['emergency_contact', 'blocked_words', 'updated_at'])
            _sync_emergency(request.user, name, phone)
        return ApiResponse(data={
            'emergency_contact': pref.emergency_contact or {},
            'blocked_words': pref.blocked_words or [],
        }, message='ok')

    @extend_schema(summary=_('紧急联系人'))
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='emergency')
    def emergency(self, request):
        user = request.user
        if request.method == 'GET':
            row = EmergencyContact.objects.filter(user=user).first()
            pref = UserSafetyPref.objects.filter(user=user).first()
            data = {
                'name': (row.name if row else '') or ((pref.emergency_contact or {}).get('name') if pref else ''),
                'phone': (row.phone if row else '') or ((pref.emergency_contact or {}).get('phone') if pref else ''),
            }
            return ApiResponse(data=data, message='ok')
        name = (request.data.get('name') or '').strip()[:64]
        phone = normalize_phone(request.data.get('phone') or '')
        _sync_emergency(user, name, phone)
        return ApiResponse(data={'name': name, 'phone': phone}, message='ok')

    @extend_schema(summary=_('约会分享'))
    @action(detail=False, methods=['post'], url_path='date-share')
    def date_share(self, request):
        share, share_url, share_text, sms_ok, sms_result = _create_date_share(
            request, notify_sms=bool(request.data.get('notify_sms')),
        )
        return ApiResponse(data={
            'id': share.id,
            'share_token': share.share_token,
            'share_url': share_url,
            'share_text': share_text,
            'expires_at': share.expires_at.isoformat(),
            'sms_sent': sms_ok,
            'sms': sms_result,
        }, message='ok', code=201)

    @extend_schema(summary=_('Share My Date（兼容别名）'))
    @action(detail=False, methods=['post'], url_path='share-date')
    def share_date(self, request):
        share, share_url, share_text, sms_ok, sms_result = _create_date_share(
            request, notify_sms=True,
        )
        return ApiResponse(data={
            'id': share.id,
            'share_token': share.share_token,
            'share_url': share_url,
            'sms_sent': sms_ok,
            'sms': sms_result,
            'message_preview': share_text,
            'expires_at': share.expires_at.isoformat(),
        }, message='ok', code=201)

    @extend_schema(summary=_('约会分享详情'))
    @action(detail=False, methods=['get'], url_path=r'date-share/(?P<token>[^/.]+)')
    def date_share_detail(self, request, token=None):
        share = DateShare.objects.filter(share_token=token, expires_at__gt=timezone.now()).first()
        if not share:
            return ApiResponse(code=404, message='not found')
        return ApiResponse(data={
            'peer_name': share.peer_name,
            'place': share.place,
            'venue': share.venue,
            'when_text': share.when_text,
            'meet_at': share.meet_at.isoformat() if share.meet_at else None,
            'lat': share.lat,
            'lng': share.lng,
            'note': share.note,
            'expires_at': share.expires_at.isoformat(),
        }, message='ok')

    @extend_schema(summary=_('SOS'))
    @action(detail=False, methods=['post'], url_path='sos')
    def sos(self, request):
        user = request.user
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        AnalyticsEvent.objects.create(
            app_id=user.app_id or 'spark_main',
            user=user,
            event='sos',
            props={'lat': lat, 'lng': lng},
        )
        phone = _emergency_phone(user)
        sms_ok = False
        sms_result = {}
        if phone:
            body = (
                f"SOS from {user.nickname or user.username}"
                + (f" at ({lat}, {lng})" if lat is not None and lng is not None else "")
            )
            sms_result = send_sms(phone, body)
            sms_ok = bool(sms_result.get('ok'))
        country = (user.country or 'US').upper()
        emergency_number = '110' if country in ('CN', 'HK', 'TW', 'MO') else '911'
        return ApiResponse(data={
            'dial_hint': f'tel:{emergency_number}',
            'emergency_number': emergency_number,
            'sms_sent': sms_ok,
            'sms': sms_result,
        }, message='ok')

    @extend_schema(summary=_('屏蔽词'))
    @action(detail=False, methods=['get', 'put'], url_path='blocked-words')
    def blocked_words(self, request):
        pref, _ = UserSafetyPref.objects.get_or_create(user=request.user)
        if request.method == 'GET':
            return ApiResponse(data={'list': pref.blocked_words or []}, message='ok')
        words = request.data.get('list') or request.data.get('words') or []
        if not isinstance(words, list):
            return ApiResponse(code=400, message='list required')
        pref.blocked_words = [str(w).strip() for w in words if str(w).strip()][:100]
        pref.save(update_fields=['blocked_words', 'updated_at'])
        return ApiResponse(data={'list': pref.blocked_words}, message='ok')
