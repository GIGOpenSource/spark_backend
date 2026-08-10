from django.db.models import F, Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.spark_helpers import (
    serialize_user_card, has_vip_at_least, get_discover_param,
    message_contains_banned, blocked_ids, match_is_live, clear_match_expire_if_opened,
    can_user_open_chat, serialize_match_messaging,
)
from tools.push_service import notify_safe, EVENT_NEW_MESSAGE, touch_user_activity
from models.models import Conversation, Message, Match, SayHi, QmPair
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid

VOICE_MSG_TYPES = ('voice', 'audio')
IMAGE_MSG_TYPES = ('image', 'photo', 'gif')
ALLOWED_MSG_TYPES = ('text',) + IMAGE_MSG_TYPES + VOICE_MSG_TYPES


def _normalize_msg_type(raw):
    t = (raw or 'text').strip().lower()
    if t == 'audio':
        return 'voice'
    return t


def _preview_for_type(msg_type, content=''):
    if msg_type == 'gif':
        return '[GIF]'
    if msg_type in IMAGE_MSG_TYPES:
        return '[Photo]'
    if msg_type in VOICE_MSG_TYPES or msg_type == 'voice':
        return '[Voice]'
    return content or ''


def _serialize_message(row):
    return {
        'id': row.id,
        'sender_id': row.sender_id,
        'msg_type': row.msg_type,
        'content': row.content,
        'duration_ms': getattr(row, 'duration_ms', 0) or 0,
        'translated': row.translated,
        'is_read': row.is_read,
        'delivered_at': row.delivered_at.isoformat() if getattr(row, 'delivered_at', None) else None,
        'read_at': row.read_at.isoformat() if getattr(row, 'read_at', None) else None,
        'created_at': row.created_at.isoformat(),
    }


# Common mobile recorder formats
VOICE_EXT_ALLOW = {
    '.m4a', '.aac', '.mp3', '.wav', '.amr', '.ogg', '.webm', '.caf', '.3gp',
}
VOICE_CONTENT_TYPES = {
    'audio/mp4', 'audio/m4a', 'audio/aac', 'audio/mpeg', 'audio/mp3',
    'audio/wav', 'audio/x-wav', 'audio/amr', 'audio/ogg', 'audio/webm',
    'audio/x-caf', 'audio/3gpp',
}
# Reject application/octet-stream for voice (S-15 / BE-029)

IMAGE_EXT_ALLOW = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}
IMAGE_CONTENT_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/heic', 'image/heif',
}


def _parse_duration_ms(raw):
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 0
    # Cap at 10 minutes
    return max(0, min(n, 10 * 60 * 1000))


def _url_host_allowed(url: str) -> bool:
    """Whitelist remote media hosts (own media / CDN / DomainWhitelist). Reject SSRF."""
    from urllib.parse import urlparse
    if not url:
        return False
    if url.startswith('/'):
        return True
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ('http', 'https'):
        return False
    host = (parsed.hostname or '').lower()
    if not host:
        return False
    # Block obvious SSRF targets
    if host in ('localhost', '127.0.0.1', '0.0.0.0', '::1') or host.startswith('169.254.'):
        return False
    if host.startswith('10.') or host.startswith('192.168.') or host.startswith('172.'):
        # allow only if explicitly whitelisted below
        pass
    allowed = set()
    try:
        media_url = getattr(settings, 'MEDIA_URL', '') or ''
        if media_url.startswith('http'):
            allowed.add(urlparse(media_url).hostname or '')
    except Exception:
        pass
    # COS / CDN from env-style buckets often appear in absolute URLs
    for extra in (
        getattr(settings, 'ALLOWED_MEDIA_HOSTS', None) or [],
    ):
        if extra:
            allowed.add(str(extra).lower())
    try:
        from models.models import DomainWhitelist
        for d in DomainWhitelist.objects.values_list('domain', flat=True)[:500]:
            if d:
                allowed.add(str(d).lower().lstrip('.'))
    except Exception:
        pass
    # Always allow same-host relative builds and common COS suffix when bucket configured
    if host in allowed:
        return True
    for d in allowed:
        if d and (host == d or host.endswith('.' + d)):
            return True
    # Local/dev media path served by this API
    if 'cos.' in host and host.endswith('.myqcloud.com'):
        return True
    return False


