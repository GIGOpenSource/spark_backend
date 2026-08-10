"""Shared helpers for community / moments / short_video posts."""

from django.db import transaction
from django.db.models import F

from models.models import Post, PostMedia, PostComment, PostLike
from tools.spark_helpers import serialize_user_card, message_contains_banned, blocked_ids


def serialize_media(m):
    return {
        'id': m.id,
        'media_type': m.media_type,
        'url': m.url,
        'cover_url': m.cover_url or '',
        'duration_ms': m.duration_ms or 0,
        'sort': m.sort,
    }


def serialize_post(post, viewer=None, liked_ids=None):
    liked = False
    if liked_ids is not None:
        liked = post.id in liked_ids
    elif viewer is not None:
        liked = PostLike.objects.filter(post=post, user=viewer).exists()
    return {
        'id': post.id,
        'app_id': post.app_id,
        'post_type': post.post_type,
        'text': post.text or '',
        'status': post.status,
        'topic_id': post.topic_id,
        'like_count': post.like_count,
        'comment_count': post.comment_count,
        'liked': liked,
        'author': serialize_user_card(post.author),
        'media': [serialize_media(m) for m in post.media.all()],
        'created_at': post.created_at.isoformat() if post.created_at else None,
    }


def serialize_comment(c):
    return {
        'id': c.id,
        'post_id': c.post_id,
        'text': c.text,
        'author': serialize_user_card(c.author),
        'created_at': c.created_at.isoformat() if c.created_at else None,
    }


def create_post_with_media(user, *, post_type, text='', topic=None, media_list=None):
    """media_list: [{url, media_type?, cover_url?, duration_ms?, sort?}, ...]"""
    media_list = media_list or []
    banned = message_contains_banned(user.app_id, text or '', user.country or '*')
    if banned:
        return None, 'content_blocked', {'word': banned}
    if post_type == Post.TYPE_VIDEO:
        has_video = any((m.get('media_type') or 'video') == 'video' and m.get('url') for m in media_list)
        if not has_video:
            return None, 'video_required', None
    with transaction.atomic():
        post = Post.objects.create(
            app_id=user.app_id or 'spark_main',
            author=user,
            topic=topic,
            post_type=post_type,
            text=text or '',
            status=Post.STATUS_VISIBLE,
        )
        for i, m in enumerate(media_list):
            url = (m.get('url') or '').strip()
            if not url:
                continue
            PostMedia.objects.create(
                post=post,
                media_type=m.get('media_type') or (
                    PostMedia.MEDIA_VIDEO if post_type == Post.TYPE_VIDEO else PostMedia.MEDIA_IMAGE
                ),
                url=url,
                cover_url=m.get('cover_url') or '',
                duration_ms=int(m.get('duration_ms') or 0),
                sort=int(m.get('sort') if m.get('sort') is not None else i),
            )
    post = Post.objects.select_related('author').prefetch_related('media').get(id=post.id)
    return post, None, None


def visible_posts_qs(app_id, post_type=None, viewer=None):
    qs = Post.objects.filter(app_id=app_id, status=Post.STATUS_VISIBLE).select_related(
        'author', 'topic',
    ).prefetch_related('media')
    if post_type:
        qs = qs.filter(post_type=post_type)
    if viewer is not None:
        blocked = blocked_ids(viewer)
        if blocked:
            qs = qs.exclude(author_id__in=blocked)
    return qs.order_by('-id')


def toggle_like(post, user):
    existing = PostLike.objects.filter(post=post, user=user).first()
    if existing:
        existing.delete()
        Post.objects.filter(id=post.id, like_count__gt=0).update(like_count=F('like_count') - 1)
        post.refresh_from_db(fields=['like_count'])
        return False, post.like_count
    PostLike.objects.create(post=post, user=user)
    Post.objects.filter(id=post.id).update(like_count=F('like_count') + 1)
    post.refresh_from_db(fields=['like_count'])
    return True, post.like_count


def add_comment(post, user, text):
    text = (text or '').strip()
    if not text:
        return None, 'text required'
    banned = message_contains_banned(user.app_id, text, user.country or '*')
    if banned:
        return None, 'content_blocked'
    c = PostComment.objects.create(post=post, author=user, text=text)
    Post.objects.filter(id=post.id).update(comment_count=F('comment_count') + 1)
    return c, None
