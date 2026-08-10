from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.social_content import (
    serialize_post, serialize_comment, create_post_with_media,
    visible_posts_qs, toggle_like, add_comment,
)
from models.models import Topic, Post, PostLike


def _serialize_topic(t):
    return {
        'id': t.id,
        'app_id': t.app_id,
        'title': t.title,
        'cover': t.cover or '',
        'sort': t.sort,
        'is_active': t.is_active,
        'created_at': t.created_at.isoformat() if t.created_at else None,
    }


@extend_schema(tags=[_('社区')])
class CommunityViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('话题列表'))
    @action(detail=False, methods=['get'], url_path='topics')
    def topics(self, request):
        user = request.user
        rows = Topic.objects.filter(
            app_id=user.app_id or 'spark_main', is_active=True,
        ).order_by('sort', 'id')
        return ApiResponse(data={'list': [_serialize_topic(t) for t in rows]}, message='ok')

    @extend_schema(summary=_('社区帖子流'))
    @action(detail=False, methods=['get'], url_path='posts')
    def posts(self, request):
        user = request.user
        topic_id = request.query_params.get('topic_id')
        before = request.query_params.get('before')
        qs = visible_posts_qs(user.app_id or 'spark_main', Post.TYPE_COMMUNITY, viewer=user)
        if topic_id:
            qs = qs.filter(topic_id=topic_id)
        if before:
            qs = qs.filter(id__lt=int(before))
        rows = list(qs[:30])
        liked_ids = set(
            PostLike.objects.filter(user=user, post_id__in=[p.id for p in rows]).values_list('post_id', flat=True)
        ) if rows else set()
        return ApiResponse(data={
            'list': [serialize_post(p, liked_ids=liked_ids) for p in rows],
        }, message='ok')

    @extend_schema(summary=_('发社区帖'))
    @action(detail=False, methods=['post'], url_path='posts/create')
    def create_post(self, request):
        user = request.user
        text = request.data.get('text') or ''
        topic_id = request.data.get('topic_id')
        media_list = request.data.get('media') or []
        if not isinstance(media_list, list):
            media_list = []
        topic = None
        if topic_id:
            topic = Topic.objects.filter(
                id=topic_id, app_id=user.app_id or 'spark_main', is_active=True,
            ).first()
            if not topic:
                return ApiResponse(message='topic not found', code=404)
        post, err, data = create_post_with_media(
            user, post_type=Post.TYPE_COMMUNITY, text=text, topic=topic, media_list=media_list,
        )
        if err:
            return ApiResponse(code=400, message=err, data=data)
        return ApiResponse(data=serialize_post(post, viewer=user), message='ok', code=201)

    @extend_schema(summary=_('帖子详情'))
    @action(detail=False, methods=['get'], url_path=r'posts/(?P<pid>[^/.]+)')
    def post_detail(self, request, pid=None):
        user = request.user
        post = Post.objects.filter(
            id=pid, app_id=user.app_id or 'spark_main', status=Post.STATUS_VISIBLE,
        ).select_related('author', 'topic').prefetch_related('media').first()
        if not post:
            return ApiResponse(message='not found', code=404)
        return ApiResponse(data=serialize_post(post, viewer=user), message='ok')

    @extend_schema(summary=_('评论列表'))
    @action(detail=False, methods=['get'], url_path=r'posts/(?P<pid>[^/.]+)/comments')
    def comments(self, request, pid=None):
        user = request.user
        post = Post.objects.filter(
            id=pid, app_id=user.app_id or 'spark_main', status=Post.STATUS_VISIBLE,
        ).first()
        if not post:
            return ApiResponse(message='not found', code=404)
        qs = post.comments.filter(status='visible').select_related('author').order_by('id')
        before = request.query_params.get('before')
        if before:
            qs = qs.filter(id__lt=int(before))
        rows = list(qs[:50])
        return ApiResponse(data={'list': [serialize_comment(c) for c in rows]}, message='ok')

    @extend_schema(summary=_('发表评论'))
    @action(detail=False, methods=['post'], url_path=r'posts/(?P<pid>[^/.]+)/comments')
    def comment(self, request, pid=None):
        user = request.user
        post = Post.objects.filter(
            id=pid, app_id=user.app_id or 'spark_main', status=Post.STATUS_VISIBLE,
        ).first()
        if not post:
            return ApiResponse(message='not found', code=404)
        c, err = add_comment(post, user, request.data.get('text'))
        if err:
            return ApiResponse(code=400, message=err)
        return ApiResponse(data=serialize_comment(c), message='ok', code=201)

    @extend_schema(summary=_('点赞/取消'))
    @action(detail=False, methods=['post'], url_path=r'posts/(?P<pid>[^/.]+)/like')
    def like(self, request, pid=None):
        user = request.user
        post = Post.objects.filter(
            id=pid, app_id=user.app_id or 'spark_main', status=Post.STATUS_VISIBLE,
        ).first()
        if not post:
            return ApiResponse(message='not found', code=404)
        liked, count = toggle_like(post, user)
        return ApiResponse(data={'liked': liked, 'like_count': count}, message='ok')

    @extend_schema(summary=_('内容媒体上传'))
    @action(
        detail=False, methods=['post'], url_path='upload',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload(self, request):
        user = request.user
        url = request.data.get('url')
        f = request.FILES.get('file')
        if f:
            name = f'community/{user.id}/{uuid.uuid4().hex}_{getattr(f, "name", "file")}'
            path = default_storage.save(name, ContentFile(f.read()))
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            url = request.build_absolute_uri(media_url + path) if hasattr(request, 'build_absolute_uri') else media_url + path
        if not url:
            return ApiResponse(message='url or file required', code=400)
        return ApiResponse(data={'url': url}, message='ok', code=201)