@extend_schema(tags=[_('聊天')])
class ChatViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    def _other(self, conv, user):
        return conv.user_b if conv.user_a_id == user.id else conv.user_a

    def _is_blocked_peer(self, user, conv, blocked=None):
        other_id = conv.user_b_id if conv.user_a_id == user.id else conv.user_a_id
        ids = blocked if blocked is not None else blocked_ids(user)
        return other_id in ids

    def _is_quick_match(self, conv):
        return getattr(conv, 'origin', Conversation.ORIGIN_DATING) == Conversation.ORIGIN_QUICK_MATCH

    def _qm_pair_active(self, conv):
        """True if quick-match conversation still has an active pair (or no pair row yet)."""
        pair = getattr(conv, 'qm_pair', None)
        if pair is None:
            pair = QmPair.objects.filter(conversation=conv).first()
        if not pair:
            return True
        return pair.status == QmPair.STATUS_ACTIVE

    def _say_hi_meta(self, conv, user):
        """Return pre-match Say Hi context for blur / reply limits."""
        # Dating match OR quick-match free chat: never apply Say Hi limits.
        if conv.match_id or self._is_quick_match(conv):
            return {
                'is_prematch': False,
                'blur_peer': False,
                'free_replies_left': None,
                'i_am_receiver': False,
                'say_hi_expired': False,
            }
        other = self._other(conv, user)
        now = timezone.now()
        sh = SayHi.objects.filter(
            Q(sender=user, receiver=other) | Q(sender=other, receiver=user),
            status='pending',
        ).order_by('-id').first()
        if sh and sh.expire_at and sh.expire_at < now:
            sh.status = 'expired'
            sh.save(update_fields=['status'])
            sh = None
        say_hi_expired = False
        if not sh:
            last = SayHi.objects.filter(
                Q(sender=user, receiver=other) | Q(sender=other, receiver=user),
            ).order_by('-id').first()
            if last and (last.status == 'expired' or (last.expire_at and last.expire_at < now)):
                if last.status != 'expired':
                    last.status = 'expired'
                    last.save(update_fields=['status'])
                say_hi_expired = True
                sh = last
            elif last:
                sh = last
        i_am_receiver = bool(sh and sh.receiver_id == user.id)
        platinum = has_vip_at_least(user, 'platinum')
        blur_peer = i_am_receiver and not platinum and not say_hi_expired
        free_left = None
        if i_am_receiver and not platinum:
            if say_hi_expired:
                free_left = 0
            else:
                param = get_discover_param(user.app_id, user.country or '*')
                used = Message.objects.filter(conversation=conv, sender=user).count()
                free_left = max(0, (param.free_say_hi_replies or 2) - used)
        return {
            'is_prematch': True,
            'blur_peer': blur_peer,
            'free_replies_left': free_left,
            'i_am_receiver': i_am_receiver,
            'say_hi_id': sh.id if sh else None,
            'say_hi_expired': say_hi_expired,
        }

    def _peer_payload(self, conv, user, meta):
        other = self._other(conv, user)
        if meta.get('blur_peer'):
            card = serialize_user_card(other, blur=True)
            nick = (other.nickname or 'Someone')[:1]
            card['nickname'] = f'{nick}***'
            card['masked'] = True
            return card
        return serialize_user_card(other)

    @extend_schema(summary=_('会话列表'))
    @action(detail=False, methods=['get'], url_path='conversations')
    def conversations(self, request):
        from django.db.models import OuterRef, Subquery

        user = request.user
        blocked = blocked_ids(user)
        try:
            limit = min(max(int(request.query_params.get('limit', 20)), 1), 100)
        except (TypeError, ValueError):
            limit = 20
        try:
            offset = max(int(request.query_params.get('offset', 0)), 0)
        except (TypeError, ValueError):
            offset = 0

        last_sender_sub = (
            Message.objects.filter(conversation_id=OuterRef('pk'))
            .order_by('-id')
            .values('sender_id')[:1]
        )
        # Over-fetch then filter (blocked / dead match / app) before paging
        fetch_cap = min(offset + limit + 40, 500)
        rows = list(
            Conversation.objects.filter(Q(user_a=user) | Q(user_b=user))
            .select_related('user_a', 'user_b', 'match')
            .prefetch_related('user_a__photos', 'user_b__photos', 'qm_pair')
            .annotate(last_sender_id=Subquery(last_sender_sub))
            .order_by('-last_at', '-id')[:fetch_cap]
        )

        match_ids = [c.match_id for c in rows if c.match_id]
        matches = {
            m.id: m for m in Match.objects.filter(id__in=match_ids)
        } if match_ids else {}

        items = []
        for c in rows:
            if self._is_blocked_peer(user, c, blocked):
                continue
            messaging = {}
            if c.match_id:
                live = matches.get(c.match_id) or getattr(c, 'match', None)
                # Read-only live check (no match_is_live expire writes)
                if not live or live.status != 'active':
                    continue
                if live.expire_at and live.expire_at <= timezone.now():
                    continue
                messaging = serialize_match_messaging(live, user) or {}
            meta = self._say_hi_meta(c, user)
            if not c.match_id and not self._is_quick_match(c) and meta.get('say_hi_expired'):
                continue
            if self._is_quick_match(c) and not self._qm_pair_active(c):
                continue
            peer = self._peer_payload(c, user, meta)
            # 三端不互通：会话对端必须同 app
            peer_app = None
            try:
                other = self._other(c, user)
                peer_app = getattr(other, 'app_id', None)
            except Exception:
                peer_app = None
            if peer_app and user.app_id and peer_app != user.app_id:
                continue
            unread = c.unread_for(user)
            preview = c.last_message or ''
            if preview in ('[image]', '[photo]', '[图片]', '[照片]'):
                preview = '[Photo]'
            if preview in ('[voice]', '[audio]', '[语音]', '[Voice]'):
                preview = '[Voice]'
            if messaging.get('waiting_for_opener') and not preview:
                preview = 'Waiting for her to move first…'
            last_sender_id = getattr(c, 'last_sender_id', None)
            your_turn = False
            if last_sender_id and last_sender_id != user.id:
                your_turn = True
            elif not preview and messaging.get('i_am_opener') and not messaging.get('waiting_for_opener'):
                your_turn = True
            items.append({
                'id': c.id,
                'match_id': c.match_id,
                'origin': getattr(c, 'origin', Conversation.ORIGIN_DATING) or Conversation.ORIGIN_DATING,
                'user': peer,
                'last_message': preview,
                'last_at': c.last_at.isoformat() if c.last_at else None,
                'unread': unread,
                'your_turn': your_turn,
                'is_prematch': meta['is_prematch'],
                'blur_peer': meta['blur_peer'],
                'say_hi_expired': meta.get('say_hi_expired', False),
                'expire_at': messaging.get('expire_at'),
                **messaging,
            })
            if len(items) >= offset + limit:
                break
        page = items[offset:offset + limit]
        return ApiResponse(data={'list': page}, message='ok')

    @extend_schema(summary=_('消息历史'))
    @action(detail=False, methods=['get'], url_path=r'conversations/(?P<cid>[^/.]+)/messages')
    def messages(self, request, cid=None):
        user = request.user
        conv = Conversation.objects.filter(id=cid).filter(Q(user_a=user) | Q(user_b=user)).first()
        if not conv:
            return ApiResponse(message='not found', code=404)
        if self._is_blocked_peer(user, conv):
            return ApiResponse(code=403, message='blocked')
        match_status = 'active'
        match_expire_at = None
        messaging = {}
        if conv.match_id:
            m = Match.objects.filter(id=conv.match_id).first()
            messaging = serialize_match_messaging(m, user)
            if not m or m.status not in ('active',):
                match_status = 'ended' if (not m or m.status == 'ended') else (m.status if m else 'ended')
            elif match_is_live(m):
                match_expire_at = m.expire_at.isoformat() if m.expire_at else None
                match_status = 'active'
            else:
                match_status = 'expired'
        elif self._is_quick_match(conv):
            match_status = 'active' if self._qm_pair_active(conv) else 'ended'
        qs = conv.messages.order_by('-id')
        before = (
            request.query_params.get('before_id')
            or request.query_params.get('before')
        )
        if before:
            qs = qs.filter(id__lt=int(before))
        limit = min(int(request.query_params.get('limit') or 50), 100)
        # Latest N messages, returned chronological for the client
        rows = list(reversed(list(qs[:limit])))
        now = timezone.now()
        unread_qs = conv.messages.filter(is_read=False).exclude(sender=user)
        unread_qs.update(is_read=True, read_at=now)
        # Mark peer's messages as delivered when we fetch
        conv.messages.filter(delivered_at__isnull=True).exclude(sender=user).update(delivered_at=now)
        clear_fields = (
            {'unread_count_a': 0} if conv.user_a_id == user.id else {'unread_count_b': 0}
        )
        Conversation.objects.filter(id=conv.id).update(**clear_fields)
        meta = self._say_hi_meta(conv, user)
        if not conv.match_id and not self._is_quick_match(conv) and meta.get('say_hi_expired'):
            match_status = 'expired'
        return ApiResponse(data={
            'list': [_serialize_message(row) for row in rows],
            'peer': self._peer_payload(conv, user, meta),
            'match_id': conv.match_id,
            'origin': getattr(conv, 'origin', Conversation.ORIGIN_DATING) or Conversation.ORIGIN_DATING,
            'conversation_id': conv.id,
            'match_status': match_status,
            'match_expire_at': match_expire_at,
            'is_prematch': meta['is_prematch'],
            'blur_peer': meta['blur_peer'],
            'free_replies_left': meta['free_replies_left'],
            'i_am_receiver': meta['i_am_receiver'],
            'say_hi_expired': meta.get('say_hi_expired', False),
            **messaging,
        }, message='ok')

    @extend_schema(summary=_('发送消息'))
    @action(detail=False, methods=['post'], url_path=r'conversations/(?P<cid>[^/.]+)/send')
    def send(self, request, cid=None):
        user = request.user
        conv = Conversation.objects.filter(id=cid).filter(Q(user_a=user) | Q(user_b=user)).first()
        if not conv:
            return ApiResponse(message='not found', code=404)
        if self._is_blocked_peer(user, conv):
            return ApiResponse(code=403, message='blocked')
        # Quick-match free chat: skip Match / Say Hi gates; still block + word filter.
        is_qm = self._is_quick_match(conv)
        if is_qm and not self._qm_pair_active(conv):
            return ApiResponse(code=400, message='quick_match_ended')
        live_match = None
        if not is_qm and conv.match_id:
            live_match = Match.objects.filter(id=conv.match_id).first()
            if not live_match or live_match.status == 'ended':
                return ApiResponse(code=400, message='match_ended')
            if live_match.status != 'active' or (
                live_match.expire_at and live_match.expire_at < timezone.now()
                and not (conv.last_message or conv.messages.exists())
            ):
                return ApiResponse(code=400, message='match_expired')
        content = request.data.get('content') or ''
        msg_type = _normalize_msg_type(request.data.get('msg_type') or 'text')
        if msg_type not in ALLOWED_MSG_TYPES:
            return ApiResponse(message='unsupported msg_type', code=400, data={
                'allowed': list(ALLOWED_MSG_TYPES),
            })
        if not content:
            return ApiResponse(message='content required', code=400)

        duration_ms = 0
        if msg_type in VOICE_MSG_TYPES or msg_type == 'voice':
            msg_type = 'voice'
            duration_ms = _parse_duration_ms(
                request.data.get('duration_ms') or request.data.get('duration') or 0
            )
            # content must be an uploaded audio URL
            if not (str(content).startswith('http://') or str(content).startswith('https://')
                    or str(content).startswith('/')):
                return ApiResponse(message='voice url required', code=400)

        if msg_type == 'text':
            banned = message_contains_banned(user.app_id, content, user.country or '*', user=user)
            if banned:
                return ApiResponse(code=400, message='content_blocked', data={'word': banned})

        if not is_qm:
            meta = self._say_hi_meta(conv, user)
            if meta['is_prematch'] and meta.get('say_hi_expired'):
                return ApiResponse(code=400, message='say_hi_expired')
            if meta['is_prematch'] and meta['i_am_receiver'] and not has_vip_at_least(user, 'platinum'):
                if meta['free_replies_left'] is not None and meta['free_replies_left'] <= 0:
                    return ApiResponse(
                        code=403, message='need_platinum',
                        data={'need_vip': True, 'reason': 'say_hi_reply_limit'},
                    )

            if live_match:
                ok, err = can_user_open_chat(live_match, user)
                if not ok:
                    return ApiResponse(
                        code=403,
                        message=err or 'waiting_for_opener',
                        data=serialize_match_messaging(live_match, user),
                    )

        msg = Message.objects.create(
            conversation=conv, sender=user, content=content, msg_type=msg_type,
            duration_ms=duration_ms,
        )
        conv.last_message = _preview_for_type(msg_type, content)[:512]
        conv.last_at = timezone.now()
        # Peer unread counter (user_a / user_b)
        if conv.user_a_id == user.id:
            Conversation.objects.filter(id=conv.id).update(
                last_message=conv.last_message,
                last_at=conv.last_at,
                unread_count_b=F('unread_count_b') + 1,
            )
        else:
            Conversation.objects.filter(id=conv.id).update(
                last_message=conv.last_message,
                last_at=conv.last_at,
                unread_count_a=F('unread_count_a') + 1,
            )
        # PRD: 已匹配已开聊 → 不过期 (+ stamp opened_at for women_first)
        if live_match:
            clear_match_expire_if_opened(live_match)
        payload = _serialize_message(msg)
        payload['conversation_id'] = conv.id
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{conv.id}',
                    {'type': 'chat.message', 'data': payload},
                )
        except Exception:
            pass
        peer = self._other(conv, user)
        touch_user_activity(user)
        if peer and not getattr(peer, 'is_online', False):
            preview = _preview_for_type(msg_type, content)
            if msg_type == 'text' and len(preview) > 80:
                preview = preview[:77] + '...'
            notify_safe(peer, EVENT_NEW_MESSAGE, {
                'nickname': user.nickname or user.username or '',
                'preview': preview,
                'conversation_id': conv.id,
                'from_user_id': user.id,
            })
        return ApiResponse(data=payload, message='ok', code=201)

    @extend_schema(summary=_('GIF 搜索 (Tenor)'))
    @action(detail=False, methods=['get'], url_path='gifs/search')
    def gifs_search(self, request):
        from tools.tenor_service import search_gifs
        q = request.query_params.get('q') or ''
        limit = request.query_params.get('limit') or 20
        result = search_gifs(q, limit=limit)
        if not result.get('ok'):
            code = 503 if result.get('error') == 'tenor_not_configured' else 400
            return ApiResponse(code=code, message=result.get('error') or 'gif_search_failed', data=result)
        return ApiResponse(data={'list': result.get('list') or []}, message='ok')

    @extend_schema(summary=_('视频通话 RTC Token'))
    @action(detail=False, methods=['post'], url_path='call/token')
    def call_token(self, request):
        from tools.agora_service import build_rtc_token
        cid = request.data.get('conversation_id') or request.data.get('cid')
        user = request.user
        conv = Conversation.objects.filter(id=cid).filter(Q(user_a=user) | Q(user_b=user)).first()
        if not conv:
            return ApiResponse(message='not found', code=404)
        if self._is_blocked_peer(user, conv):
            return ApiResponse(code=403, message='blocked')
        channel = f'conv_{conv.id}'
        result = build_rtc_token(channel, user.id, role='publisher')
        if not result.get('ok'):
            code = 503 if result.get('error') == 'agora_not_configured' else 400
            return ApiResponse(code=code, message=result.get('error') or 'call_token_failed', data=result)
        # Notify peer via WS
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{conv.id}',
                    {
                        'type': 'chat.event',
                        'data': {
                            'type': 'call_invite',
                            'conversation_id': conv.id,
                            'from_user_id': user.id,
                            'channel': channel,
                        },
                    },
                )
        except Exception:
            pass
        return ApiResponse(data=result, message='ok')

    @extend_schema(summary=_('挂断视频通话'))
    @action(detail=False, methods=['post'], url_path='call/hangup')
    def call_hangup(self, request):
        cid = request.data.get('conversation_id') or request.data.get('cid')
        user = request.user
        conv = Conversation.objects.filter(id=cid).filter(Q(user_a=user) | Q(user_b=user)).first()
        if not conv:
            return ApiResponse(message='not found', code=404)
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'chat_{conv.id}',
                    {
                        'type': 'chat.event',
                        'data': {
                            'type': 'call_hangup',
                            'conversation_id': conv.id,
                            'from_user_id': user.id,
                        },
                    },
                )
        except Exception:
            pass
        return ApiResponse(message='ok')

    @extend_schema(summary=_('聊天媒体上传（图片/语音，不入相册）'))
    @action(
        detail=False, methods=['post'], url_path='upload',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload(self, request):
        """Chat media only — never creates UserPhoto / audit queue.

        Query/body `kind`: image (default) | voice
        Voice also accepts duration_ms (echoed back for client convenience).
        """
        user = request.user
        kind = (request.data.get('kind') or request.query_params.get('kind') or 'image').strip().lower()
        if kind in ('audio', 'voice'):
            kind = 'voice'
        url = request.data.get('url')
        f = request.FILES.get('file')
        if f:
            raw_name = getattr(f, 'name', '') or ('voice.m4a' if kind == 'voice' else 'img.jpg')
            ext = os.path.splitext(raw_name)[1].lower() or ('.m4a' if kind == 'voice' else '.jpg')
            content_type = (getattr(f, 'content_type', None) or '').lower()
            if kind == 'voice':
                # Require real audio MIME or known extension; reject octet-stream (S-15)
                mime_ok = content_type in VOICE_CONTENT_TYPES
                ext_ok = ext in VOICE_EXT_ALLOW
                if content_type == 'application/octet-stream' or not (mime_ok or ext_ok):
                    return ApiResponse(
                        code=400, message='unsupported_audio',
                        data={'ext': ext, 'content_type': content_type},
                    )
                # Soft size cap ~10MB
                size = getattr(f, 'size', None)
                if size is not None and size > 10 * 1024 * 1024:
                    return ApiResponse(code=400, message='file_too_large')
                folder = f'chat/voice/{user.id}'
            else:
                mime_ok = content_type in IMAGE_CONTENT_TYPES or content_type.startswith('image/')
                ext_ok = ext in IMAGE_EXT_ALLOW
                if not mime_ok and not ext_ok:
                    return ApiResponse(
                        code=400, message='unsupported_image',
                        data={'ext': ext, 'content_type': content_type},
                    )
                folder = f'chat/{user.id}'
            name = f'{folder}/{uuid.uuid4().hex}_{raw_name}'
            path = default_storage.save(name, ContentFile(f.read()))
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            url = request.build_absolute_uri(media_url + path) if hasattr(request, 'build_absolute_uri') else media_url + path
        if not url:
            return ApiResponse(message='url or file required', code=400)
        # Remote URL must be on whitelist (no arbitrary fetch / SSRF vector)
        if not f and not _url_host_allowed(str(url)):
            return ApiResponse(code=400, message='url_host_not_allowed')
        data = {'url': url, 'kind': kind}
        if kind == 'voice':
            data['duration_ms'] = _parse_duration_ms(
                request.data.get('duration_ms') or request.data.get('duration') or 0
            )
            data['msg_type'] = 'voice'
        else:
            data['msg_type'] = 'image'
        return ApiResponse(data=data, message='ok', code=201)
