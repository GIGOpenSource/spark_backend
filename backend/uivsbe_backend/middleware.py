# template/middleware.py（和 settings.py 同级目录）
import logging
import os
import random
import time

logger = logging.getLogger('spark.timing')

# O-07: sample hot paths (feed / badges / conversations)
_TIMING_PATH_HINTS = (
    '/recommend/feed',
    '/auth/badges',
    '/chat/conversations',
)


class DummyUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 给 request 加一个 dummy user，仅满足 rosetta 的属性检查
        class DummyUser:
            is_authenticated = True  # 模拟已登录
            is_staff = True  # 模拟 staff 权限（rosetta 要求）
            is_superuser = True  # 模拟超级用户权限

        request.user = DummyUser()  # 给 request 绑定 user 属性
        response = self.get_response(request)
        return response


class TimingMiddleware:
    """Log request duration for hot paths when DEBUG or ~1% SAMPLE.

    Env:
      SPARK_TIMING_SAMPLE=0.01  (default) — probability when not DEBUG
      SPARK_TIMING_SAMPLE=1     — always log matching paths
    """

    def __init__(self, get_response):
        self.get_response = get_response
        try:
            self.sample = float(os.getenv('SPARK_TIMING_SAMPLE', '0.01'))
        except ValueError:
            self.sample = 0.01

    def __call__(self, request):
        path = getattr(request, 'path', '') or ''
        watch = any(h in path for h in _TIMING_PATH_HINTS)
        from django.conf import settings
        do_time = watch and (
            getattr(settings, 'DEBUG', False) or random.random() < self.sample
        )
        if not do_time:
            return self.get_response(request)
        t0 = time.perf_counter()
        response = self.get_response(request)
        ms = (time.perf_counter() - t0) * 1000.0
        logger.info(
            'timing path=%s method=%s status=%s ms=%.1f',
            path,
            getattr(request, 'method', ''),
            getattr(response, 'status_code', ''),
            ms,
        )
        return response
