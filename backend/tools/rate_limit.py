"""Lightweight Redis token-bucket rate limiting for hot API paths."""
import logging
import time
from functools import wraps

from tools.utils import ApiResponse

logger = logging.getLogger(__name__)


def _redis():
    from tools.token_tools import _redis as r
    return r


def token_bucket_allow(key: str, rate: float, capacity: float) -> bool:
    """
    Redis token bucket. `rate` tokens/sec, `capacity` burst size.
    Returns True if request is allowed.
    Fails open if Redis is unavailable.
    """
    try:
        client = _redis().client
        now = time.time()
        bucket_key = f'rl:tb:{key}'
        pipe = client.pipeline()
        pipe.hgetall(bucket_key)
        data = pipe.execute()[0] or {}
        tokens = float(data.get('tokens', capacity))
        last = float(data.get('ts', now))
        elapsed = max(0.0, now - last)
        tokens = min(capacity, tokens + elapsed * rate)
        if tokens < 1.0:
            client.hset(bucket_key, mapping={'tokens': tokens, 'ts': now})
            client.expire(bucket_key, max(60, int(capacity / max(rate, 0.01)) + 10))
            return False
        tokens -= 1.0
        client.hset(bucket_key, mapping={'tokens': tokens, 'ts': now})
        client.expire(bucket_key, max(60, int(capacity / max(rate, 0.01)) + 10))
        return True
    except Exception:
        logger.exception('rate_limit redis error; failing open')
        return True


def rate_limit(scope: str, rate: float = 5.0, capacity: float = 20.0, by: str = 'user'):
    """
    Decorator for ViewSet actions.

    by='user' → key includes authenticated user id (or anon IP)
    by='app'  → key includes app_id from request
    by='ip'   → client IP only
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, request, *args, **kwargs):
            uid = getattr(getattr(request, 'user', None), 'id', None) or 'anon'
            app_id = (
                request.query_params.get('app_id')
                or (getattr(request, 'data', {}) or {}).get('app_id')
                or getattr(getattr(request, 'user', None), 'app_id', None)
                or 'spark_main'
            )
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
                or '0.0.0.0'
            )
            if by == 'app':
                key = f'{scope}:app:{app_id}'
            elif by == 'ip':
                key = f'{scope}:ip:{ip}'
            else:
                key = f'{scope}:u:{uid}:app:{app_id}'
            if not token_bucket_allow(key, rate=rate, capacity=capacity):
                return ApiResponse(code=429, message='rate_limited')
            return fn(self, request, *args, **kwargs)
        return wrapper
    return decorator
