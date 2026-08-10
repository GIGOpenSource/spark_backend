import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user:
            await self.close(code=4401)
            return
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        if not await self._user_in_room(user.id, self.room_id):
            await self.close(code=4403)
            return
        self.user_id = user.id
        self.group_name = f'group_{self.room_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                return
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))

    async def group_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'data': event.get('data')}))

    @database_sync_to_async
    def _user_in_room(self, user_id, room_id):
        from models.models import ChatRoom, ChatRoomMember
        room = ChatRoom.objects.filter(id=room_id).exclude(status=ChatRoom.STATUS_DISSOLVED).first()
        if not room:
            return False
        return ChatRoomMember.objects.filter(room=room, user_id=user_id).exists()
