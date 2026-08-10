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
from models.models import Post, PostLike


@extend_schema(tags=[_('Moment')])
class MomentsViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    @extend_schema(summary=_('Moment 时间线'))
    @action(detail=False, methods=['get'], url_path='feed')
    def feed(self, request):
        user = request.user
        before = request.query_params.get('before')
        qs = visible_posts_qs(user.app_id or 'spark_main', Post.TYPE_MOMENT, viewer=user)
        if before:
            qs = qs.filter(id__lt=int(before))
        rows = list(qs[:30])
        liked_ids = set(
            PostLike.objects.filter(user=user, post_id__in=[p.id for p in rows]).values_list('post_id', flat=True)
        ) if rows else set()
        return ApiResponse(data={
            'list': [serialize_post(p, liked_ids=liked_ids) for p in rows],
        }, message='ok')

    @extend_schema(summary=_('发布 Moment'))
    @action(detail=False, methods=['post'], url_path='create')
    def create_moment(self, request):
        user = request.user
        text = request.data.get('text') or ''
        media_list = request.data.get('media') or []
        if not isinstance(media_list, list):
            media_list = []
        # moments: image-oriented; coerce media_type to image unless explicitly video
        normalized = []
        for m in media_list:
            item = dict(m)
            item['media_type'] = item.get('media_type') or 'image'
            normalized.append(item)
        post, err, data = create_post_with_media(
            user, post_type=Post.TYPE_MOMENT, text=text, media_list=normalized,
        )
        if err:
            return ApiResponse(code=400, message=err, data=data)
        return ApiResponse(data=serialize_post(post, viewer=user), message='ok', code=201)

    @extend_schema(summary=_('详情'))
    @action(detail=False, methods=['get'], url_path=r'(?P<pid>[^/.]+)')
    def moment_detail(self, request, pid=None):
        # 方法名不能叫 detail：会与 ViewSetMixin.detail 布尔属性冲突，打爆 /api/schema/
        user = request.user
        post = Post.objects.filter(
            id=pid, app_id=user.app_id or 'spark_main',
            post_type=Post.TYPE_MOMENT, status=Post.STATUS_VISIBLE,
        ).select_related('author').prefetch_related('media').first()
        if not post:
            return ApiResponse(message='not found', code=404)
        return ApiResponse(data=serialize_post(post, viewer=user), message='ok')

    @extend_schema(summary=_('评论'))
    @action(detail=False, methods=['get', 'post'], url_path=r'(?P<pid>[^/.]+)/comments')
    def comments(self, request, pid=None):
        user = request.user
        post = Post.objects.filter(
            id=pid, app_id=user.app_id or 'spark_main',
            post_type=Post.TYPE_MOMENT, status=Post.STATUS_VISIBLE,
        ).first()
        if not post:
            return ApiResponse(message='not found', code=404)
        if request.method == 'POST':
            c, err = add_comment(post, user, request.data.get('text'))
            if err:
                return ApiResponse(code=400, message=err)
            return ApiResponse(data=serialize_comment(c), message='ok', code=201)
        qs = post.comments.filter(status='visible').select_related('author').order_by('id')
        before = request.query_params.get('before')
        if before:
            qs = qs.filter(id__lt=int(before))
        return ApiResponse(data={'list': [serialize_comment(c) for c in qs[:50]]}, message='ok')

    @extend_schema(summary=_('点赞'))
    @action(detail=False, methods=['post'], url_path=r'(?P<pid>[^/.]+)/like')
    def like(self, request, pid=None):
        user = request.user
        post = Post.objects.filter(
            id=pid, app_id=user.app_id or 'spark_main',
            post_type=Post.TYPE_MOMENT, status=Post.STATUS_VISIBLE,
        ).first()
        if not post:
            return ApiResponse(message='not found', code=404)
        liked, count = toggle_like(post, user)
        return ApiResponse(data={'liked': liked, 'like_count': count}, message='ok')

    @extend_schema(summary=_('上传'))
    @action(
        detail=False, methods=['post'], url_path='upload',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def upload(self, request):
        user = request.user
        url = request.data.get('url')
        f = request.FILES.get('file')
        if f:
            name = f'moments/{user.id}/{uuid.uuid4().hex}_{getattr(f, "name", "img.jpg")}'
            path = default_storage.save(name, ContentFile(f.read()))
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            url = request.build_absolute_uri(media_url + path) if hasattr(request, 'build_absolute_uri') else media_url + path
        if not url:
            return ApiResponse(message='url or file required', code=400)
        return ApiResponse(data={'url': url}, message='ok', code=201)
