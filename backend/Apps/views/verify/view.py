from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils import timezone
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.persona_service import create_inquiry, parse_webhook_event, persona_configured
from models.models import VerifyInquiry, User


@extend_schema(tags=[_('核验')])
class VerifyViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action == 'webhook':
            return []
        return [IsTokenValid(), RequireAppModule()]

    @extend_schema(summary=_('发起人脸/照片核验'))
    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        user = request.user
        if user.is_verified:
            return ApiResponse(data={'is_verified': True, 'status': 'approved'}, message='ok')
        pending = VerifyInquiry.objects.filter(
            user=user, status__in=(VerifyInquiry.STATUS_CREATED, VerifyInquiry.STATUS_PENDING),
        ).order_by('-id').first()
        if pending:
            return ApiResponse(data={
                'inquiry_id': pending.inquiry_id,
                'status': pending.status,
                'is_verified': False,
                'persona_configured': persona_configured(),
            }, message='ok')
        result = create_inquiry(str(user.id), note=f'app={user.app_id}')
        if not result.get('ok'):
            return ApiResponse(code=502, message=result.get('error') or 'persona_failed')
        row = VerifyInquiry.objects.create(
            user=user,
            app_id=user.app_id or 'spark_main',
            inquiry_id=result['inquiry_id'],
            status=VerifyInquiry.STATUS_PENDING if not result.get('mock') else VerifyInquiry.STATUS_CREATED,
            raw=result,
        )
        return ApiResponse(data={
            'inquiry_id': row.inquiry_id,
            'status': row.status,
            'is_verified': False,
            'mock': bool(result.get('mock')),
            'persona_configured': persona_configured(),
            'hosted_url': result.get('hosted_url') or '',
            'inquiry_session_token': result.get('inquiry_session_token') or '',
        }, message='ok')

    @extend_schema(summary=_('核验状态'))
    @action(detail=False, methods=['get'], url_path='status')
    def status(self, request):
        user = request.user
        latest = VerifyInquiry.objects.filter(user=user).order_by('-id').first()
        return ApiResponse(data={
            'is_verified': bool(user.is_verified),
            'inquiry_id': latest.inquiry_id if latest else None,
            'status': latest.status if latest else None,
            'persona_configured': persona_configured(),
        }, message='ok')

    @extend_schema(summary=_('沙盒：模拟通过/驳回'))
    @action(detail=False, methods=['post'], url_path='sandbox/decide')
    def sandbox_decide(self, request):
        """Only when Persona mode=sandbox or not configured."""
        from tools.provider_helpers import get_raw_provider_config
        cfg = get_raw_provider_config('persona')
        mode = (cfg.get('mode') or 'sandbox').lower()
        if persona_configured() and mode != 'sandbox':
            return ApiResponse(code=400, message='use_persona_webhook')
        user = request.user
        approve = bool(request.data.get('approve', True))
        inquiry_id = (request.data.get('inquiry_id') or '').strip()
        row = None
        if inquiry_id:
            row = VerifyInquiry.objects.filter(user=user, inquiry_id=inquiry_id).first()
        if not row:
            row = VerifyInquiry.objects.filter(user=user).order_by('-id').first()
        if not row:
            return ApiResponse(code=404, message='no_inquiry')
        row.status = VerifyInquiry.STATUS_APPROVED if approve else VerifyInquiry.STATUS_DECLINED
        row.decided_at = timezone.now()
        row.save(update_fields=['status', 'decided_at', 'updated_at'])
        user.is_verified = bool(approve)
        user.save(update_fields=['is_verified', 'updated_at'])
        return ApiResponse(data={
            'is_verified': user.is_verified,
            'status': row.status,
            'inquiry_id': row.inquiry_id,
        }, message='ok')

    @extend_schema(summary=_('Persona Webhook'))
    @action(detail=False, methods=['post'], url_path='webhook', permission_classes=[])
    def webhook(self, request):
        parsed = parse_webhook_event(request.data if isinstance(request.data, dict) else {})
        inquiry_id = parsed.get('inquiry_id') or ''
        if not inquiry_id:
            return ApiResponse(message='ok')
        row = VerifyInquiry.objects.filter(inquiry_id=inquiry_id).select_related('user').first()
        if not row:
            # Try reference_id as user id
            ref = parsed.get('reference_id') or ''
            if ref.isdigit():
                row = VerifyInquiry.objects.filter(user_id=int(ref)).order_by('-id').first()
        if not row:
            return ApiResponse(message='ok')
        if parsed.get('approved'):
            row.status = VerifyInquiry.STATUS_APPROVED
            row.user.is_verified = True
            row.user.save(update_fields=['is_verified', 'updated_at'])
        elif parsed.get('declined'):
            row.status = VerifyInquiry.STATUS_DECLINED
            row.user.is_verified = False
            row.user.save(update_fields=['is_verified', 'updated_at'])
        else:
            row.status = VerifyInquiry.STATUS_PENDING
        row.decided_at = timezone.now()
        row.raw = request.data if isinstance(request.data, dict) else {'raw': str(request.data)}
        row.save(update_fields=['status', 'decided_at', 'raw', 'updated_at'])
        return ApiResponse(message='ok')
