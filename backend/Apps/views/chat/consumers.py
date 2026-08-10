import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user:
            await self.close(code=4401)
            return
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        if not await self._user_in_conversation(user.id, self.conversation_id):
            await self.close(code=4403)
            return
        self.user_id = user.id
        self.group_name = f'chat_{self.conversation_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # Mark messages delivered when peer connects
        await self._mark_delivered(user.id, self.conversation_id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        typ = data.get('type')
        if typ == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return
        if typ == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.event',
                    'data': {
                        'type': 'typing',
                        'user_id': self.user_id,
                        'conversation_id': int(self.conversation_id),
                        'is_typing': bool(data.get('is_typing', True)),
                    },
                },
            )
            return
        if typ == 'delivered':
            ids = data.get('message_ids') or []
            await self._mark_delivered_ids(ids)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.event',
                    'data': {
                        'type': 'delivered',
                        'user_id': self.user_id,
                        'message_ids': ids,
                        'conversation_id': int(self.conversation_id),
                    },
                },
            )
            return
        if typ == 'read':
            ids = data.get('message_ids') or []
            await self._mark_read_ids(self.user_id, self.conversation_id, ids)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.event',
                    'data': {
                        'type': 'read',
                        'user_id': self.user_id,
                        'message_ids': ids,
                        'conversation_id': int(self.conversation_id),
                    },
                },
            )
            return

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({'type': 'message', 'data': event.get('data')}))

    async def chat_event(self, event):
        await self.send(text_data=json.dumps(event.get('data') or {}))

    @database_sync_to_async
    def _user_in_conversation(self, user_id, conversation_id):
        from models.models import Conversation, User
        from tools.spark_helpers import blocked_ids
        conv = Conversation.objects.filter(
            Q(user_a_id=user_id) | Q(user_b_id=user_id),
            id=conversation_id,
        ).first()
        if not conv:
            return False
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return False
        other_id = conv.user_b_id if conv.user_a_id == user_id else conv.user_a_id
        if other_id in blocked_ids(user):
            return False
        return True

    @database_sync_to_async
    def _mark_delivered(self, user_id, conversation_id):
        from models.models import Message
        Message.objects.filter(
            conversation_id=conversation_id,
            delivered_at__isnull=True,
        ).exclude(sender_id=user_id).update(delivered_at=timezone.now())

    @database_sync_to_async
    def _mark_delivered_ids(self, ids):
        from models.models import Message
        if not ids:
            return
        # S-14 / BE-028: only mark messages in this conversation, not sent by self
        Message.objects.filter(
            id__in=ids,
            conversation_id=self.conversation_id,
            delivered_at__isnull=True,
        ).exclude(sender_id=self.user_id).update(delivered_at=timezone.now())

    @database_sync_to_async
    def _mark_read_ids(self, user_id, conversation_id, ids):
        from models.models import Conversation, Message
        now = timezone.now()
        qs = Message.objects.filter(conversation_id=conversation_id).exclude(sender_id=user_id)
        if ids:
            qs = qs.filter(id__in=ids)
        qs.update(is_read=True, read_at=now)
        conv = Conversation.objects.filter(id=conversation_id).only(
            'id', 'user_a_id', 'user_b_id',
        ).first()
        if not conv:
            return
        # Opening/read receipt clears this reader's badge counter.
        if conv.user_a_id == user_id:
            Conversation.objects.filter(id=conversation_id).update(unread_count_a=0)
        elif conv.user_b_id == user_id:
            Conversation.objects.filter(id=conversation_id).update(unread_count_b=0)
