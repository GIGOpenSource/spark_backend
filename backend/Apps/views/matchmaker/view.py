from django.db.models import Q
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action

from models.models import MatchmakerInvite, User
from tools.permissions import IsTokenValid, RequireAppModule
from tools.spark_helpers import get_or_create_pair_match, serialize_user_card
from tools.utils import ApiResponse


def _serialize(invite, viewer):
    other = invite.user_b if invite.user_a_id == viewer.id else invite.user_a
    status = invite.a_status if invite.user_a_id == viewer.id else invite.b_status
    return {'id': invite.id, 'matchmaker': serialize_user_card(invite.matchmaker), 'user': serialize_user_card(other),
            'message': invite.message, 'status': status, 'match_id': invite.match_id,
            'created_at': invite.created_at.isoformat()}


@extend_schema(tags=[_('Matchmaker')])
class MatchmakerViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @action(detail=False, methods=['post'], url_path='invite')
    def invite(self, request):
        user = request.user
        try:
            a = User.objects.get(id=int(request.data.get('user_a_id')), app_id=user.app_id, status=1)
            b = User.objects.get(id=int(request.data.get('user_b_id')), app_id=user.app_id, status=1)
        except (User.DoesNotExist, TypeError, ValueError):
            return ApiResponse(code=404, message='not found')
        if a.id == b.id or user.id in (a.id, b.id):
            return ApiResponse(code=400, message='two distinct other users required')
        invite = MatchmakerInvite.objects.create(matchmaker=user, user_a=a, user_b=b,
                                                  message=(request.data.get('message') or '')[:256])
        return ApiResponse(data={'invite_id': invite.id}, message='ok', code=201)

    @action(detail=False, methods=['get'], url_path='inbox')
    def inbox(self, request):
        rows = MatchmakerInvite.objects.filter(Q(user_a=request.user) | Q(user_b=request.user)).select_related(
            'matchmaker', 'user_a', 'user_b').order_by('-id')[:100]
        return ApiResponse(data={'list': [_serialize(row, request.user) for row in rows]}, message='ok')

    @action(detail=False, methods=['post'], url_path='respond')
    def respond(self, request):
        invite = MatchmakerInvite.objects.filter(id=request.data.get('invite_id')).filter(
            Q(user_a=request.user) | Q(user_b=request.user)).select_related('user_a', 'user_b').first()
        if not invite:
            return ApiResponse(code=404, message='not found')
        accepted = bool(request.data.get('accept'))
        field = 'a_status' if invite.user_a_id == request.user.id else 'b_status'
        setattr(invite, field, MatchmakerInvite.STATUS_ACCEPTED if accepted else MatchmakerInvite.STATUS_DECLINED)
        if not accepted:
            invite.save(update_fields=[field])
            return ApiResponse(data={'invite_id': invite.id, 'status': 'declined'}, message='ok')
        if invite.a_status == MatchmakerInvite.STATUS_ACCEPTED and invite.b_status == MatchmakerInvite.STATUS_ACCEPTED:
            match, _ = get_or_create_pair_match(invite.user_a_id, invite.user_b_id, app_id=request.user.app_id)
            invite.match = match
            invite.a_status = invite.b_status = MatchmakerInvite.STATUS_MATCHED
            invite.save(update_fields=['a_status', 'b_status', 'match'])
            return ApiResponse(data={'invite_id': invite.id, 'status': 'matched', 'match_id': match.id}, message='ok')
        invite.save(update_fields=[field])
        return ApiResponse(data={'invite_id': invite.id, 'status': 'accepted'}, message='ok')

    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request):
        """Matchmaker voids a pending invite."""
        invite = MatchmakerInvite.objects.filter(
            id=request.data.get('invite_id'), matchmaker=request.user,
        ).first()
        if not invite:
            return ApiResponse(code=404, message='not found')
        if invite.a_status == MatchmakerInvite.STATUS_MATCHED:
            return ApiResponse(code=400, message='already_matched')
        invite.a_status = MatchmakerInvite.STATUS_DECLINED
        invite.b_status = MatchmakerInvite.STATUS_DECLINED
        invite.save(update_fields=['a_status', 'b_status'])
        return ApiResponse(data={'invite_id': invite.id, 'status': 'cancelled'}, message='ok')
