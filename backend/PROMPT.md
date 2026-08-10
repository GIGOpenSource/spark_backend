# 后端项目复刻提示词

> 将以下内容完整复制，作为 prompt 发给任意 AI，即可生成与本项目完全一致的后端代码。

---

你是一个高级 Python/Django 后端工程师。请根据以下规范，从零搭建一个 Django 后端项目。**项目名称不限**，你可自行命名（如 `myproject`、`backend`、`app` 等），只需全局统一替换配置包目录名、settings 引用、`manage.py` 中的 `DJANGO_SETTINGS_MODULE` 即可。**只生成后端 admin 相关功能**，不需要前端。

---

## 一、技术栈（版本不限，按需选用）

| 组件 | 推荐版本 | 说明 |
|------|----------|------|
| Python | 3.11+ | 运行环境 |
| Django | 5.x | Web 框架 |
| Django REST Framework | 3.x | REST API |
| PostgreSQL | 14+ | 主数据库 |
| Redis | 6+ | Token 存储、缓存 |
| drf-spectacular | 0.28+ | API 文档（可选） |

**核心依赖（requirements.txt，版本不锁定，按需调整）：**
```
Django
djangorestframework
drf-spectacular
drf-spectacular-sidecar
django-cors-headers
psycopg2-binary
redis
python-dotenv
passlib
bcrypt
pycryptodome
```

---

## 二、目录结构（严格遵循，一个文件都不能少）

> **项目名称可自定义**，下面用 `{project}` 表示你的项目名（如 `myapp`、`backend` 等）。
> 对应的 Django 配置包目录为 `{project}_backend/`，`manage.py` 中的 `DJANGO_SETTINGS_MODULE` 也要跟着改。

```
backend/
├── manage.py
├── requirements.txt
├── .env                          # 环境变量（DB/Redis/COS 凭证）
├── .gitignore
├── {project}_backend/            # Django 配置包（名称自定义）
│   ├── __init__.py               # 空文件
│   ├── urls.py                   # 根路由
│   ├── wsgi.py
│   ├── asgi.py
│   └── settings/
│       ├── __init__.py           # 空文件
│       └── pro.py                # 唯一的 settings 文件
├── Apps/                         # 业务应用
│   ├── __init__.py               # 空文件
│   ├── urls.py                   # 应用路由注册
│   └── views/
│       ├── __init__.py           # 空文件
│       ├── user/                 # 用户模块
│       │   ├── __init__.py
│       │   ├── view.py
│       │   ├── urls.py           # 本模块不用单独 urls，路由在 Apps/urls.py 中用 router 注册
│       │   └── serializers.py
│       ├── admin/                # 管理员模块
│       │   ├── __init__.py
│       │   ├── view.py
│       │   ├── urls.py
│       │   └── serializers.py
│       └── Example/              # 示例模块（参考模板）
│           ├── __init__.py
│           ├── view.py
│           ├── urls.py
│           └── serializers.py
├── models/                       # 数据模型（统一定义，所有表都在这里）
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── migrations/
│       └── __init__.py
├── tools/                        # 工具类
│   ├── __init__.py
│   ├── utils.py                  # ApiResponse + CustomPagination
│   ├── base_views.py             # BaseViewSet
│   ├── authentication.py         # TokenAuthentication + CustomBasicAuthentication
│   ├── permissions.py            # IsTokenValid + IsAdmin
│   ├── token_tools.py            # CustomTokenTool（Redis + AES）
│   ├── auth_helpers.py           # persist_auth / clear_auth / get_token_from_request
│   ├── password_hasher.py        # bcrypt 密码哈希
│   ├── tools.py                  # getEnvConfig + CustomStatus 枚举
│   └── redis.py                  # Redis 连接测试（可选）
└── middleware/
    ├── __init__.py
    └── c_permission.py           # IsTokenValid 的 middleware 版本
```

---

## 三、全局强制规范（违反任何一条即为错误）

> **项目名称不限**，你可自行命名。只需全局统一替换配置包目录名、settings 引用、`manage.py` 中的 `DJANGO_SETTINGS_MODULE` 即可。

1. **所有时间统一 UTC**，数据库时间、接口返回时间、日志时间全部 UTC。
2. **全局使用 `logging.getLogger(__name__)`**，**禁止 `print`**。
3. **所有接口强制使用 `ApiResponse` 返回**，禁止手动构造 JSON 响应。
4. **所有表名以 `t_` 开头**（如 `t_user`、`t_example`）。
5. **禁止使用 `django.contrib.auth`**、SessionAuthentication、JWT。需要认证就自己用 Redis + AES 写。
6. **新模块结构**：`Apps/views/NewModule/` 下放 `view.py`、`urls.py`、`serializers.py`。
7. **每个 ViewSet 必须加 `@extend_schema(tags=[...])`**，每个接口必须有 `summary`。
8. **错误码**：200 成功、201 创建成功、400 参数错误、401 未授权、403 禁止、404 不存在、500 服务器错误。

---

## 四、INSTALLED_APPS（基础固定，按需扩展）

> 不管项目叫什么名字，`INSTALLED_APPS` 里永远是 `"Apps"` 和 `"models"`，这是业务应用的固定名称。
> 其余按需添加，但 **不要引入 `django.contrib.auth`**（见下方认证规范）。

