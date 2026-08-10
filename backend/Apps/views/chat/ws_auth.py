"""WebSocket auth via Redis+AES business token (no django.contrib.auth).

Prefer Authorization header / Sec-WebSocket-Protocol; query `?token=` kept for uni-app.
Never log the raw token.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware


@database_sync_to_async
def _user_from_token(token):
    if not token:
        return None
    from tools.token_tools import CustomTokenTool
    from models.models import User
    ok, uid = CustomTokenTool.verify_token(token)
    if not ok or not uid:
        return None
    return User.objects.filter(id=uid, status=1).first()


def _token_from_scope(scope):
    """Prefer header / subprotocol; fall back to query string for uni-app."""
    headers = dict(scope.get('headers') or [])
    # Authorization: Bearer <token> or Token <token>
    raw = headers.get(b'authorization') or b''
    if isinstance(raw, (bytes, bytearray)):
        auth = raw.decode(errors='ignore').strip()
    else:
        auth = str(raw or '').strip()
    if auth:
        lower = auth.lower()
        if lower.startswith('bearer '):
            return auth[7:].strip()
        if lower.startswith('token '):
            return auth[6:].strip()
        return auth
    # Custom token header
    raw = headers.get(b'token') or b''
    if raw:
        return raw.decode(errors='ignore').strip() if isinstance(raw, (bytes, bytearray)) else str(raw).strip()
    # Sec-WebSocket-Protocol: bearer.<token> or raw token (first protocol)
    for proto in scope.get('subprotocols') or []:
        p = (proto or '').strip()
        if not p:
            continue
        lower = p.lower()
        if lower.startswith('bearer.'):
            return p[7:].strip()
        if lower.startswith('token.'):
            return p[6:].strip()
        if lower not in ('graphql-ws', 'graphql-transport-ws', 'mqtt'):
            return p
    # uni-app fallback: ?token=
    query = parse_qs((scope.get('query_string') or b'').decode(errors='ignore'))
    return (query.get('token') or [None])[0]


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)
        token = _token_from_scope(scope)
        scope['user'] = await _user_from_token(token)
        return await super().__call__(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(inner)
