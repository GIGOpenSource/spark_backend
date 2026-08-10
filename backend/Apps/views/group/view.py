from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.spark_helpers import serialize_user_card, message_contains_banned, blocked_ids
from models.models import ChatRoom, ChatRoomMember, ChatRoomMessage, User


def _member_of(room, user):
    return ChatRoomMember.objects.filter(room=room, user=user).first()


def _serialize_room(room, viewer=None):
    member_count = room.members.count()
    my_role = None
    if viewer is not None:
        m = _member_of(room, viewer)
        my_role = m.role if m else None
    return {
        'id': room.id,
        'app_id': room.app_id,
        'name': room.name,
        'avatar': room.avatar or '',
        'status': room.status,
        'max_members': room.max_members,
        'member_count': member_count,
        'my_role': my_role,
        'owner_id': room.owner_id,
        'last_message': room.last_message or '',
        'last_at': room.last_at.isoformat() if room.last_at else None,
        'created_at': room.created_at.isoformat() if room.created_at else None,
    }


def _broadcast(room_id, payload):
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'group_{room_id}',
                {'type': 'group.message', 'data': payload},
            )
    except Exception:
        pass


@extend_schema(tags=[_('群聊')])
class GroupViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('我的群列表'))
    @action(detail=False, methods=['get'], url_path='rooms')
    def rooms(self, request):
        user = request.user
        room_ids = ChatRoomMember.objects.filter(user=user).values_list('room_id', flat=True)
        rows = ChatRoom.objects.filter(
            id__in=room_ids, app_id=user.app_id or 'spark_main',
        ).exclude(status=ChatRoom.STATUS_DISSOLVED).order_by('-last_at', '-id')
        return ApiResponse(data={'list': [_serialize_room(r, user) for r in rows]}, message='ok')

    @extend_schema(summary=_('创建群'))
    @action(detail=False, methods=['post'], url_path='rooms/create')
    def create_room(self, request):
        user = request.user
        name = (request.data.get('name') or '').strip()
        if not name:
            return ApiResponse(message='name required', code=400)
        avatar = request.data.get('avatar') or ''
        max_members = int(request.data.get('max_members') or 200)
        member_ids = request.data.get('member_ids') or []
        if not isinstance(member_ids, list):
            member_ids = []
        blocked = blocked_ids(user)
        room = ChatRoom.objects.create(
            app_id=user.app_id or 'spark_main',
            name=name[:128],
            owner=user,
            avatar=avatar[:512] if avatar else '',
            max_members=max(2, min(max_members, 500)),
        )
        ChatRoomMember.objects.create(room=room, user=user, role=ChatRoomMember.ROLE_OWNER)
        for uid in member_ids[:room.max_members - 1]:
            try:
                uid = int(uid)
            except (TypeError, ValueError):
                continue
            if uid == user.id or uid in blocked:
                continue
            peer = User.objects.filter(id=uid, app_id=user.app_id).first()
            if not peer:
                continue
            ChatRoomMember.objects.get_or_create(
                room=room, user=peer,
                defaults={'role': ChatRoomMember.ROLE_MEMBER},
            )
        return ApiResponse(data=_serialize_room(room, user), message='ok', code=201)

    @extend_schema(summary=_('群详情'))
    @action(detail=False, methods=['get'], url_path=r'rooms/(?P<rid>[^/.]+)')
    def room_detail(self, request, rid=None):
        user = request.user
        room = ChatRoom.objects.filter(id=rid, app_id=user.app_id or 'spark_main').first()
        if not room:
            return ApiResponse(message='not found', code=404)
        if not _member_of(room, user):
            return ApiResponse(code=403, message='not_member')
        members = [
            {
                'user_id': m.user_id,
                'role': m.role,
                'joined_at': m.joined_at.isoformat() if m.joined_at else None,
                'user': serialize_user_card(m.user),
            }
            for m in room.members.select_related('user').order_by('id')
        ]
        data = _serialize_room(room, user)
        data['members'] = members
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('邀请入群'))
    @action(detail=False, methods=['post'], url_path=r'rooms/(?P<rid>[^/.]+)/invite')
    def invite(self, request, rid=None):
        user = request.user
        room = ChatRoom.objects.filter(id=rid, app_id=user.app_id or 'spark_main').first()
        if not room or room.status == ChatRoom.STATUS_DISSOLVED:
            return ApiResponse(message='not found', code=404)
        me = _member_of(room, user)
        if not me or me.role not in (ChatRoomMember.ROLE_OWNER, ChatRoomMember.ROLE_ADMIN):
            return ApiResponse(code=403, message='forbidden')
        if room.members.count() >= room.max_members:
            return ApiResponse(code=400, message='room_full')
        blocked = blocked_ids(user)
        added = []
        for uid in (request.data.get('member_ids') or []):
            try:
                uid = int(uid)
            except (TypeError, ValueError):
                continue
            if uid in blocked or uid == user.id:
                continue
            if room.members.count() >= room.max_members:
                break
            peer = User.objects.filter(id=uid, app_id=user.app_id).first()
            if not peer:
                continue
            _, created = ChatRoomMember.objects.get_or_create(
                room=room, user=peer,
                defaults={'role': ChatRoomMember.ROLE_MEMBER},
            )
            if created:
                added.append(uid)
        return ApiResponse(data={'added': added}, message='ok')

    @extend_schema(summary=_('踢出成员'))
    @action(detail=False, methods=['post'], url_path=r'rooms/(?P<rid>[^/.]+)/kick')
    def kick(self, request, rid=None):
        user = request.user
        room = ChatRoom.objects.filter(id=rid, app_id=user.app_id or 'spark_main').first()
        if not room:
            return ApiResponse(message='not found', code=404)
        me = _member_of(room, user)
        if not me or me.role not in (ChatRoomMember.ROLE_OWNER, ChatRoomMember.ROLE_ADMIN):
            return ApiResponse(code=403, message='forbidden')
        try:
            target_id = int(request.data.get('user_id'))
        except (TypeError, ValueError):
            return ApiResponse(message='user_id required', code=400)
        if target_id == room.owner_id:
            return ApiResponse(code=400, message='cannot_kick_owner')
        deleted, _ = ChatRoomMember.objects.filter(room=room, user_id=target_id).delete()
        return ApiResponse(data={'kicked': bool(deleted)}, message='ok')

    @extend_schema(summary=_('退群'))
    @action(detail=False, methods=['post'], url_path=r'rooms/(?P<rid>[^/.]+)/leave')
    def leave(self, request, rid=None):
        user = request.user
        room = ChatRoom.objects.filter(id=rid, app_id=user.app_id or 'spark_main').first()
        if not room:
            return ApiResponse(message='not found', code=404)
        me = _member_of(room, user)
        if not me:
            return ApiResponse(code=403, message='not_member')
        if me.role == ChatRoomMember.ROLE_OWNER:
            room.status = ChatRoom.STATUS_DISSOLVED
            room.save(update_fields=['status'])
        ChatRoomMember.objects.filter(room=room, user=user).delete()
        return ApiResponse(message='ok')

    @extend_schema(summary=_('群消息历史'))
    @action(detail=False, methods=['get'], url_path=r'rooms/(?P<rid>[^/.]+)/messages')
    def messages(self, request, rid=None):
        user = request.user
        room = ChatRoom.objects.filter(id=rid, app_id=user.app_id or 'spark_main').first()
        if not room:
            return ApiResponse(message='not found', code=404)
        if not _member_of(room, user):
            return ApiResponse(code=403, message='not_member')
        qs = room.messages.select_related('sender').order_by('-id')
        before = request.query_params.get('before')
        if before:
            qs = qs.filter(id__lt=int(before))
        rows = list(qs[:50])
        rows.reverse()
        return ApiResponse(data={
            'list': [{
                'id': m.id,
                'room_id': room.id,
                'sender_id': m.sender_id,
                'sender': serialize_user_card(m.sender),
                'msg_type': m.msg_type,
                'content': m.content,
                'created_at': m.created_at.isoformat(),
            } for m in rows],
            'room': _serialize_room(room, user),
        }, message='ok')

    @extend_schema(summary=_('发送群消息'))
    @action(detail=False, methods=['post'], url_path=r'rooms/(?P<rid>[^/.]+)/send')
    def send(self, request, rid=None):
        user = request.user
        room = ChatRoom.objects.filter(id=rid, app_id=user.app_id or 'spark_main').first()
        if not room:
            return ApiResponse(message='not found', code=404)
        if room.status == ChatRoom.STATUS_DISSOLVED:
            return ApiResponse(code=400, message='room_dissolved')
        if room.status == ChatRoom.STATUS_MUTED:
            return ApiResponse(code=400, message='room_muted')
        if not _member_of(room, user):
            return ApiResponse(code=403, message='not_member')
        content = request.data.get('content') or ''
        msg_type = request.data.get('msg_type') or 'text'
        if not content:
            return ApiResponse(message='content required', code=400)
        if msg_type == 'text':
            banned = message_contains_banned(user.app_id, content, user.country or '*')
            if banned:
                return ApiResponse(code=400, message='content_blocked', data={'word': banned})
        msg = ChatRoomMessage.objects.create(
            room=room, sender=user, content=content, msg_type=msg_type,
        )
        preview = '[Photo]' if msg_type in ('image', 'photo') else content
        room.last_message = preview[:512]
        room.last_at = timezone.now()
        room.save(update_fields=['last_message', 'last_at'])
        payload = {
            'id': msg.id,
            'room_id': room.id,
            'sender_id': user.id,
            'msg_type': msg_type,
            'content': content,
            'created_at': msg.created_at.isoformat(),
        }
        _broadcast(room.id, payload)
        return ApiResponse(data=payload, message='ok', code=201)

    @extend_schema(summary=_('群媒体上传'))
    @action(
        detail=False, methods=['post'], url_path='upload',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload(self, request):
        user = request.user
        url = request.data.get('url')
        f = request.FILES.get('file')
        if f:
            name = f'group/{user.id}/{uuid.uuid4().hex}_{getattr(f, "name", "file")}'
            path = default_storage.save(name, ContentFile(f.read()))
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            url = request.build_absolute_uri(media_url + path) if hasattr(request, 'build_absolute_uri') else media_url + path
        if not url:
            return ApiResponse(message='url or file required', code=400)
        return ApiResponse(data={'url': url}, message='ok', code=201)