```python
INSTALLED_APPS = [
    "Apps",               # 业务应用（固定）
    "models",             # 数据模型（固定）
    'rest_framework',     # DRF（必须）
    'drf_spectacular',    # API 文档（推荐）
    'drf_spectacular_sidecar',
    # 可按需添加，如 'django_cors_headers' 等
]
```

### 认证规范（重要）

**禁止使用 Django 自带认证体系**，包括：
- ❌ `django.contrib.auth`（不要加入 INSTALLED_APPS）
- ❌ `SessionAuthentication`
- ❌ `JWT`（第三方库）
- ❌ Django 自带的 `User` 模型

**如果项目需要 Token 认证，必须自己实现：**
- ✅ 用 **Redis** 存储 Token（不依赖数据库存 Token）
- ✅ 用 **AES 加密** 生成 Token（或类似方案）
- ✅ 自定义 `TokenAuthentication` 类
- ✅ 自定义 `IsTokenValid` / `IsAdmin` 权限类
- ✅ 自定义 `User` 模型（在 `models/models.py` 中定义）

下方第五节有每个工具文件的完整代码，直接照搬即可。

---

## 五、各文件完整代码

### 5.1 `manage.py`

> 将 `uivsbe_backend` 替换为你的 `{project}_backend`。

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project}_backend.settings.pro')  # 替换
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
```

### 5.2 `{project}_backend/settings/pro.py`

> 将下面所有 `uivsbe_backend` 替换为你的 `{project}_backend`。

```python
"""
Django settings for {project} project.
"""
import sys
from pathlib import Path
from django.utils.translation import gettext_noop
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# 国际化
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True

LANGUAGES = [
    ('zh-hans', gettext_noop('Simplified Chinese')),
    ('zh-hant', gettext_noop('Traditional Chinese')),
    ('ja', gettext_noop('Japanese')),
    ('ko', gettext_noop('Korean')),
    ('en', gettext_noop('English')),
    ('de', gettext_noop('German')),
    ('fr', gettext_noop('French')),
    ('es', gettext_noop('Spanish')),
]
LOCALE_PATHS = [
    os.path.join(BASE_DIR.parent, 'locale'),
]

# 加载 .env
env_path = BASE_DIR.parent / ".env"
from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

SECRET_KEY = 'django-insecure-(vmo#itel@_(bv*y5j^@*4mp=7%!*d&l4r*af-fb2jj046s!(l'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    "Apps",
    "models",
    'rest_framework',
    'drf_spectacular',
    'drf_spectacular_sidecar',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = '{project}_backend.urls'  # 替换为你的项目名

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = '{project}_backend.wsgi.application'  # 替换为你的项目名

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'tools.authentication.TokenAuthentication',
        'tools.authentication.CustomBasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'UNAUTHENTICATED_USER': None
}

SPECTACULAR_SETTINGS = {
    'TITLE': '{project} API',  # 替换为你的项目名
    'DESCRIPTION': '一站式后端极速脚手架，统一响应、视图封装、业务层、数据实体、自带 API 文档。',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

POSTGRES_HOST = os.getenv('POSTGRES_BUILDMART_HOST') or os.getenv('DB_HOST')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'uivsbe'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': POSTGRES_HOST or 'localhost',
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### 5.3 `{project}_backend/urls.py`

```python
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.http import JsonResponse

def home(request):
    return JsonResponse({"message": "Welcome to API", "version": "1.0.0"})

urlpatterns = [
    path('', home, name='home'),
    path('api/', include('Apps.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

### 5.4 `{project}_backend/wsgi.py`

```python
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project}_backend.settings.pro')  # 替换
application = get_wsgi_application()
```

### 5.5 `{project}_backend/asgi.py`

```python
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project}_backend.settings.pro')  # 替换
application = get_asgi_application()
```

### 5.6 `tools/utils.py` — ApiResponse + CustomPagination

```python
import logging
from django.core.paginator import EmptyPage
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.utils.translation import gettext as _


class ApiResponse(Response):
    """统一响应格式"""
    def __init__(self, data=None, message='success', code=200, pagination=None, **kwargs):
        # 确保 message 是字符串类型
        if not isinstance(message, str):
            if isinstance(message, dict):
                message = "; ".join([f"{k}: {', '.join(v)}" for k, v in message.items()])
            else:
                message = str(message)
        # 确保 data 不为 null
        if data is None:
            data = {}

        response_data = {
            'code': code,
            'message': message,
            'results': data
        }

        if pagination is not None:
            response_data["pagination"] = pagination
        # 始终使用 200 作为 HTTP 状态码
        super().__init__(response_data, status=200, **kwargs)


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_query_param = 'currentPage'
    page_size_query_param = 'pageSize'
    max_page_size = 999

    def get_paginated_response(self, data):
        pagination_info = {
            'page': self.page.number,
            'page_size': self.page.paginator.per_page,
            'total': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages
        }
        return ApiResponse(data=data, pagination=pagination_info)

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except Exception as e:
            if "Invalid page" in str(e) or isinstance(e, EmptyPage):
                self.request = request
                page_size = self.get_page_size(request) or self.page_size
                from django.core.paginator import Paginator
                empty_paginator = Paginator([], page_size)
                self.page = empty_paginator.page(1)
                return []
            raise e


