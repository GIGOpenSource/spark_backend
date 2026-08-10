from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from models.models import User
from tools.token_tools import CustomTokenTool
from tools.auth_helpers import get_token_from_request


class IsStaffUser(BasePermission):
    """允许 is_staff=True 或 is_active=True 的用户访问"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_staff or request.user.is_active


class IsOwner(BasePermission):
    """允许管理员访问"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 只允许 User 表的管理员
        if isinstance(request.user, User):
            from tools.admin_rbac import ADMIN_ROLE_KEYS
            if request.user.role in ADMIN_ROLE_KEYS:
                return True
        return False


class IsAdmin(BasePermission):
    """Allow access for admin roles."""
    def has_permission(self, request, view):
        from tools.admin_rbac import ADMIN_ROLE_KEYS
        try:
            role = request.user.role
        except AttributeError:
            raise AuthenticationFailed({"code": 401, "message": "管理员无role权限"})
        if not request.user or not role:
            raise AuthenticationFailed({"code": 401, "message": "请提供有效的管理员token"})
        try:
            if role in ADMIN_ROLE_KEYS:
                return True
            raise AuthenticationFailed({"code": 401, "message": "管理员role权限不够"})
        except User.DoesNotExist:
            raise AuthenticationFailed('token对应的管理员不存在')

class IsTokenValid(BasePermission):
    """
    自定义权限：仅允许携带有效 Token 且账号未封禁的请求访问
    """
    message = "Token 无效或已过期"  # 权限拒绝时的提示

    def has_permission(self, request, view):
        token = get_token_from_request(request)
        is_valid, user_id = CustomTokenTool.verify_token(token)
        if is_valid and user_id:
            try:
                request.user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return False
            # BE-008: banned users (status != 1) cannot use REST token
            if getattr(request.user, 'status', 1) != 1:
                self.message = "账号已被封禁"
                return False
            return True
        return False


class RequireAdminPerm(BasePermission):
    """
    BE-009 helper: require a menu permission from effective_permissions.

    Usage on a ViewSet:
      permission_classes = [IsTokenValid, IsAdmin, RequireAdminPerm]
      required_admin_perm = 'users'          # fixed
      # or map by action:
      admin_perm_map = {'list': 'users', 'create': 'users', 'dashboard': 'dashboard'}

    Super-admin / '*' always passes. Empty permissions deny.
    Also available as function: check_admin_perm(user, perm, app_id).
    """
    message = "缺少管理端权限"

    def has_permission(self, request, view):
        from tools.admin_rbac import (
            effective_permissions, resolve_request_app_id, is_all_app,
        )
        user = request.user
        # Custom User is models.Model (no AbstractBaseUser.is_authenticated).
        # Treat any user with an id as authenticated; role gate is IsAdmin.
        if not user or not getattr(user, 'id', None):
            return False
        if getattr(user, 'role', None) == 'super_admin':
            return True
        perm = getattr(view, 'required_admin_perm', None)
        action = getattr(view, 'action', None)
        perm_map = getattr(view, 'admin_perm_map', None) or {}
        if action and action in perm_map:
            perm = perm_map[action]
        if not perm:
            return True  # no perm declared → do not block (opt-in)
        app_id = resolve_request_app_id(request, default='spark_main')
        if is_all_app(app_id):
            app_id = 'spark_main'
        perms = effective_permissions(user, app_id=app_id)
        if not perms:
            return False
        if '*' in perms or perm in perms:
            return True
        if perm == 'config' and 'app_list' in perms:
            return True
        return False


def check_admin_perm(user, perm, app_id='spark_main'):
    """Imperative helper for spark_admin write paths."""
    from tools.admin_rbac import effective_permissions, is_all_app
    if not user:
        return False
    if getattr(user, 'role', None) == 'super_admin':
        return True
    if is_all_app(app_id):
        app_id = 'spark_main'
    perms = effective_permissions(user, app_id=app_id)
    if not perms:
        return False
    return '*' in perms or perm in perms or (perm == 'config' and 'app_list' in perms)


class RequireAppModule(BasePermission):
    """
    Gate product APIs by AppConfig.config.enabled_modules.
    Ungated paths (bootstrap/auth/admin/...) always pass.
    """
    message = "该 APP 未开通此功能"

    def has_permission(self, request, view):
        from tools.app_modules import (
            path_to_module, is_module_enabled, resolve_request_app_id_for_module,
        )
        module = path_to_module(request.path)
        if not module:
            return True
        app_id = resolve_request_app_id_for_module(request)
        return is_module_enabled(app_id, module)

class IsCustomerTokenValid(BasePermission):
    """C 端客户 Token（请求头 token，值为 CToken 开头）。"""
    message = "客户 Token 无效或已过期"

    def has_permission(self, request, view):
        token = request.headers.get("token")
        is_valid, customer_id = CustomTokenTool.verify_customer_token(token)
        if is_valid:
            request.customer_id = int(customer_id)
            return True
        raise AuthenticationFailed({"code": 401, "message": "请先登录"})


class IsOwnerOrAdmin(BasePermission):
    """
    自定义权限：仅允许对象所有者或管理员访问
    """
    message = "您没有权限访问此对象"  # 权限拒绝时的提示

    def has_object_permission(self, request, view, obj):
        from models.models import User

        # 管理员可以操作所有对象
        if isinstance(request.user, User):
            from tools.admin_rbac import ADMIN_ROLE_KEYS
            if hasattr(request.user, 'role') and request.user.role in ADMIN_ROLE_KEYS:
                return True

        # 客户用户只能操作自己上传的壁纸
        if isinstance(request.user):
            # 检查是否有 customer_upload 关系
            if hasattr(obj, 'customer_upload'):
                upload_relation = obj.customer_upload
                if upload_relation and upload_relation.customer_id == request.user.id:
                    return True
        return False


class URLAuthorization(BasePermission):
    def authenticate(self, request):
        # 获取当前请求的 URL
        url = request.path
        # 获取当前用户
        user = request.user
        token = request.query_params.get('token')
        if not token:
            return
        return True

class HeaderAuthorization(BasePermission):
    def authenticate(self, request):
        # 获取当前请求的 Header
        token = request.META.get('HTTP_AUTHORIZATION')
        # 获取当前用户
        if not token:
            return
        return True

class NotAuthenticated(BasePermission):
    """
    没有权限 兜底认证
    """
    def authenticate(self, request):
        raise AuthenticationFailed({"code":20000,"message":'用户未认证'})
    def authenticate_header(self, request):
        return 'NotAuthenticated'