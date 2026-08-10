"""
ASGI config for Spark — HTTP + WebSocket (chat).
Uses Redis+AES token auth for WS (not django.contrib.auth).
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uivsbe_backend.settings.dev')
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from Apps.views.chat.consumers import ChatConsumer
from Apps.views.chat.ws_auth import TokenAuthMiddlewareStack
from Apps.views.group.consumers import GroupChatConsumer
from Apps.views.match.consumers import MatchQAConsumer

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': TokenAuthMiddlewareStack(
        URLRouter([
            path('ws/chat/<int:conversation_id>/', ChatConsumer.as_asgi()),
            path('ws/group/<int:room_id>/', GroupChatConsumer.as_asgi()),
            path('ws/match/<int:match_id>/qa/', MatchQAConsumer.as_asgi()),
        ])
    ),
})
