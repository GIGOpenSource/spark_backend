import logging

from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.translate_service import translate_text, normalize_lang

logger = logging.getLogger(__name__)


@extend_schema(tags=[_('翻译')])
class TranslateViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('翻译文本（Google Cloud Translation v2）'))
    @action(detail=False, methods=['post'], url_path='text')
    def text(self, request):
        """
        Body: text, target?, source?, message_id?
        Uses admin「三方配置 → Google Translate」API Key (fallback .env).
        When message_id is provided and caller can access the message, persists translated.
        """
        text = request.data.get('text') or ''
        target = request.data.get('target') or getattr(request.user, 'locale', None) or 'en'
        source = request.data.get('source') or 'auto'
        message_id = request.data.get('message_id')

        if not text and message_id:
            from models.models import Message
            try:
                msg = Message.objects.select_related('conversation').get(id=int(message_id))
                text = msg.content or ''
            except (Message.DoesNotExist, TypeError, ValueError):
                return ApiResponse(message='message not found', code=404)

        if not text:
            return ApiResponse(message='text required', code=400)

        result = translate_text(text, target=target, source=source, allow_mock=False)
        if result.get('error') == 'not_configured':
            return ApiResponse(code=503, message='translate_not_configured', data=result)
        if result.get('error') and not result.get('translated'):
            return ApiResponse(code=502, message=result.get('error') or 'translate_failed', data=result)
        if result.get('error') and not result.get('translated'):
            return ApiResponse(
                code=502,
                message=result.get('error') or 'translate failed',
                data={
                    'target': result.get('target'),
                    'source': result.get('source'),
                    'mock': result.get('mock', False),
                    'provider': result.get('provider'),
                },
            )

        # Persist on message when possible
        saved = False
        if message_id and result.get('translated') and not result.get('mock'):
            saved = self._persist_translation(request.user, message_id, result['translated'])

        return ApiResponse(data={
            'translated': result.get('translated') or '',
            'target': result.get('target') or normalize_lang(target),
            'source': result.get('source') or source,
            'detected_source': result.get('detected_source'),
            'mock': bool(result.get('mock')),
            'provider': result.get('provider') or 'none',
            'message_id': int(message_id) if message_id else None,
            'saved': saved,
        }, message='ok')

    def _persist_translation(self, user, message_id, translated: str) -> bool:
        from models.models import Message
        try:
            mid = int(message_id)
        except (TypeError, ValueError):
            return False
        msg = (
            Message.objects.select_related('conversation')
            .filter(id=mid)
            .first()
        )
        if not msg:
            return False
        conv = msg.conversation
        uid = getattr(user, 'id', None)
        if uid not in (conv.user_a_id, conv.user_b_id):
            return False
        msg.translated = translated[:8000]
        msg.save(update_fields=['translated'])
        return True