def custom_exception_handler(exc, context):
    """自定义异常处理函数"""
    response = exception_handler(exc, context)
    if isinstance(exc, NotFound) and ("Invalid page" in str(exc.detail) or "无效页面" in str(exc.detail)):
        return ApiResponse(
            data={
                'pagination': {
                    'page': 1,
                    'page_size': 20,
                    'total': 0,
                    'total_pages': 0
                },
                'results': []
            },
            message=_("请求的页面超出范围，返回空结果"),
            code=200
        )
    return response
```

### 5.7 `tools/base_views.py` — BaseViewSet

```python
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from tools.utils import ApiResponse


class BaseViewSet(viewsets.ModelViewSet):
    """基础 ViewSet，统一处理响应格式为 ApiResponse"""

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(queryset, many=True)
            return ApiResponse(code=200, data=serializer.data, message="列表获取成功")
        except Exception as e:
            return ApiResponse(code=500, message=f"列表获取失败: {str(e)}")

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return ApiResponse(data=serializer.data, message="详情获取成功")
        except ObjectDoesNotExist:
            return ApiResponse(code=404, message=f"{self.queryset.model.__name__}不存在")
        except Exception as e:
            return ApiResponse(code=500, message=f"详情获取失败: {str(e)}")

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return ApiResponse(data=serializer.data, message="创建成功", code=201)
        except ValidationError as e:
            return ApiResponse(code=400, message=str(e.detail))
        except Exception as e:
            return ApiResponse(code=500, message=f"创建失败: {str(e)}")

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return ApiResponse(data=serializer.data, message="更新成功")
        except ObjectDoesNotExist:
            return ApiResponse(code=404, message=f"{self.queryset.model.__name__}不存在")
        except ValidationError as e:
            return ApiResponse(code=400, message=e.detail)
        except Exception as e:
            return ApiResponse(code=500, message=f"更新失败: {str(e)}")

    def partial_update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return ApiResponse(data=serializer.data, message="部分更新成功")
        except ObjectDoesNotExist:
            return ApiResponse(code=404, message=f"{self.queryset.model.__name__}不存在")
        except ValidationError as e:
            return ApiResponse(code=400, message=e.detail)
        except Exception as e:
            return ApiResponse(code=500, message=f"部分更新失败: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return ApiResponse(message="删除成功")
        except ObjectDoesNotExist:
            return ApiResponse(code=404, message=f"{self.queryset.model.__name__}不存在")
        except Exception as e:
            return ApiResponse(code=500, message=f"删除失败: {str(e)}")
```

### 5.8 `tools/password_hasher.py`

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw_password: str) -> str:
    """哈希密码（处理72字节限制）"""
    truncated_password = raw_password[:72]
    return pwd_context.hash(truncated_password)

def verify_password(raw_password: str, hashed_password: str) -> bool:
    """验证密码"""
    truncated_password = raw_password[:72]
    return pwd_context.verify(truncated_password, hashed_password)
```

### 5.9 `tools/tools.py` — getEnvConfig + CustomStatus

```python
import os
from enum import Enum
import logging
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)
logger = logging.getLogger('info')


def getEnvConfig(key: str, default=None):
    """获取环境变量"""
    return os.getenv(key, default)


class CustomStatus(Enum):
    """自定义状态枚举类"""
    SUCCESS = (200, "成功")
    CREATED = (201, "创建成功")
    UPDATED = (202, "更新成功")
    DELETED = (204, "删除成功")
    BAD_REQUEST = (400, "请求参数错误")
    UNAUTHORIZED = (401, "未授权访问")
    FORBIDDEN = (403, "禁止访问")
    NOT_FOUND = (404, "资源不存在")
    USERNAME_EXISTS = (1001, "用户名已存在")
    INVALID_CREDENTIALS = (1002, "用户名或密码错误")
    ACCOUNT_DISABLED = (1003, "账户已被禁用")
    TOKEN_EXPIRED = (1005, "令牌已过期")
    TOKEN_INVALID = (1006, "令牌无效")
    INTERNAL_ERROR = (500, "服务器内部错误")

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def to_dict(self):
        return {'code': self.code, 'message': self.message}
```

### 5.10 `tools/token_tools.py` — CustomTokenTool（Redis + AES）

```python
import redis
import base64
import time
from datetime import timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from tools.tools import getEnvConfig

# 全局配置
AES_SECRET_KEY = b"zhiliao-12345678"
TOKEN_EXPIRE_HOURS = 2
ROOM_TOKEN_EXPIRE_HOURS = 4
AES_IV_LENGTH = 16

REDIS_LOGIN_PREFIX = "Login:"
REDIS_CHAT_PREFIX = "ChatRoom:"


class RedisTool(object):
    """redis 工具类"""
    def __init__(self):
        self.host = getEnvConfig("REDIS_BUILDMART_HOST", "localhost")
        self.port = int(getEnvConfig("REDIS_PORT", 6389))
        self.password = getEnvConfig("REDIS_BUILDMART_PASSWORD", "")
        self.db = int(getEnvConfig("REDIS_DB", 0))
        self.ex = 3600
        max_connections = getEnvConfig("REDIS_MAX_CONNECTIONS", 10)
        try:
            max_connections = int(max_connections)
            if max_connections <= 0:
                raise ValueError("max_connections 必须是正整数")
        except (ValueError, TypeError):
            raise ValueError("max_connections 必须是正整数")

        self.pool = redis.ConnectionPool(
            host=self.host, port=self.port,
            password=self.password, db=self.db,
            max_connections=max_connections
        )
        self.client = redis.Redis(connection_pool=self.pool, decode_responses=True)

    def setKey(self, key, values, ex=None):
        expire = ex if ex else self.ex
        self.client.set(key, values, ex=expire)
        return True

    def getKey(self, key):
        return self.client.get(key)

    def delKey(self, key):
        self.client.delete(key)
        return True

    def expireKey(self, key, ex=None):
        expire = ex if ex else self.ex
        self.client.expire(key, expire)


_redis = RedisTool()


class CustomTokenTool:
    @staticmethod
    def _aes_encrypt(data: bytes) -> tuple[bytes, bytes]:
        iv = get_random_bytes(AES_IV_LENGTH)
        cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data, AES.block_size))
        return encrypted_data, iv

    @staticmethod
    def _aes_decrypt(encrypted_data: bytes, iv: bytes) -> bytes:
        cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        return decrypted_data

    @classmethod
    def generate_token(cls, user_id: int, remember: bool = False) -> str:
        expire_timestamp = int(time.time()) + int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
        token_core = f"{user_id}:{expire_timestamp}".encode("utf-8")
        encrypted_core, iv = cls._aes_encrypt(token_core)
        token_bytes = iv + encrypted_core
        raw_token = base64.b64encode(token_bytes).decode("utf-8")
        token = f"{REDIS_LOGIN_PREFIX}{raw_token}"
        expire_seconds = int(timedelta(days=30 if remember else 7).total_seconds())
        _redis.setKey(token, user_id, ex=expire_seconds)
        return token

    @classmethod
    def verify_token(cls, token: str) -> tuple[bool, int | None]:
        try:
            if not token:
                return False, None
            redis_key = token if token.startswith(REDIS_LOGIN_PREFIX) else f"{REDIS_LOGIN_PREFIX}{token}"
            user_id_str = _redis.getKey(redis_key)
            if not user_id_str:
                return False, None
            _redis.expireKey(redis_key)
            return True, int(user_id_str)
        except Exception:
            return False, None

    @classmethod
    def delete_token(cls, token):
        if not token:
            return
        redis_key = token if str(token).startswith(REDIS_LOGIN_PREFIX) else f"{REDIS_LOGIN_PREFIX}{token}"
        _redis.delKey(redis_key)

    @classmethod
    def delete_user_all_tokens(cls, user_id: int):
        try:
            keys = _redis.client.keys(f"{REDIS_LOGIN_PREFIX}*")
            for key in keys:
                val = _redis.getKey(key)
                if val and str(val) == str(user_id):
                    _redis.delKey(key)
            return True
        except Exception:
            return False

    @classmethod
    def generate_room_token(cls, room_id: str | int) -> str:
        expire_timestamp = int(time.time()) + int(timedelta(hours=ROOM_TOKEN_EXPIRE_HOURS).total_seconds())
        token_core = f"{room_id}:{expire_timestamp}".encode("utf-8")
        encrypted_core, iv = cls._aes_encrypt(token_core)
        token_bytes = iv + encrypted_core
        raw_token = base64.b64encode(token_bytes).decode("utf-8")
        room_token = f"RoomToken:{raw_token}"
        redis_key = f"{REDIS_CHAT_PREFIX}{room_token}"
        _redis.setKey(redis_key, str(room_id), ex=int(timedelta(hours=ROOM_TOKEN_EXPIRE_HOURS).total_seconds()))
        return room_token

    @classmethod
    def verify_room_token(cls, room_token: str) -> tuple[bool, str | None]:
        try:
            if not room_token or not room_token.startswith("RoomToken:"):
                return False, None
            redis_key = f"{REDIS_CHAT_PREFIX}{room_token}"
            room_id = _redis.getKey(redis_key)
            if not room_id:
                return False, None
            _redis.expireKey(redis_key, ex=int(timedelta(hours=ROOM_TOKEN_EXPIRE_HOURS).total_seconds()))
            return True, room_id
        except Exception:
            return False, None

    @classmethod
    def delete_room_token(cls, room_token: str):
        if room_token and room_token.startswith("RoomToken:"):
            redis_key = f"{REDIS_CHAT_PREFIX}{room_token}"
            _redis.delKey(redis_key)


def generate_is_user_token(request, user):
    if request:
        existing_token = 0
        if existing_token:
            is_valid, user_id = CustomTokenTool.verify_token(existing_token)
            if is_valid and user_id == user.id:
                return existing_token
    token = CustomTokenTool.generate_token(user.id)
    return token


def generate_login_user_token(request, user, remember=False):
    CustomTokenTool.delete_user_all_tokens(user.id)
    token = CustomTokenTool.generate_token(user.id, remember=remember)
    return token
```

### 5.11 `tools/auth_helpers.py`

```python
from datetime import timedelta
from tools.token_tools import TOKEN_EXPIRE_HOURS

SESSION_EXPIRE_SECONDS = int(timedelta(days=7).total_seconds())
REMEMBER_EXPIRE_SECONDS = int(timedelta(days=30).total_seconds())
COOKIE_NAME = 'auth_token'


def get_token_from_request(request) -> str | None:
    """从请求中提取 token（header / Authorization / cookie）"""
    token = request.headers.get('token')
    if token:
        return token.strip()
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Token '):
        return auth_header[6:].strip()
    if auth_header.startswith('Bearer '):
        return auth_header[7:].strip()
    token = request.COOKIES.get(COOKIE_NAME)
    if token:
        return token.strip()
    return None


def persist_auth(request, response, token: str, user_id: int, remember: bool = False):
    """登录成功后写入 Cookie"""
    max_age = REMEMBER_EXPIRE_SECONDS if remember else SESSION_EXPIRE_SECONDS
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=max_age, httponly=False,
        samesite='Lax', secure=False,
    )
    return response


def clear_auth(request, response):
    """登出时清除 Cookie"""
    response.delete_cookie(COOKIE_NAME)
    return response


def token_redis_expire(remember: bool = False) -> int:
    if remember:
        return REMEMBER_EXPIRE_SECONDS
    return int(timedelta(hours=TOKEN_EXPIRE_HOURS).total_seconds())
```

### 5.12 `tools/authentication.py`

```python
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _
from models.models import User
from tools.password_hasher import verify_password
from tools.token_tools import CustomTokenTool, generate_is_user_token
from tools.auth_helpers import get_token_from_request


class CustomBasicAuthentication(BasicAuthentication):
    """完全重写 BasicAuthentication，使用自定义密码验证逻辑，应用到 Swagger UI"""
    def authenticate_credentials(self, userid, password, request=None):
        try:
            user = User.objects.get(username=userid)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=userid)
            except User.DoesNotExist:
                raise AuthenticationFailed(_('无效的用户名或密码'))
        if not verify_password(password, user.password):
            raise AuthenticationFailed(_('无效的用户名或密码'))
        token = generate_is_user_token(request, user)
        return (user, token)

    def authenticate_header(self, request):
        return 'Basic realm="%s"' % self.www_authenticate_realm


from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomBasicAuthSchema(OpenApiAuthenticationExtension):
    target_class = 'tools.authentication.CustomBasicAuthentication'
    name = 'CustomBasicAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'basic',
            'description': "使用用户名/密码登录（密码验证逻辑：截断72字节后验证）"
        }


class TokenAuthentication(BasicAuthentication):
    """基于Token的认证：支持 token 请求头、Authorization、Cookie"""
    def authenticate(self, request):
        token = get_token_from_request(request)
        if not token:
            return None
        is_valid, user_id = CustomTokenTool.verify_token(token)
        if not is_valid or not user_id:
            return None
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
        return (user, token)

    def authenticate_header(self, request):
        return 'Token realm="API"'


class TokenAuthSchema(OpenApiAuthenticationExtension):
    target_class = 'tools.authentication.TokenAuthentication'
    name = 'TokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'token',
            'description': '通过token进行认证，支持 header: token / Authorization: Token xxx / Cookie'
        }
```

### 5.13 `tools/permissions.py`

```python
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from models.models import User
from tools.token_tools import CustomTokenTool
from tools.auth_helpers import get_token_from_request


class IsAdmin(BasePermission):
    """管理员权限：role 为 operator/admin/super_admin"""
    def has_permission(self, request, view):
        try:
            role = request.user.role
        except AttributeError:
            raise AuthenticationFailed({"code": 401, "message": "管理员无role权限"})
        if not request.user or not role:
            raise AuthenticationFailed({"code": 401, "message": "请提供有效的管理员token"})
        try:
            if role in ['operator', 'admin', 'super_admin']:
                return True
            else:
                raise AuthenticationFailed({"code": 401, "message": "管理员role权限不够"})
        except User.DoesNotExist:
            raise AuthenticationFailed('token对应的管理员不存在')


class IsTokenValid(BasePermission):
    """自定义权限：仅允许携带有效 Token 的请求访问"""
    message = "Token 无效或已过期"

    def has_permission(self, request, view):
        token = get_token_from_request(request)
        is_valid, user_id = CustomTokenTool.verify_token(token)
        if is_valid and user_id:
            try:
                request.user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return False
            return True
        return False
```

### 5.14 `models/apps.py`

```python
from django.apps import AppConfig

class ModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'models'
    verbose_name = '数据模型'
```

### 5.15 `models/models.py`

```python
from django.db import models
from tools.password_hasher import hash_password


class User(models.Model):
    """用户表"""
    username = models.CharField(max_length=20, unique=True, verbose_name="用户名")
    email = models.EmailField(unique=True, verbose_name="邮箱")
    password = models.CharField(max_length=256, verbose_name="密码")
    role = models.CharField(max_length=20, default="user", verbose_name="角色")
    status = models.IntegerField(default=1, verbose_name="状态")  # 1: 正常, 0: 禁用
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def save(self, *args, **kwargs):
        if not self.password.startswith('$2b$'):
            self.password = hash_password(self.password[:72])
        super().save(*args, **kwargs)

    class Meta:
        db_table = 't_user'
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return self.username


class Example(models.Model):
    """示例表 — 建表规范参考，表名以 t_ 开头"""
    STATUS_DRAFT = 0
    STATUS_ACTIVE = 1
    STATUS_DISABLED = 2
    STATUS_CHOICES = [
        (STATUS_DRAFT, '草稿'),
        (STATUS_ACTIVE, '启用'),
        (STATUS_DISABLED, '禁用'),
    ]

    name = models.CharField(max_length=100, verbose_name="名称")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    status = models.IntegerField(default=STATUS_ACTIVE, choices=STATUS_CHOICES, verbose_name="状态")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    remark = models.CharField(max_length=500, null=True, blank=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 't_example'
        verbose_name = "示例"
        verbose_name_plural = "示例"
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.name
```

### 5.16 `Apps/urls.py`

```python
from django.urls import path, include
from rest_framework import routers
from Apps.views.user.view import UserViewSet, AdminUserViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', include('Apps.views.admin.urls')),
    path('example/', include('Apps.views.Example.urls')),
]
```

### 5.17 `Apps/views/user/serializers.py`

```python
from rest_framework import serializers
from models.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'status', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_username(self, value):
        queryset = User.objects.filter(username=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("用户名已存在")
        return value

    def validate_email(self, value):
        queryset = User.objects.filter(email=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("邮箱已存在")
        return value
```

### 5.18 `Apps/views/user/view.py`

```python
from django.db import IntegrityError
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view
from tools.permissions import IsTokenValid
from tools.token_tools import CustomTokenTool, generate_login_user_token
from tools.auth_helpers import persist_auth, clear_auth, get_token_from_request
from models.models import User
from tools.password_hasher import verify_password
from django.utils.translation import gettext as _
from tools.base_views import BaseViewSet
from tools.utils import ApiResponse, CustomPagination
from Apps.views.user.serializers import UserSerializer


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'confirm_password')

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError(_("两次输入的密码不一致"))
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


@extend_schema(tags=[_("用户管理")])
@extend_schema_view(
    list=extend_schema(summary=_('获取用户列表（需有效 Token）')),
)
class UserViewSet(viewsets.ViewSet):
    permission_classes_by_action = {
        'register': [],
        'login': [],
        'me': [],
        'list': [IsTokenValid],
        'retrieve': [IsTokenValid],
    }
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def get_permissions(self):
        return [perm() for perm in self.permission_classes_by_action.get(self.action, [])]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: {"type": "object", "properties": {"token": {"type": "string"}, "user_id": {"type": "integer"}}}},
        summary=_("用户注册"),
    )
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(message=str(serializer.errors), code=400)
        user = serializer.save()
        remember = bool(request.data.get('remember'))
        token = CustomTokenTool.generate_token(user_id=user.id, remember=remember)
        response = ApiResponse(
            data={"token": token, "user_id": user.id, "username": user.username},
            message=_('注册成功'), code=201
        )
        persist_auth(request, response, token, user.id, remember=remember)
        return response

    @extend_schema(
        request=LoginSerializer,
        responses={200: {"type": "object", "properties": {"token": {"type": "string"}, "user_id": {"type": "integer"}}}},
        summary=_("用户登录"),
    )
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return ApiResponse(message=_('用户名和密码不能为空'), code=400)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return ApiResponse(message=_('用户名不存在'), code=400)
        except IntegrityError:
            return ApiResponse(message=_('用户名重复'), code=400)
        if verify_password(password, user.password):
            remember = bool(request.data.get('remember'))
            token = generate_login_user_token(request, user, remember=remember)
            response = ApiResponse(
                data={"token": token, "user_id": user.id, "username": user.username},
                message=_('登录成功')
            )
            persist_auth(request, response, token, user.id, remember=remember)
            return response
        return ApiResponse(message=_('用户名或密码错误'), code=400)

    @extend_schema(
        responses={200: {"type": "object", "properties": {
            "user_id": {"type": "integer"}, "username": {"type": "string"}, "role": {"type": "string"},
        }}},
        summary=_("获取当前登录用户信息")
    )
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        token = get_token_from_request(request)
        if not token:
            return ApiResponse(message=_('未登录'), code=401)
        is_valid, user_id = CustomTokenTool.verify_token(token)
        if not is_valid:
            return ApiResponse(message=_('Token无效或已过期'), code=401)
        try:
            user = User.objects.get(id=user_id)
            return ApiResponse(data={"user_id": user.id, "username": user.username, "role": user.role})
        except User.DoesNotExist:
            return ApiResponse(message=_('用户不存在'), code=404)

    def list(self, request):
        users = self.queryset.all().order_by('-created_at')
        paginator = CustomPagination()
        page = paginator.paginate_queryset(users, request)
        if page is not None:
            serializer = RegisterSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = RegisterSerializer(users, many=True)
        return ApiResponse(data=serializer.data)

    @extend_schema(
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
        summary="用户登出"
    )
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        token = get_token_from_request(request)
        if token:
            CustomTokenTool.delete_token(token)
        response = ApiResponse(message=_("登出成功，Token 已失效"))
        return clear_auth(request, response)


@extend_schema(tags=[_("用户管理-后台")])
@extend_schema_view(
    list=extend_schema(summary=_('获取用户列表')),
    retrieve=extend_schema(summary=_('获取用户详情')),
    create=extend_schema(summary=_('创建用户')),
    update=extend_schema(summary=_('更新用户')),
    partial_update=extend_schema(summary=_('部分更新用户')),
    destroy=extend_schema(summary=_('删除用户')),
)
class AdminUserViewSet(BaseViewSet):
    """后台用户管理 ViewSet"""
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserSerializer
    pagination_class = CustomPagination
    filterset_fields = ['username', 'email', 'role', 'status']

    @extend_schema(
        responses={200: {"type": "object", "properties": {
            "user_id": {"type": "integer"}, "status": {"type": "integer"},
        }}},
        summary=_("启用/禁用用户")
    )
    @action(detail=True, methods=['post'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        user = self.get_object()
        user.status = 0 if user.status == 1 else 1
        user.save()
        return ApiResponse(data={"user_id": user.id, "status": user.status}, message=_("状态已更新"))
```

### 5.19 `Apps/views/admin/serializers.py`

```python
from rest_framework import serializers
from models.models import User
from django.utils.translation import gettext as _


class AdminRegisterSerializer(serializers.ModelSerializer):
    """管理员注册序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'confirm_password')

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError(_("两次输入的密码不一致"))
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        validated_data['role'] = 'admin'
        user = User.objects.create(**validated_data)
        return user


class AdminLoginSerializer(serializers.Serializer):
    """管理员登录序列化器"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class AdminUserSerializer(serializers.ModelSerializer):
    """管理员信息序列化器"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'status', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
```

### 5.20 `Apps/views/admin/view.py`

```python
from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view
from tools.permissions import IsTokenValid, IsAdmin
from tools.token_tools import CustomTokenTool, generate_login_user_token
from tools.auth_helpers import persist_auth, clear_auth, get_token_from_request
from models.models import User
from tools.password_hasher import verify_password
from tools.utils import ApiResponse, CustomPagination
from django.utils.translation import gettext as _
from Apps.views.admin.serializers import (
    AdminRegisterSerializer, AdminLoginSerializer, AdminUserSerializer,
)


@extend_schema(tags=[_("管理员管理")])
@extend_schema_view(
    list=extend_schema(summary=_('获取管理员列表')),
)
class AdminViewSet(viewsets.ViewSet):
    """管理员登录注册视图"""
    permission_classes_by_action = {
        'register': [],
        'login': [],
        'list': [IsTokenValid, IsAdmin],
        'info': [IsTokenValid, IsAdmin],
    }

    def get_permissions(self):
        return [perm() for perm in self.permission_classes_by_action.get(self.action, [])]

    @extend_schema(
        request=AdminRegisterSerializer,
        responses={201: {"type": "object", "properties": {
            "token": {"type": "string"}, "user_id": {"type": "integer"}, "username": {"type": "string"}
        }}},
        summary=_("管理员注册"),
    )
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        serializer = AdminRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return ApiResponse(message=str(serializer.errors), code=400)
        user = serializer.save()
        remember = bool(request.data.get('remember'))
        token = CustomTokenTool.generate_token(user_id=user.id, remember=remember)
        response = ApiResponse(
            data={"token": token, "user_id": user.id, "username": user.username, "role": user.role},
            message=_('注册成功'), code=201
        )
        persist_auth(request, response, token, user.id, remember=remember)
        return response

    @extend_schema(
        request=AdminLoginSerializer,
        responses={200: {"type": "object", "properties": {
            "token": {"type": "string"}, "user_id": {"type": "integer"},
            "username": {"type": "string"}, "role": {"type": "string"}
        }}},
        summary=_("管理员登录")
    )
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return ApiResponse(message=_('用户名和密码不能为空'), code=400)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return ApiResponse(message=_('用户名不存在'), code=400)
        except IntegrityError:
            return ApiResponse(message=_('用户名重复'), code=400)
        if user.role not in ['admin', 'operator', 'super_admin']:
            return ApiResponse(message=_('该账号不是管理员账号'), code=403)
        if user.status == 0:
            return ApiResponse(message=_('该账号已被禁用'), code=403)
        if verify_password(password, user.password):
            remember = bool(request.data.get('remember'))
            token = generate_login_user_token(request, user, remember=remember)
            response = ApiResponse(
                data={"token": token, "user_id": user.id, "username": user.username, "role": user.role},
                message=_('登录成功')
            )
            persist_auth(request, response, token, user.id, remember=remember)
            return response
        return ApiResponse(message=_('用户名或密码错误'), code=400)

    @extend_schema(
        responses={200: AdminUserSerializer},
        summary=_("获取当前管理员信息")
    )
    @action(detail=False, methods=['get'], url_path='info')
    def info(self, request):
        token = get_token_from_request(request)
        is_valid, user_id = CustomTokenTool.verify_token(token)
        if not is_valid:
            return ApiResponse(message=_('Token无效或已过期'), code=401)
        try:
            user = User.objects.get(id=user_id)
            serializer = AdminUserSerializer(user)
            return ApiResponse(data=serializer.data)
        except User.DoesNotExist:
            return ApiResponse(message=_('用户不存在'), code=404)

    @extend_schema(
        responses={200: {"type": "object", "properties": {"message": {"type": "string"}}}},
        summary=_("管理员登出")
    )
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        token = get_token_from_request(request)
        if token:
            CustomTokenTool.delete_token(token)
        response = ApiResponse(message=_("登出成功，Token 已失效"))
        return clear_auth(request, response)

    def list(self, request):
        admins = User.objects.filter(role__in=['admin', 'operator', 'super_admin']).order_by('-created_at')
        paginator = CustomPagination()
        page = paginator.paginate_queryset(admins, request)
        if page is not None:
            serializer = AdminUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = AdminUserSerializer(admins, many=True)
        return ApiResponse(data=serializer.data)
```

### 5.21 `Apps/views/admin/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Apps.views.admin.view import AdminViewSet

router = DefaultRouter()
router.register('', AdminViewSet, basename='admin')

urlpatterns = [
    path('', include(router.urls)),
]
```

### 5.22 `Apps/views/Example/serializers.py`

```python
from rest_framework import serializers
from models.models import Example


class ExampleSerializer(serializers.ModelSerializer):
    """示例序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Example
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExampleCreateSerializer(serializers.ModelSerializer):
    """示例创建序列化器"""
    class Meta:
        model = Example
        fields = ['name', 'description', 'status', 'sort_order', 'remark']


class ExampleUpdateSerializer(serializers.ModelSerializer):
    """示例更新序列化器"""
    class Meta:
        model = Example
        fields = ['name', 'description', 'status', 'sort_order', 'is_deleted', 'remark']
```

### 5.23 `Apps/views/Example/view.py`

```python
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils.translation import gettext as _
from tools.base_views import BaseViewSet
from tools.utils import ApiResponse, CustomPagination
from models.models import Example
from Apps.views.Example.serializers import (
    ExampleSerializer, ExampleCreateSerializer, ExampleUpdateSerializer,
)


@extend_schema(tags=[_("示例管理")])
@extend_schema_view(
    list=extend_schema(summary=_('获取示例列表')),
    retrieve=extend_schema(summary=_('获取示例详情')),
    create=extend_schema(summary=_('创建示例')),
    update=extend_schema(summary=_('更新示例')),
    partial_update=extend_schema(summary=_('部分更新示例')),
    destroy=extend_schema(summary=_('删除示例')),
)
class ExampleViewSet(BaseViewSet):
    """示例视图集 — 演示 BaseViewSet + ApiResponse + CustomPagination 的标准用法"""
    queryset = Example.objects.filter(is_deleted=False)
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return ExampleCreateSerializer
        if self.action in ('update', 'partial_update'):
            return ExampleUpdateSerializer
        return ExampleSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return ApiResponse(data=serializer.data, message="列表获取成功")

    def destroy(self, request, *args, **kwargs):
        """软删除：标记 is_deleted=True 而非物理删除"""
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'updated_at'])
        return ApiResponse(message="删除成功")
```

### 5.24 `Apps/views/Example/urls.py`

```python
from rest_framework import routers
from Apps.views.Example.view import ExampleViewSet

router = routers.DefaultRouter()
router.register(r'examples', ExampleViewSet, basename='example')

urlpatterns = router.urls
```

### 5.25 `middleware/c_permission.py`

```python
from rest_framework.permissions import BasePermission
from models.models import User
from tools.token_tools import CustomTokenTool
from tools.auth_helpers import get_token_from_request


class IsTokenValid(BasePermission):
    """自定义权限：仅允许携带有效 Token 的请求访问"""
    message = "Token 无效或已过期"

    def has_permission(self, request, view):
        token = get_token_from_request(request)
        if not token:
            return False
        is_valid, user_id = CustomTokenTool.verify_token(token)
        if not is_valid or not user_id:
            return False
        try:
            request.user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return False
        return True
```

---

## 六、启动命令

> 下面的 `uivsbe_env` 可替换为任意虚拟环境名，`uivsbe_backend` 替换为你的 `{project}_backend`。

```bash
# 1. 创建虚拟环境
python -m venv uivsbe_env
uivsbe_env\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 配置 .env（按实际填写）
# POSTGRES_BUILDMART_HOST=localhost
# POSTGRES_DB=uivsbe
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=your_password
# POSTGRES_PORT=5432
# REDIS_BUILDMART_HOST=localhost
# REDIS_PORT=6389
# REDIS_BUILDMART_PASSWORD=
# REDIS_DB=0

# 4. 迁移
python manage.py makemigrations models
python manage.py migrate models

# 5. 启动
python manage.py runserver 8000

# 6. 访问文档
# Swagger UI: http://127.0.0.1:8000/api/docs/
# ReDoc:      http://127.0.0.1:8000/api/redoc/
```

---

## 七、接口清单

| 模块 | 端点 | 方法 | 说明 |
|------|------|------|------|
| 用户 | `/api/users/register/` | POST | 用户注册 |
| 用户 | `/api/users/login/` | POST | 用户登录 |
| 用户 | `/api/users/me/` | GET | 当前用户信息 |
| 用户 | `/api/users/logout/` | POST | 用户登出 |
| 用户-后台 | `/api/admin/users/` | CRUD | 用户管理 |
| 用户-后台 | `/api/admin/users/{id}/toggle-status/` | POST | 启用/禁用用户 |
| 管理员 | `/api/admin/register/` | POST | 管理员注册 |
| 管理员 | `/api/admin/login/` | POST | 管理员登录 |
| 管理员 | `/api/admin/info/` | GET | 获取管理员信息 |
| 管理员 | `/api/admin/logout/` | POST | 管理员登出 |
| 管理员 | `/api/admin/list/` | GET | 管理员列表 |
| 示例 | `/api/example/examples/` | CRUD | 示例管理 |

---

> 📝 生成时间: 2026-08-07
>
> **使用方法**: 将 `{project}` 全局替换为你的项目名（如 `myapp`），然后将所有代码交给 AI 生成即可。
>
> 🤖 本提示词基于实际项目代码提取，可完整复刻后端项目。项目名称不限，按需替换即可。
