#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from django.db import IntegrityError
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view

from tools.permissions import IsTokenValid, IsAdmin
from tools.token_tools import CustomTokenTool, generate_login_user_token
from tools.auth_helpers import persist_auth, clear_auth, get_token_from_request
from models.models import User, AdminRolePermission
from tools.password_hasher import verify_password
from tools.utils import ApiResponse, CustomPagination
from tools.admin_rbac import (
    ROLE_DEFS, ALL_PERMISSIONS, ADMIN_ROLE_KEYS, KNOWN_APPS,
    effective_permissions, load_role_overrides, get_role_permissions,
    accessible_app_ids, can_access_app, concrete_app_id, is_all_app,
)
from django.utils.translation import gettext as _
from Apps.views.admin.serializers import (
    AdminRegisterSerializer,
    AdminLoginSerializer,
    AdminUserSerializer,
)


@extend_schema(tags=[_("管理员管理")])
@extend_schema_view(
    list=extend_schema(summary=_('获取管理员列表')),
)
class AdminViewSet(viewsets.ViewSet):
    """管理员登录注册与 RBAC 视图"""
    permission_classes_by_action = {
        'register': [],
        'login': [],
        'list': [IsTokenValid, IsAdmin],
        'info': [IsTokenValid, IsAdmin],
        'members': [IsTokenValid, IsAdmin],
        'toggle_member': [IsTokenValid, IsAdmin],
        'roles': [IsTokenValid, IsAdmin],
    }

    def get_permissions(self):
        return [perm() for perm in self.permission_classes_by_action.get(self.action, [])]

    @extend_schema(
        request=AdminRegisterSerializer,
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
        apps = accessible_app_ids(user)
        app_id = apps[0] if apps else 'spark_main'
        overrides = load_role_overrides(app_id)
        response = ApiResponse(
            data={
                "token": token,
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "permissions": effective_permissions(user, app_id=app_id, overrides=overrides),
                "admin_app_ids": apps,
                "app_id": app_id,
                "apps": KNOWN_APPS,
            },
            message=_('注册成功'),
            code=201
        )
        persist_auth(request, response, token, user.id, remember=remember)
        return response

    @extend_schema(request=AdminLoginSerializer, summary=_("管理员登录"))
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return ApiResponse(message=_('用户名和密码不能为空'), code=400)

        user = User.objects.filter(username=username).first()
        if not user and '@' in str(username):
            user = User.objects.filter(email__iexact=username).first()
        if not user:
            return ApiResponse(message=_('用户名不存在'), code=400)

        if user.role not in ADMIN_ROLE_KEYS:
            return ApiResponse(message=_('该账号不是管理员账号'), code=403)

        if user.status == 0:
            return ApiResponse(message=_('该账号已被禁用'), code=403)

        if verify_password(password, user.password):
            remember = bool(request.data.get('remember'))
            token = generate_login_user_token(request, user, remember=remember)
            apps = accessible_app_ids(user)
            app_id = request.data.get('app_id') or (apps[0] if apps else 'spark_main')
            if not can_access_app(user, app_id):
                app_id = apps[0] if apps else 'spark_main'
            overrides = load_role_overrides(app_id)
            response = ApiResponse(
                data={
                    "token": token,
                    "user_id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "permissions": effective_permissions(user, app_id=app_id, overrides=overrides),
                    "admin_app_ids": apps,
                    "app_id": app_id,
                    "apps": [a for a in KNOWN_APPS if a['app_id'] in apps],
                },
                message=_('登录成功')
            )
            persist_auth(request, response, token, user.id, remember=remember)
            return response
        return ApiResponse(message=_('用户名或密码错误'), code=400)

    @extend_schema(responses={200: AdminUserSerializer}, summary=_("获取当前管理员信息"))
    @action(detail=False, methods=['get'], url_path='info')
    def info(self, request):
        token = get_token_from_request(request)
        is_valid, user_id = CustomTokenTool.verify_token(token)

        if not is_valid:
            return ApiResponse(message=_('Token无效或已过期'), code=401)

        try:
            user = User.objects.get(id=user_id)
            apps = accessible_app_ids(user)
            app_id = request.query_params.get('app_id') or (apps[0] if apps else 'spark_main')
            if not can_access_app(user, app_id):
                return ApiResponse(message=_('无权访问该 App'), code=403)
            app_id = concrete_app_id(user, app_id)
            data = AdminUserSerializer(user).data
            overrides = load_role_overrides(app_id)
            data['permissions'] = effective_permissions(user, app_id=app_id, overrides=overrides)
            data['admin_app_ids'] = apps
            data['app_id'] = app_id
            data['apps'] = [a for a in KNOWN_APPS if a['app_id'] in apps]
            return ApiResponse(data=data)
        except User.DoesNotExist:
            return ApiResponse(message=_('用户不存在'), code=404)

    @extend_schema(summary=_("管理员登出"))
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        token = get_token_from_request(request)
        if token:
            CustomTokenTool.delete_token(token)
        response = ApiResponse(message=_("登出成功，Token 已失效"))
        return clear_auth(request, response)

    def list(self, request):
        admins = User.objects.filter(role__in=ADMIN_ROLE_KEYS).order_by('-created_at')
        paginator = CustomPagination()
        page = paginator.paginate_queryset(admins, request)
        if page is not None:
            serializer = AdminUserSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = AdminUserSerializer(admins, many=True)
        return ApiResponse(data=serializer.data)

    @extend_schema(summary=_('管理员成员列表 / 创建更新'))
    @action(detail=False, methods=['get', 'post'], url_path='members')
    def members(self, request):
        if request.method == 'GET':
            admins = User.objects.filter(role__in=ADMIN_ROLE_KEYS).order_by('-created_at')
            serializer = AdminUserSerializer(admins, many=True)
            return ApiResponse(data=serializer.data)

        actor = request.user
        if actor.role != 'super_admin':
            return ApiResponse(message=_('仅超管可管理成员'), code=403)

        mid = request.data.get('id')
        username = (request.data.get('username') or '').strip()
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password') or ''
        role = request.data.get('role') or 'operator'
        admin_app_ids = request.data.get('admin_app_ids') or []

        if role not in ADMIN_ROLE_KEYS:
            return ApiResponse(message=_('无效角色'), code=400)
        if role == 'super_admin' and actor.role != 'super_admin':
            return ApiResponse(message=_('不可分配超管角色'), code=403)

        if mid:
            user = User.objects.filter(id=mid, role__in=ADMIN_ROLE_KEYS).first()
            if not user:
                return ApiResponse(message=_('管理员不存在'), code=404)
            if email:
                user.email = email
            user.role = role
            user.admin_app_ids = admin_app_ids
            if password:
                user.password = password
            user.save()
            return ApiResponse(data=AdminUserSerializer(user).data, message=_('已更新'))

        if not username or not email or not password:
            return ApiResponse(message=_('账号、邮箱、密码必填'), code=400)
        if User.objects.filter(username=username).exists():
            return ApiResponse(message=_('用户名已存在'), code=400)
        if User.objects.filter(email=email).exists():
            return ApiResponse(message=_('邮箱已存在'), code=400)

        user = User.objects.create(
            username=username,
            email=email,
            password=password,
            role=role,
            admin_app_ids=admin_app_ids,
            nickname=username,
            profile_complete=True,
        )
        return ApiResponse(data=AdminUserSerializer(user).data, message=_('已创建'), code=201)

    @extend_schema(summary=_('启停管理员'))
    @action(detail=False, methods=['post'], url_path=r'members/(?P<member_id>[^/.]+)/toggle-status')
    def toggle_member(self, request, member_id=None):
        actor = request.user
        if actor.role != 'super_admin':
            return ApiResponse(message=_('仅超管可管理成员'), code=403)
        user = User.objects.filter(id=member_id, role__in=ADMIN_ROLE_KEYS).first()
        if not user:
            return ApiResponse(message=_('管理员不存在'), code=404)
        if user.id == actor.id:
            return ApiResponse(message=_('不能停用自己'), code=400)
        if user.role == 'super_admin' and actor.role != 'super_admin':
            return ApiResponse(message=_('不可操作超管'), code=403)
        user.status = 0 if user.status == 1 else 1
        user.save(update_fields=['status'])
        return ApiResponse(data={'user_id': user.id, 'status': user.status}, message=_('状态已更新'))

    @extend_schema(summary=_('角色与权限'))
    @action(detail=False, methods=['get', 'post'], url_path='roles')
    def roles(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        actor = getattr(request, 'user', None)
        if actor and hasattr(actor, 'role') and not can_access_app(actor, app_id):
            return ApiResponse(message=_('无权访问该 App'), code=403)
        app_id = concrete_app_id(actor, app_id) if actor else app_id

        if request.method == 'GET':
            overrides = load_role_overrides(app_id)
            roles = []
            for r in ROLE_DEFS:
                roles.append({
                    **r,
                    'permissions': get_role_permissions(r['key'], overrides=overrides, app_id=app_id),
                })
            return ApiResponse(data={
                'app_id': app_id,
                'apps': KNOWN_APPS,
                'roles': roles,
                'permissions': ALL_PERMISSIONS,
                'overrides': overrides,
            })

        if actor.role != 'super_admin':
            return ApiResponse(message=_('仅超管可改角色权限'), code=403)
        if is_all_app(request.data.get('app_id') or ''):
            return ApiResponse(message=_('请选择具体产品后再保存权限'), code=400)
        role = request.data.get('role')
        permissions = request.data.get('permissions') or []
        if role not in ADMIN_ROLE_KEYS:
            return ApiResponse(message=_('无效角色'), code=400)
        if role == 'super_admin':
            permissions = ['*']
        obj, _ = AdminRolePermission.objects.update_or_create(
            app_id=app_id,
            role=role,
            defaults={'permissions': permissions},
        )
        return ApiResponse(data={
            'app_id': obj.app_id,
            'role': obj.role,
            'permissions': obj.permissions,
        }, message=_('已保存'))
