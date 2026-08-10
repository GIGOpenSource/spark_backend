"""Spark local development settings — extends pro with local defaults."""
from .pro import *  # noqa: F401,F403
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

DEBUG = True
SECRET_KEY = os.getenv('SECRET_KEY', 'spark-dev-secret-key-change-in-prod')
ALLOWED_HOSTS = ['*']

TIME_ZONE = 'UTC'
USE_TZ = True

POSTGRES_HOST = (
    os.getenv('POSTGRES_BUILDMART_HOST')
    or os.getenv('DB_HOST')
    or os.getenv('POSTGRES_HOST')
    or '127.0.0.1'
)
POSTGRES_DB_NAME = os.getenv('POSTGRES_DB', 'spark')

# 硬性约束：远程开发只允许连接名为 spark 的库，禁止触碰其它库
if str(POSTGRES_DB_NAME).lower() != 'spark':
    raise RuntimeError(
        f'Refusing database "{POSTGRES_DB_NAME}". '
        'Spark development must use ONLY the remote database named "spark".'
    )

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'spark',  # 固定写死，避免 .env 被改错库
        'USER': os.getenv('POSTGRES_USER', 'buildmart@123'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'buildmart@123'),
        'HOST': POSTGRES_HOST,
        'PORT': os.getenv('POSTGRES_PORT', '55431'),
        'OPTIONS': {
            'options': '-c search_path=public',
        },
    }
}

INSTALLED_APPS = list(INSTALLED_APPS)  # noqa: F405
for app in ('corsheaders', 'channels'):
    if app not in INSTALLED_APPS:
        INSTALLED_APPS.insert(0 if app == 'corsheaders' else len(INSTALLED_APPS), app)

MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
if 'corsheaders.middleware.CorsMiddleware' not in MIDDLEWARE:
    MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = ['*']

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(ROOT_DIR, 'media')

ASGI_APPLICATION = 'uivsbe_backend.asgi.application'

_redis_host = os.getenv('REDIS_BUILDMART_HOST') or os.getenv('REDIS_HOST', '127.0.0.1')
_redis_port = int(os.getenv('REDIS_PORT') or os.getenv('REDIS_BUILDMART_PORT', '6389'))
_redis_password = os.getenv('REDIS_PASSWORD') or os.getenv('REDIS_BUILDMART_PASSWORD', '')
_redis_db = int(os.getenv('REDIS_DB', '15'))

try:
    import redis as _redis_lib
    _r = _redis_lib.Redis(
        host=_redis_host, port=_redis_port, password=_redis_password,
        db=_redis_db, socket_connect_timeout=2,
    )
    _r.ping()
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [{
                    'address': f"redis://:{_redis_password}@{_redis_host}:{_redis_port}/{_redis_db}",
                }],
                # C-05: isolate channel keys from Login: tokens on shared Redis DB 15
                'prefix': 'spark-asgi',
            },
        },
    }
except Exception:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

USE_FIREBASE_MOCK = os.getenv('USE_FIREBASE_MOCK', 'false').lower() == 'true'
USE_IAP_MOCK = os.getenv('USE_IAP_MOCK', 'false').lower() == 'true'
IAP_WEBHOOK_SECRET = os.getenv('IAP_WEBHOOK_SECRET', '')
USE_SMS_MOCK = os.getenv('USE_SMS_MOCK', 'true').lower() == 'true'
USE_AGORA_MOCK = os.getenv('USE_AGORA_MOCK', 'false').lower() == 'true'
DEFAULT_APP_ID = os.getenv('DEFAULT_APP_ID', 'spark_main')
GOOGLE_TRANSLATE_API_KEY = os.getenv('GOOGLE_TRANSLATE_API_KEY', '')
MAPS_ALLOW_MOCK = os.getenv('MAPS_ALLOW_MOCK', 'false').lower() == 'true'

SPECTACULAR_SETTINGS = {
    **SPECTACULAR_SETTINGS,  # noqa: F405
    'TITLE': 'Spark API',
    'DESCRIPTION': 'Spark dating / social product API',
    'VERSION': '1.0.0',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
