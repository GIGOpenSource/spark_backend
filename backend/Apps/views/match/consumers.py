import json
import logging

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.db.models import Q

logger = logging.getLogger(__name__)


class MatchQAConsumer(AsyncWebsocketConsumer):
    """Realtime QA gate updates for 她说 matches."""

    async def connect(self):
        user = self.scope.get('user')
        if not user:
            await self.close(code=4401)
            return
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        if not await self._user_in_match(user.id, self.match_id):
            await self.close(code=4403)
            return
        self.user_id = user.id
        self.group_name = f'match_qa_{self.match_id}'
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

    async def qa_update(self, event):
        # Per-viewer payload: same group, correct can_* / i_am_* for each party
        by_user = event.get('by_user') or {}
        data = by_user.get(str(getattr(self, 'user_id', ''))) or event.get('data')
        if not data:
            return
        await self.send(text_data=json.dumps({'type': 'qa', 'data': data}))

    @database_sync_to_async
    def _user_in_match(self, user_id, match_id):
        from models.models import Match
        return Match.objects.filter(
            Q(user_a_id=user_id) | Q(user_b_id=user_id),
            id=match_id,
        ).exists()


def broadcast_match_qa(match, viewer=None):
    """Push per-viewer serialize_match_messaging to both parties on the match QA channel."""
    try:
        from tools.spark_helpers import serialize_match_messaging
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        user_a = match.user_a
        user_b = match.user_b
        by_user = {
            str(user_a.id): serialize_match_messaging(match, user_a),
            str(user_b.id): serialize_match_messaging(match, user_b),
        }
        async_to_sync(channel_layer.group_send)(
            f'match_qa_{match.id}',
            {'type': 'qa_update', 'by_user': by_user},
        )
    except Exception:
        logger.exception('broadcast_match_qa failed')
