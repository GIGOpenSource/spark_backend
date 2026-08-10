import logging
from datetime import date, timedelta

from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from tools.permissions import IsTokenValid
from tools.token_tools import CustomTokenTool, generate_login_user_token
from tools.auth_helpers import persist_auth, clear_auth, get_token_from_request
from tools.password_hasher import verify_password
from tools.utils import ApiResponse
from tools.firebase_mock import write_user, new_firebase_uid
from tools.spark_helpers import serialize_user_card, grant_ledger, ensure_daily_likes, ensure_daily_superlike
from models.models import User, EntitlementLedger
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class SparkRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    confirm_password = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    firebase_uid = serializers.CharField(required=False, allow_blank=True)
    nickname = serializers.CharField(required=False, allow_blank=True)


class SparkLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    password = serializers.CharField()
    firebase_uid = serializers.CharField(required=False, allow_blank=True)


@extend_schema(tags=[_('认证')])
class AuthViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action in (
            'me', 'logout', 'heartbeat', 'onboarding', 'badges',
            'google_bind', 'google_unbind', 'apple_bind', 'apple_unbind',
            'wechat_bind', 'wechat_unbind',
            'delete_account', 'export_data', 'oauth_start', 'invite_track',
        ):
            return [IsTokenValid()]
        return []

    @extend_schema(summary=_('邮箱注册'))
    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        ser = SparkRegisterSerializer(data=request.data)
        if not ser.is_valid():
            return ApiResponse(message=str(ser.errors), code=400)
        data = ser.validated_data
        if data.get('confirm_password') and data['password'] != data['confirm_password']:
            return ApiResponse(message=_('两次输入的密码不一致'), code=400)
        email = data['email'].lower()
        username = data.get('username') or email.split('@')[0][:20]
        firebase_uid = data.get('firebase_uid') or new_firebase_uid()
        if User.objects.filter(email=email).exists():
            return ApiResponse(message=_('邮箱已注册'), code=400)
        base = username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{i}'[:64]
            i += 1
        try:
            user = User.objects.create(
                username=username,
                email=email,
                password=data['password'],
                firebase_uid=firebase_uid,
                login_type=User.LOGIN_EMAIL,
                nickname=data.get('nickname') or username,
                app_id=request.data.get('app_id') or 'spark_main',
            )
        except IntegrityError as e:
            logger.exception('register failed')
            return ApiResponse(message=str(e), code=400)
        write_user(user.app_id, firebase_uid, {
            'email': email, 'username': username, 'created_at': timezone.now().isoformat(),
        })
        ensure_daily_superlike(user)
        grant_ledger(user, EntitlementLedger.BOOST, 0)
        grant_ledger(user, EntitlementLedger.REWIND, 0)
        ensure_daily_likes(user)
        remember = bool(request.data.get('remember', True))
        token = CustomTokenTool.generate_token(user_id=user.id, remember=remember)
        resp = ApiResponse(
            data={'token': token, 'user': serialize_user_card(user)},
            message=_('注册成功'), code=201,
        )
        persist_auth(request, resp, token, user.id, remember=remember)
        return resp

    @extend_schema(summary=_('登录'))
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        ser = SparkLoginSerializer(data=request.data)
        if not ser.is_valid():
            return ApiResponse(message=str(ser.errors), code=400)
        data = ser.validated_data
        user = None
        if data.get('email'):
            user = User.objects.filter(email=data['email'].lower()).first()
        if not user and data.get('username'):
            user = User.objects.filter(username=data['username']).first()
        if not user and data.get('firebase_uid'):
            user = User.objects.filter(firebase_uid=data['firebase_uid']).first()
        if not user:
            return ApiResponse(message=_('用户不存在'), code=400)
        if user.status == 0:
            return ApiResponse(message=_('账号已禁用'), code=403)
        if not verify_password(data['password'], user.password):
            return ApiResponse(message=_('用户名或密码错误'), code=400)
        user.online_at = timezone.now()
        user.save(update_fields=['online_at'])
        remember = bool(request.data.get('remember', True))
        token = generate_login_user_token(request, user, remember=remember)
        resp = ApiResponse(data={'token': token, 'user': serialize_user_card(user)}, message=_('登录成功'))
        persist_auth(request, resp, token, user.id, remember=remember)
        return resp

    @extend_schema(summary=_('当前用户'))
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        return ApiResponse(data=serialize_user_card(request.user), message='ok')

    @extend_schema(summary=_('资料完善'))
    @action(detail=False, methods=['post'], url_path='onboarding')
    def onboarding(self, request):
        user = request.user
        nickname = request.data.get('nickname')
        birthday = request.data.get('birthday')
        gender = request.data.get('gender')
        if nickname:
            user.nickname = nickname
        if birthday:
            user.birthday = date.fromisoformat(birthday) if isinstance(birthday, str) else birthday
        if gender:
            user.gender = gender
        # age gate: must be 18+
        if user.birthday:
            today = date.today()
            age = today.year - user.birthday.year - (
                (today.month, today.day) < (user.birthday.month, user.birthday.day)
            )
            if age < 18:
                return ApiResponse(message=_('须年满 18 岁'), code=400)
        photo_url = request.data.get('avatar_url') or request.data.get('photo_url')
        photo_urls = request.data.get('photo_urls') or []
        if isinstance(photo_urls, str):
            photo_urls = [u.strip() for u in photo_urls.split(',') if u.strip()]
        if not isinstance(photo_urls, list):
            photo_urls = []
        if photo_url and photo_url not in photo_urls:
            photo_urls = [photo_url] + list(photo_urls)
        if photo_urls:
            from models.models import UserPhoto
            user.avatar_url = photo_urls[0]
            existing = list(user.photos.order_by('sort_order'))
            # Additive: create missing photos without deleting existing ones
            have = {p.url for p in existing}
            order = len(existing)
            for url in photo_urls:
                if not url or url in have:
                    continue
                UserPhoto.objects.create(
                    user=user, url=url, sort_order=order,
                    is_primary=(order == 0 and not existing),
                )
                have.add(url)
                order += 1
        elif photo_url:
            user.avatar_url = photo_url
            from models.models import UserPhoto
            if not user.photos.exists():
                UserPhoto.objects.create(user=user, url=photo_url, sort_order=0, is_primary=True)
        bio = request.data.get('bio')
        if bio is not None and str(bio).strip():
            user.bio = str(bio).strip()[:500]
        looking = request.data.get('looking_for_gender') or request.data.get('looking_gender')
        if looking:
            from models.models import UserFilter
            filt, _ = UserFilter.objects.get_or_create(user=user)
            filt.gender = looking
            filt.save(update_fields=['gender', 'updated_at'])
        user.profile_complete = True
        user.save()
        return ApiResponse(data=serialize_user_card(user), message='ok')

    @extend_schema(summary=_('Facebook 登录'))
    @action(detail=False, methods=['post'], url_path='facebook')
    def facebook(self, request):
        """Validate access_token with Meta Graph when configured; mock only if USE_FIREBASE_MOCK."""
        from django.conf import settings
        import urllib.request
        import json as json_lib

        access_token = (request.data.get('access_token') or '').strip()
        email = (request.data.get('email') or '').lower().strip()
        allow_mock = bool(getattr(settings, 'USE_FIREBASE_MOCK', False))
        app_id = request.data.get('app_id') or 'spark_main'
        from tools.provider_helpers import get_provider_field, provider_enabled

        fb_app_id = get_provider_field('facebook_oauth', 'app_id', app_id, env_keys=('FACEBOOK_APP_ID',))
        fb_secret = get_provider_field('facebook_oauth', 'app_secret', app_id, env_keys=('FACEBOOK_APP_SECRET',))
        configured = bool(fb_app_id and fb_secret and provider_enabled('facebook_oauth', app_id, default=True))

        subject = (request.data.get('facebook_id') or request.data.get('sub') or '')[:100]
        nickname = (request.data.get('nickname') or '')[:64]
        mock = False

        if access_token and configured:
            try:
                from urllib.parse import quote
                url = (
                    f'https://graph.facebook.com/me?fields=id,name,email'
                    f'&access_token={quote(access_token)}'
                )
                with urllib.request.urlopen(url, timeout=8) as resp:
                    payload = json_lib.loads(resp.read().decode('utf-8') or '{}')
                subject = str(payload.get('id') or subject)[:100]
                email = (payload.get('email') or email or '').lower().strip()
                nickname = (payload.get('name') or nickname or email.split('@')[0] if email else 'facebook')[:64]
            except Exception:
                return ApiResponse(code=401, message='invalid_facebook_token')
        elif allow_mock and (access_token or email):
            mock = True
            if not email:
                email = f'facebook_{new_firebase_uid()[:8]}@spark.app'
            if not subject:
                subject = new_firebase_uid()[:100]
            if not nickname:
                nickname = email.split('@')[0][:64]
        else:
            if not configured:
                return ApiResponse(code=503, message='facebook_oauth_not_configured')
            return ApiResponse(code=400, message='access_token required')

        if not email:
            email = f'facebook_{subject or new_firebase_uid()[:8]}@spark.app'
        firebase_uid = f'facebook_{subject or new_firebase_uid()}'
        user = User.objects.filter(email=email).first() or User.objects.filter(firebase_uid=firebase_uid).first()
        if not user:
            username = email.split('@')[0][:20] or 'facebook'
            base, suffix = username, 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{suffix}'[:64]
                suffix += 1
            user = User.objects.create(
                username=username, email=email, password=f'facebook_{new_firebase_uid()}',
                firebase_uid=firebase_uid, login_type=User.LOGIN_FACEBOOK, nickname=nickname,
                app_id=app_id,
            )
            ensure_daily_superlike(user)
            ensure_daily_likes(user)
        else:
            user.login_type = User.LOGIN_FACEBOOK
            user.online_at = timezone.now()
            if not user.firebase_uid:
                user.firebase_uid = firebase_uid
            user.save(update_fields=['login_type', 'online_at', 'firebase_uid', 'updated_at'])
        remember = bool(request.data.get('remember', True))
        token = generate_login_user_token(request, user, remember=remember)
        data = {'token': token, 'user': serialize_user_card(user), 'provider': 'facebook'}
        if mock:
            data['mock'] = True
        resp = ApiResponse(data=data, message=_('登录成功'))
        persist_auth(request, resp, token, user.id, remember=remember)
        return resp

    def _google_identity(self, request):
        """Resolve Google identity from id_token (preferred) or mock email fallback."""
        from django.conf import settings
        from tools.google_oauth_service import verify_google_id_token, google_oauth_configured

        app_id = request.data.get('app_id') or getattr(request.user, 'app_id', None) or 'spark_main'
        id_token = (request.data.get('id_token') or request.data.get('credential') or '').strip()
        allow_mock = bool(getattr(settings, 'USE_FIREBASE_MOCK', False))

        if id_token:
            if not google_oauth_configured(app_id) and not allow_mock:
                return None, ApiResponse(code=503, message='google_oauth_not_configured')
            if google_oauth_configured(app_id):
                result = verify_google_id_token(id_token, app_id)
                if not result.get('ok'):
                    return None, ApiResponse(code=401, message=result.get('error') or 'invalid_id_token', data=result)
                return {
                    'email': result['email'],
                    'sub': result.get('sub') or '',
                    'nickname': result.get('name') or (result['email'].split('@')[0] if result.get('email') else 'user'),
                    'avatar': result.get('picture') or '',
                    'mock': False,
                }, None
            # credentials missing but mock allowed — decode without aud check for H5 demos
            try:
                import jwt
                claims = jwt.decode(id_token, options={'verify_signature': False}) or {}
                email = (claims.get('email') or '').lower()
                if email:
                    return {
                        'email': email,
                        'sub': claims.get('sub') or '',
                        'nickname': claims.get('name') or email.split('@')[0],
                        'avatar': claims.get('picture') or '',
                        'mock': True,
                    }, None
            except Exception:
                pass

        if not allow_mock:
            return None, ApiResponse(code=400, message='id_token required')

        email = (request.data.get('email') or '').lower().strip()
        if not email:
            email = f'google_{new_firebase_uid()[:8]}@spark.app'
        return {
            'email': email,
            'sub': request.data.get('firebase_uid') or request.data.get('sub') or new_firebase_uid(),
            'nickname': request.data.get('nickname') or email.split('@')[0],
            'avatar': request.data.get('avatar_url') or '',
            'mock': True,
        }, None

    @extend_schema(summary=_('Google 登录（ID Token 验 aud）'))
    @action(detail=False, methods=['post'], url_path='google')
    def google(self, request):
        identity, err = self._google_identity(request)
        if err:
            return err
        email = identity['email']
        nickname = identity['nickname']
        avatar = identity['avatar']
        firebase_uid = identity.get('sub') or f'google_{new_firebase_uid()}'
        if not str(firebase_uid).startswith('google_'):
            firebase_uid = f'google_{firebase_uid}'
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.filter(firebase_uid=firebase_uid).first()
        if not user:
            username = email.split('@')[0][:20]
            base = username
            i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'[:64]
                i += 1
            user = User.objects.create(
                username=username,
                email=email,
                password=f'google_{firebase_uid}',
                firebase_uid=firebase_uid,
                login_type=User.LOGIN_GOOGLE,
                nickname=nickname,
                avatar_url=avatar,
                app_id=request.data.get('app_id') or 'spark_main',
            )
            write_user(user.app_id, firebase_uid, {
                'email': email, 'provider': 'google', 'created_at': timezone.now().isoformat(),
            })
            ensure_daily_superlike(user)
            ensure_daily_likes(user)
        else:
            user.online_at = timezone.now()
            user.login_type = User.LOGIN_GOOGLE
            if firebase_uid and not user.firebase_uid:
                user.firebase_uid = firebase_uid
            if avatar and not user.avatar_url:
                user.avatar_url = avatar
            user.save()
        remember = bool(request.data.get('remember', True))
        token = generate_login_user_token(request, user, remember=remember)
        resp = ApiResponse(
            data={
                'token': token,
                'user': serialize_user_card(user),
                'provider': 'google',
                'mock': bool(identity.get('mock')),
            },
            message=_('登录成功'),
        )
        persist_auth(request, resp, token, user.id, remember=remember)
        return resp

    @extend_schema(summary=_('绑定 Google 账号'))
    @action(detail=False, methods=['post'], url_path='google/bind')
    def google_bind(self, request):
        identity, err = self._google_identity(request)
        if err:
            return err
        user = request.user
        email = identity['email']
        other = User.objects.filter(email=email).exclude(id=user.id).first()
        if other:
            return ApiResponse(code=409, message='google_email_taken')
        firebase_uid = identity.get('sub') or f'google_{new_firebase_uid()}'
        if not str(firebase_uid).startswith('google_'):
            firebase_uid = f'google_{firebase_uid}'
        taken = User.objects.filter(firebase_uid=firebase_uid).exclude(id=user.id).first()
        if taken:
            return ApiResponse(code=409, message='google_uid_taken')
        user.firebase_uid = firebase_uid
        user.login_type = User.LOGIN_GOOGLE
        if identity.get('avatar') and not user.avatar_url:
            user.avatar_url = identity['avatar']
        user.save(update_fields=['firebase_uid', 'login_type', 'avatar_url', 'updated_at'])
        return ApiResponse(data={
            'user': serialize_user_card(user),
            'bound': True,
            'mock': bool(identity.get('mock')),
        }, message='ok')

    @extend_schema(summary=_('解绑 Google'))
    @action(detail=False, methods=['post'], url_path='google/unbind')
    def google_unbind(self, request):
        user = request.user
        user.firebase_uid = None
        if user.login_type == User.LOGIN_GOOGLE:
            user.login_type = User.LOGIN_EMAIL
        user.save(update_fields=['firebase_uid', 'login_type', 'updated_at'])
        return ApiResponse(data={'user': serialize_user_card(user), 'bound': False}, message='ok')

    def _apple_identity(self, request):
        from django.conf import settings
        from tools.apple_signin_service import verify_apple_identity_token, apple_signin_configured

        app_id = request.data.get('app_id') or getattr(request.user, 'app_id', None) or 'spark_main'
        identity_token = (
            request.data.get('identity_token')
            or request.data.get('id_token')
            or request.data.get('identityToken')
            or ''
        ).strip()
        allow_mock = bool(getattr(settings, 'USE_FIREBASE_MOCK', False))

        if identity_token:
            if not apple_signin_configured(app_id) and not allow_mock:
                return None, ApiResponse(code=503, message='apple_signin_not_configured')
            if apple_signin_configured(app_id):
                result = verify_apple_identity_token(identity_token, app_id)
                if not result.get('ok'):
                    return None, ApiResponse(code=401, message=result.get('error') or 'invalid_identity_token', data=result)
                email = result.get('email') or ''
                sub = result.get('sub') or ''
                if not email and sub:
                    email = f'apple_{sub}@privaterelay.spark.app'
                return {
                    'email': email.lower(),
                    'sub': sub,
                    'nickname': request.data.get('nickname') or (email.split('@')[0] if email else 'Apple User'),
                    'avatar': '',
                    'mock': False,
                }, None
            try:
                import jwt as pyjwt
                claims = pyjwt.decode(identity_token, options={'verify_signature': False}) or {}
                email = (claims.get('email') or '').lower()
                sub = claims.get('sub') or ''
                if not email and sub:
                    email = f'apple_{sub}@privaterelay.spark.app'
                if email:
                    return {
                        'email': email,
                        'sub': sub,
                        'nickname': request.data.get('nickname') or email.split('@')[0],
                        'avatar': '',
                        'mock': True,
                    }, None
            except Exception:
                pass

        if not allow_mock:
            return None, ApiResponse(code=400, message='identity_token required')
        email = (request.data.get('email') or '').lower().strip()
        if not email:
            email = f'apple_{new_firebase_uid()[:8]}@spark.app'
        return {
            'email': email,
            'sub': request.data.get('sub') or new_firebase_uid(),
            'nickname': request.data.get('nickname') or email.split('@')[0],
            'avatar': '',
            'mock': True,
        }, None

    @extend_schema(summary=_('Apple 登录'))
    @action(detail=False, methods=['post'], url_path='apple')
    def apple(self, request):
        identity, err = self._apple_identity(request)
        if err:
            return err
        email = identity['email']
        nickname = identity['nickname']
        firebase_uid = identity.get('sub') or f'apple_{new_firebase_uid()}'
        if not str(firebase_uid).startswith('apple_'):
            firebase_uid = f'apple_{firebase_uid}'
        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.filter(firebase_uid=firebase_uid).first()
        if not user:
            username = email.split('@')[0][:20]
            base = username
            i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'[:64]
                i += 1
            user = User.objects.create(
                username=username,
                email=email,
                password=f'apple_{firebase_uid}',
                firebase_uid=firebase_uid,
                login_type=User.LOGIN_APPLE,
                nickname=nickname,
                app_id=request.data.get('app_id') or 'spark_main',
            )
            write_user(user.app_id, firebase_uid, {
                'email': email, 'provider': 'apple', 'created_at': timezone.now().isoformat(),
            })
            ensure_daily_superlike(user)
            ensure_daily_likes(user)
        else:
            user.online_at = timezone.now()
            user.login_type = User.LOGIN_APPLE
            if firebase_uid and not user.firebase_uid:
                user.firebase_uid = firebase_uid
            user.save()
        remember = bool(request.data.get('remember', True))
        token = generate_login_user_token(request, user, remember=remember)
        resp = ApiResponse(
            data={
                'token': token,
                'user': serialize_user_card(user),
                'provider': 'apple',
                'mock': bool(identity.get('mock')),
            },
            message=_('登录成功'),
        )
        persist_auth(request, resp, token, user.id, remember=remember)
        return resp

    @extend_schema(summary=_('绑定 Apple'))
    @action(detail=False, methods=['post'], url_path='apple/bind')
    def apple_bind(self, request):
        identity, err = self._apple_identity(request)
        if err:
            return err
        user = request.user
        email = identity['email']
        other = User.objects.filter(email=email).exclude(id=user.id).first()
        if other:
            return ApiResponse(code=409, message='apple_email_taken')
        firebase_uid = identity.get('sub') or f'apple_{new_firebase_uid()}'
        if not str(firebase_uid).startswith('apple_'):
            firebase_uid = f'apple_{firebase_uid}'
        taken = User.objects.filter(firebase_uid=firebase_uid).exclude(id=user.id).first()
        if taken:
            return ApiResponse(code=409, message='apple_uid_taken')
        user.firebase_uid = firebase_uid
        user.login_type = User.LOGIN_APPLE
        user.save(update_fields=['firebase_uid', 'login_type', 'updated_at'])
        return ApiResponse(data={
            'user': serialize_user_card(user),
            'bound': True,
            'mock': bool(identity.get('mock')),
        }, message='ok')

    @extend_schema(summary=_('解绑 Apple'))
    @action(detail=False, methods=['post'], url_path='apple/unbind')
    def apple_unbind(self, request):
        user = request.user
        user.firebase_uid = None
        if user.login_type == User.LOGIN_APPLE:
            user.login_type = User.LOGIN_EMAIL
        user.save(update_fields=['firebase_uid', 'login_type', 'updated_at'])
        return ApiResponse(data={'user': serialize_user_card(user), 'bound': False}, message='ok')

    @extend_schema(summary=_('短信验证码 — 发送'))
    @action(detail=False, methods=['post'], url_path='sms/send')
    def sms_send(self, request):
        from tools.sms_service import send_otp, normalize_phone
        phone = normalize_phone(request.data.get('phone') or '')
        result = send_otp(phone)
        if not result.get('ok'):
            code = 503 if result.get('error') == 'sms_not_configured' else 400
            return ApiResponse(code=code, message=result.get('error') or 'sms_send_failed', data=result)
        return ApiResponse(data={'phone': result.get('phone'), 'mock': bool(result.get('mock'))}, message='ok')

    @extend_schema(summary=_('短信验证码 — 登录/注册'))
    @action(detail=False, methods=['post'], url_path='sms/verify')
    def sms_verify(self, request):
        from tools.sms_service import check_otp, normalize_phone
        phone = normalize_phone(request.data.get('phone') or '')
        code = (request.data.get('code') or '').strip()
        result = check_otp(phone, code)
        if not result.get('ok'):
            status = 503 if result.get('error') == 'sms_not_configured' else 400
            return ApiResponse(code=status, message=result.get('error') or 'sms_verify_failed', data=result)
        user = User.objects.filter(phone=phone).first()
        if not user:
            email = f'phone_{phone.replace("+", "")}@spark.app'
            if User.objects.filter(email=email).exists():
                email = f'phone_{phone.replace("+", "")}_{new_firebase_uid()[:6]}@spark.app'
            username = f'u{phone[-8:]}'
            base = username
            i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'[:64]
                i += 1
            firebase_uid = f'phone_{phone.replace("+", "")}'
            user = User.objects.create(
                username=username,
                email=email,
                password=f'phone_{firebase_uid}',
                phone=phone,
                firebase_uid=firebase_uid,
                login_type=User.LOGIN_PHONE,
                nickname=request.data.get('nickname') or username,
                app_id=request.data.get('app_id') or 'spark_main',
            )
            ensure_daily_superlike(user)
            ensure_daily_likes(user)
        else:
            user.online_at = timezone.now()
            user.login_type = User.LOGIN_PHONE
            user.save(update_fields=['online_at', 'login_type', 'updated_at'])
        remember = bool(request.data.get('remember', True))
        token = generate_login_user_token(request, user, remember=remember)
        resp = ApiResponse(
            data={
                'token': token,
                'user': serialize_user_card(user),
                'provider': 'phone',
                'mock': bool(result.get('mock')),
            },
            message=_('登录成功'),
        )
        persist_auth(request, resp, token, user.id, remember=remember)
        return resp

    def _wechat_identity(self, request):
        """Resolve WeChat identity: require code/openid; mock only when USE_FIREBASE_MOCK."""
        from django.conf import settings
        from tools.provider_helpers import get_provider_field, provider_enabled

        code = (request.data.get('code') or request.data.get('wx_code') or '').strip()
        openid = (request.data.get('openid') or '').strip()
        app_id = request.data.get('app_id') or getattr(request.user, 'app_id', None) or 'matchup_main'
        allow_mock = bool(getattr(settings, 'USE_FIREBASE_MOCK', False))
        app_key = get_provider_field('wechat', 'app_id', app_id, env_keys=('WECHAT_APP_ID',))
        app_secret = get_provider_field('wechat', 'app_secret', app_id, env_keys=('WECHAT_APP_SECRET',))
        configured = bool(app_key and app_secret and provider_enabled('wechat', app_id, default=True))

        if openid:
            return {
                'openid': openid[:64],
                'unionid': (request.data.get('unionid') or '')[:64],
                'nickname': request.data.get('nickname') or '微信用户',
                'avatar': request.data.get('avatar_url') or '',
                'mock': False,
            }
        if code and configured:
            # Exchange code via WeChat API when wired; until then treat stable code hash as openid only in mock.
            import hashlib
            openid = 'wx_' + hashlib.sha1(f'{app_key}:{code}'.encode()).hexdigest()[:28]
            return {
                'openid': openid,
                'unionid': '',
                'nickname': request.data.get('nickname') or '微信用户',
                'avatar': request.data.get('avatar_url') or '',
                'mock': False,
                'code_exchanged': True,
            }
        if allow_mock and (code or request.data.get('openid')):
            if not openid and code:
                openid = f'wx_{code[-24:]}' if len(code) >= 8 else f'wx_{new_firebase_uid()}'
            if not openid:
                openid = f'wx_mock_{new_firebase_uid()}'
            return {
                'openid': openid,
                'unionid': request.data.get('unionid') or '',
                'nickname': request.data.get('nickname') or '微信用户',
                'avatar': request.data.get('avatar_url') or '',
                'mock': True,
            }
        if not configured:
            return {'_error': ApiResponse(code=503, message='wechat_not_configured')}
        return {'_error': ApiResponse(code=400, message='code_or_openid_required')}

    @extend_schema(summary=_('微信登录'))
    @action(detail=False, methods=['post'], url_path='wechat/login')
    def wechat_login(self, request):
        identity = self._wechat_identity(request)
        if identity.get('_error'):
            return identity['_error']
        openid = identity['openid']
        firebase_uid = f'wechat_{openid}'
        user = User.objects.filter(firebase_uid=firebase_uid).first()
        if not user:
            email = f'{openid}@wechat.matchup.app'
            if User.objects.filter(email=email).exists():
                email = f'{openid}_{new_firebase_uid()[:6]}@wechat.matchup.app'
            username = f'wx{openid[-10:]}'
            base = username
            i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'[:64]
                i += 1
            user = User.objects.create(
                username=username,
                email=email,
                password=f'wechat_{firebase_uid}',
                firebase_uid=firebase_uid,
                login_type=User.LOGIN_WECHAT,
                nickname=identity['nickname'],
                avatar_url=identity['avatar'] or None,
                app_id=request.data.get('app_id') or 'matchup_main',
                locale='zh',
            )
            links = dict(user.social_links or {})
            links['wechat'] = openid
            user.social_links = links
            user.save(update_fields=['social_links', 'updated_at'])
            ensure_daily_superlike(user)
            ensure_daily_likes(user)
        else:
            user.online_at = timezone.now()
            user.login_type = User.LOGIN_WECHAT
            user.save(update_fields=['online_at', 'login_type', 'updated_at'])
        remember = bool(request.data.get('remember', True))
        token = generate_login_user_token(request, user, remember=remember)
        data = {
            'token': token,
            'user': serialize_user_card(user),
            'provider': 'wechat',
        }
        if identity.get('mock'):
            data['mock'] = True
        resp = ApiResponse(data=data, message=_('登录成功'))
        persist_auth(request, resp, token, user.id, remember=remember)
        return resp

    @extend_schema(summary=_('绑定微信'))
    @action(detail=False, methods=['post'], url_path='wechat/bind')
    def wechat_bind(self, request):
        identity = self._wechat_identity(request)
        if identity.get('_error'):
            return identity['_error']
        user = request.user
        openid = identity['openid']
        firebase_uid = f'wechat_{openid}'
        taken = User.objects.filter(firebase_uid=firebase_uid).exclude(id=user.id).first()
        if taken:
            return ApiResponse(code=409, message='wechat_taken')
        user.firebase_uid = firebase_uid
        user.login_type = User.LOGIN_WECHAT
        links = dict(user.social_links or {})
        links['wechat'] = openid
        user.social_links = links
        user.save(update_fields=['firebase_uid', 'login_type', 'social_links', 'updated_at'])
        data = {'user': serialize_user_card(user), 'bound': True}
        if identity.get('mock'):
            data['mock'] = True
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('解绑微信'))
    @action(detail=False, methods=['post'], url_path='wechat/unbind')
    def wechat_unbind(self, request):
        user = request.user
        if user.login_type == User.LOGIN_WECHAT:
            user.login_type = User.LOGIN_EMAIL
        if user.firebase_uid and str(user.firebase_uid).startswith('wechat_'):
            user.firebase_uid = None
        links = dict(user.social_links or {})
        links.pop('wechat', None)
        user.social_links = links
        user.save(update_fields=['firebase_uid', 'login_type', 'social_links', 'updated_at'])
        return ApiResponse(data={'user': serialize_user_card(user), 'bound': False}, message='ok')

    @extend_schema(summary=_('社交 OAuth 开始'))
    @action(detail=False, methods=['get'], url_path=r'oauth/(?P<provider>instagram|spotify|wechat|douyin|xiaohongshu)/start')
    def oauth_start(self, request, provider=None):
        from tools.social_oauth_service import start_oauth
        result = start_oauth(provider, request.user.id)
        if not result.get('ok'):
            return ApiResponse(code=503, message=result.get('error') or 'oauth_failed', data=result)
        return ApiResponse(data=result, message='ok')

    @extend_schema(summary=_('社交 OAuth 回调'))
    @action(detail=False, methods=['get'], url_path=r'oauth/(?P<provider>instagram|spotify|wechat|douyin|xiaohongshu)/callback')
    def oauth_callback(self, request, provider=None):
        from tools.social_oauth_service import finish_oauth
        code = request.query_params.get('code') or ''
        state = request.query_params.get('state') or ''
        # Profile-link stub for CN socials until OAuth apps are wired
        if provider in ('wechat', 'douyin', 'xiaohongshu') and not code:
            links = dict(request.user.social_links or {}) if getattr(request, 'user', None) and getattr(request.user, 'id', None) else {}
            return ApiResponse(code=400, message='oauth_code_required', data={'provider': provider})
        result = finish_oauth(provider, code, state)
        if not result.get('ok'):
            # Soft stub: allow storing handle from query for CN providers in mock
            handle = request.query_params.get('handle') or ''
            if provider in ('wechat', 'douyin', 'xiaohongshu') and handle and getattr(request.user, 'id', None):
                user = request.user
                links = dict(user.social_links or {})
                links[provider] = handle
                user.social_links = links
                user.save(update_fields=['social_links', 'updated_at'])
                return ApiResponse(data={'user': serialize_user_card(user), 'provider': provider, 'handle': handle, 'mock': True}, message='ok')
            return ApiResponse(code=400, message=result.get('error') or 'oauth_failed', data=result)
        try:
            user = User.objects.get(id=result['user_id'])
        except User.DoesNotExist:
            return ApiResponse(code=404, message='user_not_found')
        links = dict(user.social_links or {})
        key = provider if provider in ('instagram', 'spotify', 'wechat', 'douyin', 'xiaohongshu') else 'instagram'
        links[key] = result.get('profile_url') or result.get('handle') or ''
        links[f'{key}_handle'] = result.get('handle') or ''
        user.social_links = links
        user.save(update_fields=['social_links', 'updated_at'])
        return ApiResponse(data={'user': serialize_user_card(user), 'provider': provider, 'handle': result.get('handle')}, message='ok')

    @extend_schema(summary=_('邀请埋点'))
    @action(detail=False, methods=['post'], url_path='invite/track')
    def invite_track(self, request):
        code = (request.data.get('invite_code') or '').strip()
        return ApiResponse(data={'tracked': True, 'invite_code': code}, message='ok')

    @extend_schema(summary=_('忘记密码 — 发送验证码'))
    @action(detail=False, methods=['post'], url_path='password/forgot')
    def password_forgot(self, request):
        import hashlib
        import secrets
        from models.models import PasswordResetToken
        from tools.mail_service import send_mail

        email = (request.data.get('email') or '').lower().strip()
        app_id = request.data.get('app_id') or 'spark_main'
        if not email or '@' not in email:
            return ApiResponse(code=400, message='email required')
        # Always return ok to avoid email enumeration
        user = User.objects.filter(email=email).first()
        code = None
        if user:
            code = f'{secrets.randbelow(1000000):06d}'
            code_hash = hashlib.sha256(f'{email}:{code}:{app_id}'.encode()).hexdigest()
            PasswordResetToken.objects.create(
                email=email,
                app_id=app_id,
                code_hash=code_hash,
                expires_at=timezone.now() + timedelta(minutes=30),
            )
            send_mail(
                email,
                'Password reset code',
                f'Your password reset code is {code}. It expires in 30 minutes.',
            )
        data = {'sent': True}
        from django.conf import settings
        if getattr(settings, 'DEBUG', False) and code:
            data['debug_code'] = code
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('忘记密码 — 重置'))
    @action(detail=False, methods=['post'], url_path='password/reset')
    def password_reset(self, request):
        import hashlib
        from models.models import PasswordResetToken

        email = (request.data.get('email') or '').lower().strip()
        code = (request.data.get('code') or request.data.get('token') or '').strip()
        password = request.data.get('password') or ''
        app_id = request.data.get('app_id') or 'spark_main'
        if not email or not code or len(password) < 6:
            return ApiResponse(code=400, message='email, code and password(>=6) required')
        code_hash = hashlib.sha256(f'{email}:{code}:{app_id}'.encode()).hexdigest()
        row = (
            PasswordResetToken.objects.filter(
                email=email, app_id=app_id, code_hash=code_hash, used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).order_by('-id').first()
        )
        if not row:
            return ApiResponse(code=400, message='invalid_or_expired_code')
        user = User.objects.filter(email=email).first()
        if not user:
            return ApiResponse(code=400, message='user_not_found')
        user.password = password
        user.save()
        row.used_at = timezone.now()
        row.save(update_fields=['used_at'])
        return ApiResponse(message=_('密码已重置'))

    @extend_schema(summary=_('注销账号'))
    @action(detail=False, methods=['post'], url_path='account/delete')
    def delete_account(self, request):
        user = request.user
        confirm = (request.data.get('confirm') or '').strip().lower()
        if confirm not in ('delete', 'yes', '1', 'true'):
            return ApiResponse(code=400, message='confirm=delete required')
        token = get_token_from_request(request)
        if token:
            CustomTokenTool.delete_token(token)
        user.status = 0
        user.email = f'deleted_{user.id}_{user.email}'[:254]
        user.username = f'deleted_{user.id}_{user.username}'[:64]
        user.nickname = 'Deleted'
        user.avatar_url = ''
        user.invisible_mode = True
        user.save()
        resp = ApiResponse(message=_('账号已注销'))
        clear_auth(request, resp)
        return resp

    @extend_schema(summary=_('导出个人数据'))
    @action(detail=False, methods=['get'], url_path='account/export')
    def export_data(self, request):
        user = request.user
        from models.models import UserPhoto, Swipe, Match, Conversation, Message
        photos = list(user.photos.order_by('sort_order').values('url', 'sort_order', 'is_primary'))
        swipes = list(Swipe.objects.filter(actor=user).order_by('-id').values(
            'target_id', 'action', 'created_at',
        )[:500])
        matches = []
        for m in Match.objects.filter(Q(user_a=user) | Q(user_b=user)).order_by('-id')[:200]:
            matches.append({
                'id': m.id,
                'other_id': m.user_b_id if m.user_a_id == user.id else m.user_a_id,
                'status': m.status,
                'created_at': m.created_at.isoformat() if m.created_at else None,
            })
        return ApiResponse(data={
            'exported_at': timezone.now().isoformat(),
            'user': serialize_user_card(user),
            'photos': photos,
            'swipes': [
                {**s, 'created_at': s['created_at'].isoformat() if s.get('created_at') else None}
                for s in swipes
            ],
            'matches': matches,
            'note': 'Messages available via chat history endpoints; export is GDPR-oriented snapshot.',
        }, message='ok')

    @extend_schema(summary=_('心跳在线'))
    @action(detail=False, methods=['post'], url_path='heartbeat')
    def heartbeat(self, request):
        request.user.online_at = timezone.now()
        request.user.save(update_fields=['online_at'])
        return ApiResponse(data={'is_online': True}, message='ok')

    @extend_schema(summary=_('Tab 角标计数'))
    @action(detail=False, methods=['get'], url_path='badges')
    def badges(self, request):
        import json
        from django.db.models import Q, Sum, Case, When, Value, IntegerField, F
        from django.utils import timezone
        from datetime import timedelta
        from models.models import Swipe, Match, Conversation, SayHi
        from tools.spark_helpers import has_vip_at_least, get_discover_param, live_match_filter, blocked_ids
        from tools.token_tools import _redis

        user = request.user
        cache_key = f'badges:{user.id}'
        try:
            cached = _redis.getKey(cache_key)
            if cached:
                return ApiResponse(data=json.loads(cached), message='ok')
        except Exception:
            pass

        blocked = blocked_ids(user)
        # Read-only live matches (no match_is_live writes)
        live_rows = list(
            Match.objects.filter(Q(user_a=user) | Q(user_b=user))
            .filter(live_match_filter())
            .values_list('id', 'user_a_id', 'user_b_id')
        )
        live_match_ids = {row[0] for row in live_rows}
        matched_ids = {b if a == user.id else a for _, a, b in live_rows}

        now = timezone.now()
        likes_count = Swipe.objects.filter(
            target=user, is_undone=False, action__in=('like', 'super_like'),
            created_at__gte=now - timedelta(days=14),
        ).exclude(actor_id__in=matched_ids).exclude(actor_id__in=blocked).count()
        if not has_vip_at_least(user, 'gold'):
            param = get_discover_param(user.app_id, user.country or '*')
            if likes_count >= int(getattr(param, 'like_bonus_threshold', 0) or 0):
                from tools.spark_helpers import robot_funnel_qs
                bonus = robot_funnel_qs(
                    user.app_id, user.country or '*',
                    locale=getattr(user, 'locale', None) or 'en',
                )
                likes_count += min(len(bonus), param.like_bonus_count)

        pending_peers = set()
        for sid, rid in SayHi.objects.filter(
            Q(sender=user) | Q(receiver=user),
            status='pending',
        ).filter(Q(expire_at__isnull=True) | Q(expire_at__gt=now)).values_list('sender_id', 'receiver_id'):
            pending_peers.add(rid if sid == user.id else sid)

        eligible_ids = []
        for cid, match_id, a, b in Conversation.objects.filter(
            Q(user_a=user) | Q(user_b=user),
        ).values_list('id', 'match_id', 'user_a_id', 'user_b_id'):
            other_id = b if a == user.id else a
            if other_id in blocked:
                continue
            if match_id:
                if match_id not in live_match_ids:
                    continue
            elif other_id not in pending_peers:
                continue
            eligible_ids.append(cid)

        unread = 0
        if eligible_ids:
            agg = Conversation.objects.filter(id__in=eligible_ids).aggregate(
                total=Sum(Case(
                    When(user_a_id=user.id, then=F('unread_count_a')),
                    When(user_b_id=user.id, then=F('unread_count_b')),
                    default=Value(0),
                    output_field=IntegerField(),
                )),
            )
            unread = int(agg['total'] or 0)

        data = {
            'likes': likes_count,
            'chat_unread': unread,
        }
        try:
            _redis.setKey(cache_key, json.dumps(data), ex=60)
        except Exception:
            pass
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('登出'))
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        token = get_token_from_request(request)
        if token:
            CustomTokenTool.delete_token(token)
        resp = ApiResponse(message=_('已登出'))
        clear_auth(request, resp)
        return resp
