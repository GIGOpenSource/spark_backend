from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from models.models import CampusProfile, User
from tools.permissions import IsTokenValid, RequireAppModule
from tools.spark_helpers import blocked_ids, serialize_user_card
from tools.utils import ApiResponse

EDU_DOMAINS = ('.edu', '.edu.cn', '.ac.uk', '.ac.jp')


def _looks_like_edu(email: str) -> bool:
    e = (email or '').lower()
    return any(e.endswith(d) for d in EDU_DOMAINS)


def _serialize_campus(campus):
    if not campus:
        return None
    return {
        'school': campus.school,
        'edu_email': campus.edu_email,
        'verified': bool(campus.verified) or campus.status == CampusProfile.STATUS_VERIFIED,
        'status': campus.status,
        'reject_reason': campus.reject_reason or '',
        'verified_at': campus.verified_at.isoformat() if campus.verified_at else None,
    }


@extend_schema(tags=[_('Campus')])
class CampusViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @action(detail=False, methods=['post'], url_path='bind')
    def bind(self, request):
        school = (request.data.get('school') or '').strip()
        email = (request.data.get('edu_email') or '').strip().lower()
        if not school or not email:
            return ApiResponse(code=400, message='school and edu_email required')
        if '@' not in email:
            return ApiResponse(code=400, message='invalid_edu_email')
        campus, created = CampusProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'school': school[:128],
                'edu_email': email[:254],
                'status': CampusProfile.STATUS_PENDING,
                'verified': False,
            },
        )
        if not created:
            campus.school = school[:128]
            campus.edu_email = email[:254]
            if campus.status == CampusProfile.STATUS_VERIFIED:
                campus.status = CampusProfile.STATUS_PENDING
                campus.verified = False
                campus.verified_at = None
            campus.save()
        request.user.school = campus.school
        request.user.save(update_fields=['school', 'updated_at'])
        return ApiResponse(data=_serialize_campus(campus), message='ok')

    @action(detail=False, methods=['post'], url_path='verify')
    def verify(self, request):
        """Submit campus verification → pending (admin may approve) or auto-verify edu domains in sandbox."""
        campus = CampusProfile.objects.filter(user=request.user).first()
        if not campus:
            return ApiResponse(code=400, message='bind campus first')
        if not campus.edu_email or not _looks_like_edu(campus.edu_email):
            campus.status = CampusProfile.STATUS_PENDING
            campus.verified = False
            campus.reject_reason = 'edu_email_domain_required'
            campus.save(update_fields=['status', 'verified', 'reject_reason'])
            return ApiResponse(
                code=400,
                message='edu_email_domain_required',
                data=_serialize_campus(campus),
            )
        # Auto-approve recognizable .edu for MVP; still visible to admin as verified.
        campus.status = CampusProfile.STATUS_VERIFIED
        campus.verified = True
        campus.verified_at = timezone.now()
        campus.reject_reason = ''
        campus.save(update_fields=['status', 'verified', 'verified_at', 'reject_reason'])
        return ApiResponse(data=_serialize_campus(campus), message='ok')

    @action(detail=False, methods=['post'], url_path='verify-stub')
    def verify_stub(self, request):
        """Alias kept for older clients — same as verify."""
        return self.verify(request)

    @action(detail=False, methods=['get'], url_path='feed')
    def feed(self, request):
        school = request.user.school
        if not school:
            return ApiResponse(code=400, message='bind campus first')
        own = CampusProfile.objects.filter(user=request.user).first()
        if not own or own.status != CampusProfile.STATUS_VERIFIED:
            return ApiResponse(code=403, message='campus_not_verified', data=_serialize_campus(own))
        verified_ids = CampusProfile.objects.filter(
            school=school, status=CampusProfile.STATUS_VERIFIED,
        ).values_list('user_id', flat=True)
        rows = User.objects.filter(
            app_id=request.user.app_id,
            id__in=verified_ids,
            school=school,
            discovery_enabled=True,
            status=1,
        ).exclude(id=request.user.id).exclude(id__in=blocked_ids(request.user)).order_by(
            '-online_at', '-id',
        )[:50]
        return ApiResponse(data={
            'school': school,
            'status': own.status,
            'list': [serialize_user_card(user) for user in rows],
        }, message='ok')
