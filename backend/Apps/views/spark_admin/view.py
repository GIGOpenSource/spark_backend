from datetime import timedelta

from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema

from tools.permissions import IsAdmin, IsTokenValid
from tools.utils import ApiResponse, CustomPagination
from tools.firebase_mock import list_users, list_orders, list_payments
from tools.spark_helpers import (
    serialize_user_card, recompute_abc_grades,
    ensure_recommend_stat, apply_vip_subscription_grants, serialize_funnel_abc_rule,
    get_product_profile, set_product_profile, clear_vip_grant_balances,
    spendable_balances, grant_ledger, ensure_daily_likes, ensure_daily_feed, period_day_key,
)
from tools.app_modules import (
    ALL_MODULE_KEYS, default_enabled_modules, modules_catalog_payload,
    serialize_app_config_row,
)
from tools.admin_rbac import (
    can_access_app, resolve_request_app_id, KNOWN_APPS,
    app_scope_filter, is_all_app, concrete_app_id, accessible_app_ids,
)
from tools.robot_excel import build_robot_import_template, parse_robot_import_rows
from models.models import (
    User, Order, Payment, FunnelPool, DiscoverParam, AppConfig, CountryConfig,
    ReviewMode, AdLink, WordFilter, DomainWhitelist, Report, SkuMap, AnalyticsEvent,
    UserPhoto, FunnelAbcRule, UserRecommendStat, RobotRecommendList,
    Conversation, Message, EntitlementLedger, Swipe, SystemPushConfig,
    ProviderConfig, QmTicket, QmPair, ChatRoom, ChatRoomMember, ChatRoomMessage,
    Topic, Post, PostComment, GoogleAdsCampaign, FacebookAdsCampaign, AdAttribution,
    MatchQA,
)


class AdminPermissionMixin:
    """
    Admin API base permissions. Sensitive writes should declare
    required_admin_perm / admin_perm_map (see tools.permissions.RequireAdminPerm)
    or call check_admin_perm() inside the action.
    """
    def get_permissions(self):
        from tools.permissions import RequireAdminPerm
        return [IsTokenValid(), IsAdmin(), RequireAdminPerm()]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        app_id = resolve_request_app_id(request, default='')
        if app_id and not can_access_app(request.user, app_id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied({'code': 403, 'message': '无权访问该 App'})

    def _app_id(self, request, default='spark_main'):
        app_id = resolve_request_app_id(request, default=default)
        if not can_access_app(request.user, app_id):
            return None, ApiResponse(message='无权访问该 App', code=403)
        return app_id, None

    def _app_scope(self, request, app_id):
        return app_scope_filter(request.user, app_id)

    def _write_app_id(self, request, default='spark_main'):
        """Writes need a concrete app; refuse workspace=* (no silent remap)."""
        raw = resolve_request_app_id(request, default=default)
        if is_all_app(raw):
            return None, ApiResponse(
                message='请选择具体 App 后再写入（不可为 *）',
                code=400,
            )
        if not can_access_app(request.user, raw):
            return None, ApiResponse(message='无权访问该 App', code=403)
        return raw, None

    def _require_perm(self, request, perm, app_id='spark_main'):
        from tools.permissions import check_admin_perm
        if check_admin_perm(request.user, perm, app_id=app_id):
            return None
        return ApiResponse(message=f'缺少权限: {perm}', code=403)

from Apps.views.spark_admin.coverage_admin import CoverageAdminMixin


@extend_schema(tags=[_('管理后台')])
class SparkAdminViewSet(AdminPermissionMixin, CoverageAdminMixin, viewsets.ViewSet):
    pagination_class = CustomPagination
    # BE-009: map sensitive admin actions → menu permissions (RequireAdminPerm)
    admin_perm_map = {
        'dashboard': 'dashboard',
        'users': 'users',
        'users_detail': 'users',
        'users_action': 'users',
        'chats': 'chats',
        'chat_messages': 'chats',
        'matches_admin': 'matches',
        'matches_action': 'matches',
        'funnel': 'funnel',
        'funnel_item': 'funnel',
        'funnel_import': 'funnel',
        'orders': 'orders',
        'skus': 'orders',
        'app_config': 'config',
        'product_profile': 'config',
        'app_list': 'config',
        'review_mode': 'review',
        'country_config': 'country',
        'safety': 'safety',
        'analytics_events': 'events',
        'analytics_overview': 'events',
        'ledgers_admin': 'ledger',
        'quick_match_admin': 'quick_match',
        'quick_match_action': 'quick_match',
        'groups_admin': 'groups',
        'topics_admin': 'community',
        'posts_admin': 'community',
    }
    def _as_date(self, value):
        if value is None:
            return None
        if hasattr(value, 'date') and callable(value.date):
            try:
                if timezone.is_aware(value):
                    value = timezone.localtime(value)
            except Exception:
                pass
            return value.date()
        return value

    def _build_retention_wide(self, users_qs, today, days=30):
        """
        30-day retention wide table.
        Rows: register cohort dates (last `days` days).
        Columns: D0..D{days} rates / retained counts.
        Activity = register day ∪ online_at ∪ analytics events ∪ swipes ∪ messages.
        """
        from collections import defaultdict

        cohort_start = today - timedelta(days=days)
        activity_start = cohort_start
        activity_end = today

        cohort_rows = list(
            users_qs.filter(
                created_at__date__gte=cohort_start,
                created_at__date__lte=today,
            ).values('id', 'created_at', 'online_at')[:5000]  # A-08: hard cap; async export TODO if larger
        )
        day_offsets = list(range(days + 1))
        if not cohort_rows:
            return {'days': day_offsets, 'rows': []}

        user_ids = [r['id'] for r in cohort_rows]
        cohort_by_date = defaultdict(set)
        activity_by_user = defaultdict(set)

        for r in cohort_rows:
            uid = r['id']
            cdate = self._as_date(r['created_at'])
            if not cdate:
                continue
            cohort_by_date[cdate].add(uid)
            activity_by_user[uid].add(cdate)
            odate = self._as_date(r.get('online_at'))
            if odate and activity_start <= odate <= activity_end:
                activity_by_user[uid].add(odate)

        for row in (
            AnalyticsEvent.objects.filter(
                user_id__in=user_ids,
                created_at__date__gte=activity_start,
                created_at__date__lte=activity_end,
            )
            .annotate(day=TruncDate('created_at'))
            .values('user_id', 'day')
            .distinct()
        ):
            if row['user_id'] and row['day']:
                activity_by_user[row['user_id']].add(self._as_date(row['day']))

        for row in (
            Swipe.objects.filter(
                actor_id__in=user_ids,
                created_at__date__gte=activity_start,
                created_at__date__lte=activity_end,
            )
            .annotate(day=TruncDate('created_at'))
            .values('actor_id', 'day')
            .distinct()
        ):
            if row['actor_id'] and row['day']:
                activity_by_user[row['actor_id']].add(self._as_date(row['day']))

        for row in (
            Message.objects.filter(
                sender_id__in=user_ids,
                created_at__date__gte=activity_start,
                created_at__date__lte=activity_end,
            )
            .annotate(day=TruncDate('created_at'))
            .values('sender_id', 'day')
            .distinct()
        ):
            if row['sender_id'] and row['day']:
                activity_by_user[row['sender_id']].add(self._as_date(row['day']))

        rows = []
        for offset in range(days + 1):
            cdate = today - timedelta(days=offset)
            members = cohort_by_date.get(cdate) or set()
            new_users = len(members)
            rates = []
            counts = []
            for d in day_offsets:
                target = cdate + timedelta(days=d)
                if target > today:
                    rates.append(None)
                    counts.append(None)
                    continue
                if new_users == 0:
                    rates.append(0.0)
                    counts.append(0)
                    continue
                retained = sum(1 for uid in members if target in activity_by_user.get(uid, ()))
                counts.append(retained)
                rates.append(round(retained / new_users, 4))
            rows.append({
                'cohort_date': str(cdate),
                'new_users': new_users,
                'rates': rates,
                'counts': counts,
            })
        return {'days': day_offsets, 'rows': rows}

    @extend_schema(summary=_('汇总看板'))
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        country = request.query_params.get('country') or ''
        platform = request.query_params.get('platform') or ''
        date_from = request.query_params.get('date_from') or ''
        date_to = request.query_params.get('date_to') or ''
        cache_key = f'admin:dashboard:{app_id}:{country}:{platform}:{date_from}:{date_to}'
        try:
            from tools.token_tools import _redis
            cached = _redis.getKey(cache_key)
            if cached:
                import json
                return ApiResponse(data=json.loads(cached), message='ok')
        except Exception:
            pass
        try:
            data = self._build_dashboard_payload(
                request, app_id=app_id, country=country, platform=platform,
                date_from=date_from, date_to=date_to,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception('dashboard build failed')
            return ApiResponse(code=500, message='dashboard_error', data={'error': str(exc)[:200]})
        try:
            from tools.token_tools import _redis
            import json
            _redis.setKey(cache_key, json.dumps(data, default=str), ex=600)
        except Exception:
            pass
        return ApiResponse(data=data, message='ok')

    def _build_dashboard_payload(self, request, *, app_id, country, platform, date_from, date_to):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        range_start = today - timedelta(days=14)
        range_end = today
        from datetime import date as date_cls
        if date_from:
            try:
                range_start = date_cls.fromisoformat(date_from)
            except ValueError:
                pass
        if date_to:
            try:
                range_end = date_cls.fromisoformat(date_to)
            except ValueError:
                pass
        scope = self._app_scope(request, app_id)
        app_ids = accessible_app_ids(request.user) if is_all_app(app_id) else [app_id]
        users = User.objects.filter(**scope, role='user')
        if country and country != '*':
            users = users.filter(country__iexact=country)
        regs_today = users.filter(created_at__date=today).count()
        regs_yday = users.filter(created_at__date=yesterday).count()
        dau = users.filter(online_at__date=today).count()
        pays = Payment.objects.filter(Q(app_id__in=app_ids) | Q(user__app_id__in=app_ids), status='success')
        if country and country != '*':
            pays = pays.filter(user__country__iexact=country)
        if platform:
            pays = pays.filter(order__platform=platform)
        pay_today = pays.filter(created_at__date=today)
        gmv_today = pay_today.aggregate(s=Sum('order__amount'))['s'] or 0
        gmv_yday = pays.filter(created_at__date=yesterday).aggregate(s=Sum('order__amount'))['s'] or 0
        first_buyers = Order.objects.filter(app_id__in=app_ids, status='success')
        if country and country != '*':
            first_buyers = first_buyers.filter(user__country__iexact=country)
        first_buyers_n = first_buyers.values('user_id').distinct().count()
        trend_qs = users.filter(
            created_at__date__gte=range_start, created_at__date__lte=range_end,
        )
        trend = list(
            trend_qs.annotate(day=TruncDate('created_at')).values('day').annotate(c=Count('id')).order_by('day')
        )
        gmv_trend = list(
            pays.filter(created_at__date__gte=range_start, created_at__date__lte=range_end)
            .annotate(day=TruncDate('created_at')).values('day')
            .annotate(c=Count('id'), s=Sum('order__amount')).order_by('day')
        )
        order_qs = Order.objects.filter(app_id__in=app_ids, status='success')
        if country and country != '*':
            order_qs = order_qs.filter(user__country__iexact=country)
        platform_mix = list(
            order_qs.values('platform').annotate(c=Count('id'), s=Sum('amount')).order_by('-c')
        )
        tier_mix = list(
            users.exclude(vip_tier='none').values('vip_tier').annotate(c=Count('id')).order_by('-c')
        )
        retention_wide = self._build_retention_wide(users, today, days=30)
        return {
            'kpi': {
                'register_today': regs_today,
                'register_yesterday': regs_yday,
                'dau': dau,
                'pay_count_today': pay_today.count(),
                'gmv_today': float(gmv_today),
                'gmv_yesterday': float(gmv_yday),
                'first_buyers': first_buyers_n,
                'pay_rate': round(first_buyers_n / max(users.count(), 1), 4),
            },
            'filters': {
                'app_id': app_id,
                'country': country or '*',
                'platform': platform or '',
                'date_from': str(range_start),
                'date_to': str(range_end),
            },
            'register_trend': [{'day': str(t['day']), 'count': t['c']} for t in trend],
            'gmv_trend': [{
                'day': str(t['day']), 'count': t['c'], 'amount': float(t['s'] or 0),
            } for t in gmv_trend],
            'platform_mix': [{
                'platform': t['platform'] or 'unknown',
                'count': t['c'],
                'amount': float(t['s'] or 0),
            } for t in platform_mix],
            'vip_tier_mix': [{'tier': t['vip_tier'], 'count': t['c']} for t in tier_mix],
            'retention_wide': retention_wide,
            'recent_payments': [{
                'id': p.id, 'user_id': p.user_id, 'amount': float(p.order.amount),
                'product_id': p.order.product_id, 'platform': p.order.platform,
                'created_at': p.created_at.isoformat(),
            } for p in pays.select_related('order').order_by('-id')[:20]],
        }

    @extend_schema(summary=_('用户列表'))
    @action(detail=False, methods=['get'], url_path='users')
    def users(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        q = request.query_params.get('q') or ''
        qs = User.objects.filter(**self._app_scope(request, app_id), role='user').select_related('recommend_stat').order_by('-id')
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(nickname__icontains=q) | Q(username__icontains=q))
        page = CustomPagination()
        result = page.paginate_queryset(qs, request)
        data = []
        for u in result:
            row = serialize_user_card(u) | {
                'email': u.email, 'has_recharged': u.has_recharged, 'status': u.status,
                'created_at': u.created_at.isoformat(),
                'country': u.country or '',
                'app_id': u.app_id or '',
                'login_type': u.login_type or User.LOGIN_EMAIL,
            }
            try:
                row['abc_grade'] = u.recommend_stat.grade
            except UserRecommendStat.DoesNotExist:
                row['abc_grade'] = ensure_recommend_stat(u).grade
            data.append(row)
        return page.get_paginated_response(data)

    @extend_schema(summary=_('Firebase 注册列表'))
    @action(detail=False, methods=['get'], url_path='firebase/users')
    def firebase_users(self, request):
        return ApiResponse(data={'list': list_users(request.query_params.get('app_id'))}, message='ok')

    @extend_schema(summary=_('Firebase 订单'))
    @action(detail=False, methods=['get'], url_path='firebase/orders')
    def firebase_orders(self, request):
        return ApiResponse(data={'list': list_orders(request.query_params.get('app_id'))}, message='ok')

    @extend_schema(summary=_('Firebase 支付'))
    @action(detail=False, methods=['get'], url_path='firebase/payments')
    def firebase_payments(self, request):
        return ApiResponse(data={'list': list_payments(request.query_params.get('app_id'))}, message='ok')

    @extend_schema(summary=_('漏斗 · 机器人卡片'))
    @action(detail=False, methods=['get', 'post'], url_path='funnel')
    def funnel(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        country = request.query_params.get('country') or request.data.get('country') or '*'
        if request.method == 'GET':
            qs = FunnelPool.objects.filter(**self._app_scope(request, app_id)).filter(
                Q(pool=FunnelPool.POOL_ROBOT) | Q(pool__in=('A', 'B', 'C'))
            )
            if country and country != '*':
                qs = qs.filter(Q(country='*') | Q(country=country))
            return ApiResponse(data={'list': [{
                'id': i.id, 'pool': 'robot', 'nickname': i.nickname, 'age': i.age,
                'job': i.job, 'city': i.city, 'photo_urls': i.photo_urls,
                'bio': i.bio, 'is_active': i.is_active, 'sort_order': i.sort_order,
                'country': i.country, 'locale': i.locale, 'linked_user_id': i.linked_user_id,
                'app_id': i.app_id,
            } for i in qs.order_by('sort_order', 'id')]}, message='ok')
        write_app, err = self._write_app_id(request)
        if err:
            return err
        item = FunnelPool.objects.create(
            app_id=write_app,
            country=country,
            locale=(request.data.get('locale') or 'en').lower(),
            pool=FunnelPool.POOL_ROBOT,
            nickname=request.data.get('nickname') or 'User',
            age=int(request.data.get('age') or 24),
            job=request.data.get('job') or '',
            city=request.data.get('city') or '',
            bio=request.data.get('bio') or '',
            photo_urls=request.data.get('photo_urls') or [],
            tags=request.data.get('tags') or [],
            mbti=request.data.get('mbti') or '',
            zodiac=request.data.get('zodiac') or '',
            relationship=request.data.get('relationship') or '',
            is_traveling=bool(request.data.get('is_traveling')),
            blur=False,
            is_active=True,
            sort_order=int(request.data.get('sort_order') or 0),
        )
        return ApiResponse(data={'id': item.id}, message='ok', code=201)

    @extend_schema(summary=_('机器人卡片 Excel 模板'))
    @action(detail=False, methods=['get'], url_path='funnel-import-template')
    def funnel_import_template(self, request):
        content = build_robot_import_template()
        resp = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = 'attachment; filename="robot_cards_template.xlsx"'
        return resp

    @extend_schema(summary=_('机器人卡片 Excel 导入'))
    @action(
        detail=False, methods=['post'], url_path='funnel-import',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def funnel_import(self, request):
        write_app, err = self._write_app_id(request)
        if err:
            return err
        upload = request.FILES.get('file') or request.FILES.get('excel')
        if not upload:
            return ApiResponse(message='file required', code=400)
        name = (getattr(upload, 'name', '') or '').lower()
        if not (name.endswith('.xlsx') or name.endswith('.xlsm')):
            return ApiResponse(message='only .xlsx supported', code=400)

        default_country = request.data.get('country') or request.query_params.get('country') or '*'
        default_locale = request.data.get('locale') or request.query_params.get('locale') or 'en'
        try:
            rows, errors = parse_robot_import_rows(
                upload, default_country=default_country, default_locale=default_locale,
            )
        except Exception as exc:
            return ApiResponse(message=f'invalid excel: {exc}', code=400)

        if not rows and errors:
            return ApiResponse(message=errors[0], code=400, data={'errors': errors})
        if not rows:
            return ApiResponse(message='no data rows', code=400)

        created_ids = []
        for row in rows:
            item = FunnelPool.objects.create(
                app_id=write_app,
                pool=FunnelPool.POOL_ROBOT,
                blur=False,
                is_active=True,
                is_verified=True,
                **row,
            )
            created_ids.append(item.id)
        return ApiResponse(data={
            'created': len(created_ids),
            'ids': created_ids,
            'errors': errors,
        }, message='ok', code=201)

    @extend_schema(summary=_('更新漏斗机器人卡'))
    @action(detail=False, methods=['put', 'patch', 'delete'], url_path=r'funnel/(?P<fid>[^/.]+)')
    def funnel_item(self, request, fid=None):
        item = FunnelPool.objects.filter(id=fid).first()
        if not item:
            return ApiResponse(message='not found', code=404)
        if request.method == 'DELETE':
            item.delete()
            return ApiResponse(message='ok')
        for f in ('nickname', 'job', 'city', 'bio', 'mbti', 'zodiac', 'relationship', 'country', 'locale'):
            if f in request.data:
                val = request.data.get(f)
                if f == 'locale' and val:
                    val = str(val).lower()
                setattr(item, f, val)
        if 'age' in request.data:
            item.age = int(request.data.get('age'))
        if 'photo_urls' in request.data:
            item.photo_urls = request.data.get('photo_urls')
        if 'tags' in request.data:
            item.tags = request.data.get('tags')
        if 'is_active' in request.data:
            item.is_active = bool(request.data.get('is_active'))
        if 'sort_order' in request.data:
            item.sort_order = int(request.data.get('sort_order') or 0)
        item.blur = False
        item.pool = FunnelPool.POOL_ROBOT
        item.save()
        return ApiResponse(message='ok')

    @extend_schema(summary=_('机器人推荐列表'))
    @action(detail=False, methods=['get', 'post'], url_path='robot-recommend-lists')
    def robot_recommend_lists(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or ''
        if request.method == 'GET':
            qs = RobotRecommendList.objects.all().order_by('-priority', 'app_id', 'country', 'locale')
            if app_id and not is_all_app(app_id):
                qs = qs.filter(app_id=app_id)
            elif app_id and is_all_app(app_id):
                qs = qs.filter(**self._app_scope(request, app_id))
            country = request.query_params.get('country')
            locale = request.query_params.get('locale')
            if country and country != '*':
                qs = qs.filter(country=country)
            if locale and locale != '*':
                qs = qs.filter(locale=locale.lower())
            rows = []
            for row in qs:
                ids = []
                for x in (row.robot_ids or []):
                    try:
                        ids.append(int(x))
                    except (TypeError, ValueError):
                        continue
                robot_map = {
                    r['id']: r
                    for r in FunnelPool.objects.filter(id__in=ids).values(
                        'id', 'nickname', 'is_active', 'app_id'
                    )
                }
                robots = [robot_map[i] for i in ids if i in robot_map]
                rows.append({
                    'id': row.id,
                    'app_id': row.app_id,
                    'country': row.country,
                    'locale': row.locale,
                    'priority': int(getattr(row, 'priority', 0) or 0),
                    'name': row.name or '',
                    'robot_ids': ids,
                    'robots': robots,
                    'is_active': row.is_active,
                    'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                })
            return ApiResponse(data={'list': rows}, message='ok')

        app_id = request.data.get('app_id') or 'spark_main'
        country = request.data.get('country') or '*'
        locale = (request.data.get('locale') or '*').lower() or '*'
        robot_ids = request.data.get('robot_ids') or []
        cleaned = []
        for x in robot_ids:
            try:
                cleaned.append(int(x))
            except (TypeError, ValueError):
                continue
        # only keep robots that belong to the same app
        valid_ids = list(
            FunnelPool.objects.filter(app_id=app_id, id__in=cleaned).values_list('id', flat=True)
        )
        # preserve order from request
        order = {rid: i for i, rid in enumerate(cleaned)}
        valid_ids.sort(key=lambda rid: order.get(rid, 9999))

        if not valid_ids:
            return ApiResponse(message='select at least one robot', code=400)

        rid = request.data.get('id')
        defaults = {
            'name': request.data.get('name') or f'{app_id}/{country}/{locale}',
            'robot_ids': valid_ids,
            'is_active': bool(request.data.get('is_active', True)),
            'priority': int(request.data.get('priority', 0) or 0),
        }
        if rid:
            obj = RobotRecommendList.objects.filter(id=rid).first()
            if not obj:
                return ApiResponse(message='not found', code=404)
            clash = RobotRecommendList.objects.filter(
                app_id=app_id, country=country, locale=locale,
            ).exclude(id=obj.id).exists()
            if clash:
                return ApiResponse(message='list already exists for this app/region/language', code=400)
            obj.app_id = app_id
            obj.country = country
            obj.locale = locale
            for k, v in defaults.items():
                setattr(obj, k, v)
            obj.save()
        else:
            if 'priority' not in request.data:
                defaults['priority'] = 0
            obj, _ = RobotRecommendList.objects.update_or_create(
                app_id=app_id, country=country, locale=locale, defaults=defaults,
            )
        return ApiResponse(data={'id': obj.id, 'robot_ids': obj.robot_ids}, message='ok', code=201)

    @extend_schema(summary=_('删除机器人推荐列表'))
    @action(detail=False, methods=['delete'], url_path=r'robot-recommend-lists/(?P<lid>[^/.]+)')
    def robot_recommend_list_item(self, request, lid=None):
        obj = RobotRecommendList.objects.filter(id=lid).first()
        if not obj:
            return ApiResponse(message='not found', code=404)
        obj.delete()
        return ApiResponse(message='ok')

    @extend_schema(summary=_('真实用户推荐规则列表 / 新建'))
    @action(detail=False, methods=['get', 'post'], url_path='funnel-abc-rule')
    def funnel_abc_rule(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        country = request.query_params.get('country') or ''
        if request.method == 'GET':
            qs = FunnelAbcRule.objects.filter(**self._app_scope(request, app_id)).order_by(
                '-priority', 'country', 'locale', '-id',
            )
            if country and country != '*':
                qs = qs.filter(Q(country='*') | Q(country__iexact=country))
            return ApiResponse(data={
                'list': [serialize_funnel_abc_rule(r) for r in qs],
                'hint': 'Top A% = A, next B% = B, remaining = C (by right_swipe / impression)',
            }, message='ok')

        write_app, err = self._write_app_id(request)
        if err:
            return err
        country = (request.data.get('country') or '*').strip() or '*'
        locale = (request.data.get('locale') or '*').strip() or '*'
        a = int(request.data.get('a_percent', 20))
        b = int(request.data.get('b_percent', 40))
        c = int(request.data.get('c_percent', 40))
        priority = int(request.data.get('priority', 0) or 0)
        if a < 0 or b < 0 or c < 0:
            return ApiResponse(message='percentages must be >= 0', code=400)
        if a + b + c != 100:
            return ApiResponse(message='A+B+C must equal 100', code=400)
        if FunnelAbcRule.objects.filter(app_id=write_app, country=country, locale=locale).exists():
            return ApiResponse(message='rule already exists for this region/language', code=400)
        rule = FunnelAbcRule.objects.create(
            app_id=write_app, country=country, locale=locale,
            priority=priority,
            a_percent=a, b_percent=b, c_percent=c,
        )
        summary = recompute_abc_grades(write_app, country, locale)
        return ApiResponse(data={
            **serialize_funnel_abc_rule(rule),
            'recompute': summary,
        }, message='ok', code=201)

    @extend_schema(summary=_('更新 / 删除真实用户推荐规则'))
    @action(detail=False, methods=['put', 'patch', 'delete'], url_path=r'funnel-abc-rule/(?P<rid>[^/.]+)')
    def funnel_abc_rule_item(self, request, rid=None):
        rule = FunnelAbcRule.objects.filter(id=rid).first()
        if not rule:
            return ApiResponse(message='not found', code=404)
        if request.method == 'DELETE':
            rule.delete()
            return ApiResponse(message='ok')

        country = rule.country
        locale = rule.locale
        if 'country' in request.data:
            country = (request.data.get('country') or '*').strip() or '*'
        if 'locale' in request.data:
            locale = (request.data.get('locale') or '*').strip() or '*'
        a = int(request.data.get('a_percent', rule.a_percent))
        b = int(request.data.get('b_percent', rule.b_percent))
        c = int(request.data.get('c_percent', rule.c_percent))
        priority = int(request.data.get('priority', getattr(rule, 'priority', 0) or 0) or 0)
        if a < 0 or b < 0 or c < 0:
            return ApiResponse(message='percentages must be >= 0', code=400)
        if a + b + c != 100:
            return ApiResponse(message='A+B+C must equal 100', code=400)
        clash = FunnelAbcRule.objects.filter(
            app_id=rule.app_id, country=country, locale=locale,
        ).exclude(id=rule.id).exists()
        if clash:
            return ApiResponse(message='rule already exists for this region/language', code=400)
        rule.country = country
        rule.locale = locale
        rule.priority = priority
        rule.a_percent = a
        rule.b_percent = b
        rule.c_percent = c
        rule.save()
        summary = recompute_abc_grades(rule.app_id, country, locale)
        return ApiResponse(data={
            **serialize_funnel_abc_rule(rule),
            'recompute': summary,
        }, message='ok')

    @extend_schema(summary=_('按规则重算用户 ABC 评级'))
    @action(detail=False, methods=['post'], url_path='funnel-recompute')
    def funnel_recompute(self, request):
        # O-09: require concrete app_id; refuse peak hours unless confirm=true
        app_id = (request.data.get('app_id') or '').strip()
        if not app_id or app_id == '*':
            return ApiResponse(message='app_id required (no *)', code=400)
        confirm = request.data.get('confirm') in (True, 'true', '1', 1, 'yes')
        hour = timezone.now().hour  # UTC; peak ~10–22
        if 10 <= hour < 22 and not confirm:
            return ApiResponse(
                message='refuse during peak hours (UTC 10–22); pass confirm=true to override',
                code=403,
            )
        country = request.data.get('country') or '*'
        locale = request.data.get('locale') or '*'
        summary = recompute_abc_grades(app_id, country, locale)
        return ApiResponse(data=summary, message='ok')

    @extend_schema(summary=_('发现参数'))
    @action(detail=False, methods=['get', 'post'], url_path='discover-params')
    def discover_params(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        country = request.query_params.get('country') or request.data.get('country') or '*'
        obj, _ = DiscoverParam.objects.get_or_create(app_id=app_id, country=country)
        if request.method == 'GET':
            return ApiResponse(data={
                'daily_like_limit': obj.daily_like_limit,
                'match_expire_days': obj.match_expire_days,
                'say_hi_expire_days': obj.say_hi_expire_days,
                'free_say_hi_replies': obj.free_say_hi_replies,
                'like_bonus_threshold': obj.like_bonus_threshold,
                'like_bonus_count': obj.like_bonus_count,
                'config': obj.config,
            }, message='ok')
        for f in ('daily_like_limit', 'match_expire_days', 'say_hi_expire_days', 'free_say_hi_replies',
                  'like_bonus_threshold', 'like_bonus_count'):
            if f in request.data:
                setattr(obj, f, int(request.data.get(f)))
        if 'config' in request.data:
            obj.config = request.data.get('config')
        obj.save()
        return ApiResponse(message='ok')

    def _serialize_admin_user(self, user):
        row = serialize_user_card(user, include_pending_photos=True) | {
            'email': user.email,
            'username': user.username,
            'has_recharged': user.has_recharged,
            'status': user.status,
            'created_at': user.created_at.isoformat(),
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
            'country': user.country or '',
            'app_id': user.app_id or '',
            'login_type': user.login_type or User.LOGIN_EMAIL,
            'birthday': user.birthday.isoformat() if user.birthday else None,
            'vip_tier_raw': user.vip_tier,
            'looking_for': user.looking_for or '',
            'social_links': user.social_links or {},
            'lifestyle': user.lifestyle or {},
            'interests': user.interests or [],
        }
        try:
            row['abc_grade'] = user.recommend_stat.grade
        except Exception:
            row['abc_grade'] = ensure_recommend_stat(user).grade
        balances = spendable_balances(user)
        row['balances'] = {
            'super_like': balances.get(EntitlementLedger.SUPER_LIKE, 0),
            'boost': balances.get(EntitlementLedger.BOOST, 0),
            'rewind': balances.get(EntitlementLedger.REWIND, 0),
        }
        return row

    @extend_schema(summary=_('用户详情'))
    @action(detail=False, methods=['get'], url_path='users/detail')
    def users_detail(self, request):
        uid = request.query_params.get('user_id')
        user = User.objects.filter(id=uid, role='user').select_related('recommend_stat').first()
        if not user:
            return ApiResponse(message='not found', code=404)
        if not can_access_app(request.user, user.app_id or 'spark_main'):
            return ApiResponse(message=_('无权查看该 App 用户'), code=403)
        return ApiResponse(data=self._serialize_admin_user(user), message='ok')

    @extend_schema(summary=_('用户运营操作'))
    @action(detail=False, methods=['post'], url_path='users/action')
    def users_action(self, request):
        """Grant VIP / consumables / clear privileges / ban / unban for ops."""
        uid = request.data.get('user_id')
        action_name = request.data.get('action')
        user = User.objects.filter(id=uid, role='user').first()
        if not user:
            return ApiResponse(message='not found', code=404)
        if not can_access_app(request.user, user.app_id or 'spark_main'):
            return ApiResponse(message=_('无权操作该 App 用户'), code=403)
        if action_name == 'grant_vip':
            tier = request.data.get('tier') or 'gold'
            if tier not in ('plus', 'gold', 'platinum'):
                return ApiResponse(message='invalid tier', code=400)
            days = int(request.data.get('days') or 0)
            if days <= 0:
                unit = (request.data.get('unit') or 'day').lower()
                amount = int(request.data.get('amount') or request.data.get('quantity') or 1)
                days = amount * 30 if unit in ('month', 'months', 'm') else amount
            if days <= 0:
                return ApiResponse(message='invalid duration', code=400)
            user.vip_tier = tier
            base = user.vip_expire_at if user.vip_expire_at and user.vip_expire_at > timezone.now() else timezone.now()
            user.vip_expire_at = base + timedelta(days=days)
            user.has_recharged = True
            user.save(update_fields=['vip_tier', 'vip_expire_at', 'has_recharged'])
            apply_vip_subscription_grants(user, tier)
            from tools.spark_helpers import top_up_daily_entitlements_after_vip
            top_up_daily_entitlements_after_vip(user)
            return ApiResponse(data={'user': self._serialize_admin_user(user)}, message='ok')
        if action_name == 'grant_entitlement':
            kind = request.data.get('kind') or request.data.get('tier') or ''
            kind_map = {
                'super_like': EntitlementLedger.SUPER_LIKE,
                'boost': EntitlementLedger.BOOST,
                'rewind': EntitlementLedger.REWIND,
            }
            if kind not in kind_map:
                return ApiResponse(message='invalid kind', code=400)
            qty = int(request.data.get('quantity') or request.data.get('amount') or 1)
            if qty <= 0:
                return ApiResponse(message='invalid quantity', code=400)
            grant_ledger(user, kind_map[kind], qty, period_key='purchased')
            return ApiResponse(data={'user': self._serialize_admin_user(user)}, message='ok')
        if action_name == 'clear_vip':
            user.vip_tier = User.VIP_NONE
            user.vip_expire_at = None
            user.save(update_fields=['vip_tier', 'vip_expire_at'])
            clear_vip_grant_balances(user)
            return ApiResponse(data={'user': self._serialize_admin_user(user)}, message='ok')
        if action_name == 'ban':
            user.status = 0
            user.save(update_fields=['status'])
            return ApiResponse(message='ok')
        if action_name == 'unban':
            user.status = 1
            user.save(update_fields=['status'])
            return ApiResponse(message='ok')
        if action_name == 'force_logout':
            from tools.token_tools import CustomTokenTool
            try:
                CustomTokenTool.delete_user_all_tokens(user.id)
            except Exception:
                pass
            return ApiResponse(message='ok')
        if action_name == 'reset_daily':
            ensure_daily_likes(user)
            ensure_daily_feed(user)
            day = period_day_key()
            for kind in (EntitlementLedger.DAILY_LIKE, EntitlementLedger.DAILY_FEED):
                EntitlementLedger.objects.filter(user=user, kind=kind, period_key=day).delete()
            ensure_daily_likes(user)
            ensure_daily_feed(user)
            return ApiResponse(data={'user': self._serialize_admin_user(user)}, message='ok')
        if action_name == 'mark_verified':
            user.is_verified = bool(request.data.get('verified', True))
            user.save(update_fields=['is_verified', 'updated_at'])
            return ApiResponse(data={'user': self._serialize_admin_user(user)}, message='ok')
        if action_name == 'select_decide':
            from models.models import SelectQueue
            row = SelectQueue.objects.filter(user=user, app_id=user.app_id or 'spark_main').first()
            if not row:
                return ApiResponse(code=404, message='no_select_application')
            approve = bool(request.data.get('approve', True))
            row.status = SelectQueue.STATUS_SELECTED if approve else SelectQueue.STATUS_REJECTED
            row.save(update_fields=['status', 'updated_at'])
            return ApiResponse(data={'status': row.status}, message='ok')
        return ApiResponse(message='unknown action', code=400)

    @extend_schema(summary=_('聊天会话列表'))
    @action(detail=False, methods=['get'], url_path='chats')
    def chats(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        q = (request.query_params.get('q') or '').strip()
        user_id = request.query_params.get('user_id')
        scope = self._app_scope(request, app_id)
        # conversations where either peer is in app scope
        if 'app_id__in' in scope:
            app_ids = scope['app_id__in']
            qs = Conversation.objects.filter(
                Q(user_a__app_id__in=app_ids) | Q(user_b__app_id__in=app_ids)
            )
        else:
            aid = scope.get('app_id', app_id)
            qs = Conversation.objects.filter(
                Q(user_a__app_id=aid) | Q(user_b__app_id=aid)
            )
        qs = qs.select_related('user_a', 'user_b', 'match').annotate(
            message_count=Count('messages')
        ).order_by('-last_at', '-id')
        origin_f = request.query_params.get('origin')
        if origin_f:
            qs = qs.filter(origin=origin_f)
        if user_id:
            qs = qs.filter(Q(user_a_id=user_id) | Q(user_b_id=user_id))
        elif q:
            user_q = Q(email__icontains=q) | Q(nickname__icontains=q) | Q(username__icontains=q)
            if q.isdigit():
                user_q = user_q | Q(id=int(q))
            matched_ids = list(
                User.objects.filter(**scope, role='user').filter(user_q).values_list('id', flat=True)[:500]
            )
            if not matched_ids:
                return ApiResponse(
                    data=[],
                    pagination={'page': 1, 'page_size': 20, 'total': 0, 'total_pages': 0},
                    message='ok',
                )
            qs = qs.filter(Q(user_a_id__in=matched_ids) | Q(user_b_id__in=matched_ids))
        page = CustomPagination()
        result = page.paginate_queryset(qs, request)
        data = []
        for c in result:
            messaging_mode = ''
            qa_status = None
            if c.match_id and c.match:
                messaging_mode = c.match.messaging_mode or ''
                try:
                    qa = MatchQA.objects.filter(match_id=c.match_id).first()
                    qa_status = qa.status if qa else None
                except Exception:
                    qa_status = None
            data.append({
                'id': c.id,
                'match_id': c.match_id,
                'origin': getattr(c, 'origin', 'dating') or 'dating',
                'messaging_mode': messaging_mode,
                'qa_status': qa_status,
                'user_a': {
                    'id': c.user_a_id,
                    'nickname': c.user_a.nickname or c.user_a.username,
                    'email': c.user_a.email,
                    'app_id': c.user_a.app_id,
                    'avatar_url': c.user_a.avatar_url or '',
                },
                'user_b': {
                    'id': c.user_b_id,
                    'nickname': c.user_b.nickname or c.user_b.username,
                    'email': c.user_b.email,
                    'app_id': c.user_b.app_id,
                    'avatar_url': c.user_b.avatar_url or '',
                },
                'last_message': c.last_message or '',
                'last_at': c.last_at.isoformat() if c.last_at else None,
                'created_at': c.created_at.isoformat() if c.created_at else None,
                'message_count': c.message_count,
            })
        return page.get_paginated_response(data)

    @extend_schema(summary=_('聊天消息记录'))
    @action(detail=False, methods=['get'], url_path='chats/messages')
    def chat_messages(self, request):
        cid = request.query_params.get('conversation_id')
        conv = Conversation.objects.select_related('user_a', 'user_b').filter(id=cid).first()
        if not conv:
            return ApiResponse(message='not found', code=404)
        for u in (conv.user_a, conv.user_b):
            if can_access_app(request.user, u.app_id or 'spark_main'):
                break
        else:
            return ApiResponse(message=_('无权查看该会话'), code=403)
        qs = Message.objects.filter(conversation=conv).select_related('sender').order_by('id')
        page = CustomPagination()
        result = page.paginate_queryset(qs, request)
        data = [{
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_nickname': m.sender.nickname or m.sender.username,
            'msg_type': m.msg_type,
            'content': m.content,
            'duration_ms': getattr(m, 'duration_ms', 0) or 0,
            'translated': m.translated or '',
            'is_read': m.is_read,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        } for m in result]
        resp = page.get_paginated_response(data)
        # attach conversation meta alongside results
        body = resp.data
        body['conversation'] = {
            'id': conv.id,
            'user_a_id': conv.user_a_id,
            'user_b_id': conv.user_b_id,
            'user_a_nickname': conv.user_a.nickname or conv.user_a.username,
            'user_b_nickname': conv.user_b.nickname or conv.user_b.username,
        }
        return resp

    @extend_schema(summary=_('SKU'))
    @action(detail=False, methods=['get', 'post'], url_path='skus')
    def skus(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        if request.method == 'GET':
            return ApiResponse(data={'list': list(SkuMap.objects.filter(**self._app_scope(request, app_id)).values())}, message='ok')
        write_app, err = self._write_app_id(request)
        if err:
            return err
        SkuMap.objects.update_or_create(
            app_id=write_app, product_id=request.data.get('product_id'),
            defaults={
                'sku_type': request.data.get('sku_type') or 'subscription',
                'tier': request.data.get('tier'),
                'quantity': int(request.data.get('quantity') or 1),
                'duration_days': request.data.get('duration_days'),
                'title': request.data.get('title') or request.data.get('product_id'),
                'is_active': bool(request.data.get('is_active', True)),
            },
        )
        return ApiResponse(message='ok', code=201)

    @extend_schema(summary=_('订单列表'))
    @action(detail=False, methods=['get'], url_path='orders')
    def orders(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        qs = Order.objects.filter(**self._app_scope(request, app_id)).order_by('-id')[:100]
        return ApiResponse(data={'list': [{
            'id': o.id, 'user_id': o.user_id, 'app_id': o.app_id,
            'product_id': o.product_id, 'platform': o.platform,
            'amount': float(o.amount), 'status': o.status, 'created_at': o.created_at.isoformat(),
        } for o in qs]}, message='ok')

    @extend_schema(summary=_('广告链接'))
    @action(detail=False, methods=['get', 'post'], url_path='ad-links')
    def ad_links(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        country = request.query_params.get('country') or request.data.get('country') or '*'
        if request.method == 'GET':
            qs = AdLink.objects.filter(**self._app_scope(request, app_id))
            if country and country != '*':
                qs = qs.filter(Q(country='*') | Q(country=country))
            return ApiResponse(data={'list': list(qs.values())}, message='ok')
        write_app, err = self._write_app_id(request)
        if err:
            return err
        AdLink.objects.create(
            app_id=write_app,
            country=country,
            name=request.data.get('name') or 'link',
            deep_link=request.data.get('deep_link') or '',
            tag=request.data.get('tag') or '',
            campaign_id=(request.data.get('campaign_id') or '').strip() or None,
            source=(request.data.get('source') or 'manual').strip() or 'manual',
        )
        return ApiResponse(message='ok', code=201)

    @extend_schema(summary=_('Google Ads 广告系列列表'))
    @action(detail=False, methods=['get'], url_path='google-ads/campaigns')
    def google_ads_campaigns(self, request):
        """Read cached campaign IDs + metrics; ?live=1 fetches without persisting."""
        app_id, err = self._write_app_id(request)
        if err:
            return err
        live = str(request.query_params.get('live') or '') in ('1', 'true', 'yes')
        if live:
            from tools.google_ads_service import fetch_campaigns
            result = fetch_campaigns(app_id=app_id, with_metrics=True)
            if not result.get('ok'):
                return ApiResponse(
                    code=400,
                    message=result.get('error') or 'fetch failed',
                    data={'list': [], 'configured': False},
                )
            return ApiResponse(data={
                'list': result.get('campaigns') or [],
                'customer_id': result.get('customer_id'),
                'live': True,
                'metrics': result.get('metrics'),
                'warning': result.get('warning'),
            }, message='ok')

        from tools.google_ads_service import serialize_campaign_row, is_configured
        qs = GoogleAdsCampaign.objects.filter(app_id=app_id).order_by('-impressions', 'campaign_id')
        return ApiResponse(data={
            'list': [serialize_campaign_row(r) for r in qs],
            'configured': is_configured(app_id),
            'live': False,
            'synced_at': qs.first().synced_at.isoformat() if qs.exists() and qs.first().synced_at else None,
        }, message='ok')

    @extend_schema(summary=_('同步 Google Ads 广告系列'))
    @action(detail=False, methods=['post'], url_path='google-ads/sync')
    def google_ads_sync(self, request):
        write_app, err = self._write_app_id(request)
        if err:
            return err
        from tools.google_ads_service import sync_campaigns_to_db, is_configured
        if not is_configured(write_app):
            return ApiResponse(
                code=400,
                message='Google Ads 未配置：请到「三方配置」填写 Developer Token / OAuth / Customer ID',
            )
        with_metrics = str(request.data.get('with_metrics', '1')) not in ('0', 'false', 'no')
        result = sync_campaigns_to_db(write_app, with_metrics=with_metrics)
        if not result.get('ok'):
            return ApiResponse(code=400, message=result.get('error') or 'sync failed', data=result)
        return ApiResponse(data=result, message='ok')

    @extend_schema(summary=_('Facebook Ads 广告系列列表'))
    @action(detail=False, methods=['get'], url_path='facebook-ads/campaigns')
    def facebook_ads_campaigns(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        live = str(request.query_params.get('live') or '') in ('1', 'true', 'yes')
        if live:
            from tools.facebook_ads_service import fetch_campaigns
            result = fetch_campaigns(app_id=app_id)
            if not result.get('ok'):
                return ApiResponse(
                    code=400,
                    message=result.get('error') or 'fetch failed',
                    data={'list': [], 'configured': False},
                )
            return ApiResponse(data={
                'list': result.get('campaigns') or [],
                'ad_account_id': result.get('ad_account_id'),
                'live': True,
            }, message='ok')

        from tools.facebook_ads_service import serialize_campaign_row, is_configured
        qs = FacebookAdsCampaign.objects.filter(app_id=app_id).order_by('-impressions', 'campaign_id')
        return ApiResponse(data={
            'list': [serialize_campaign_row(r) for r in qs],
            'configured': is_configured(app_id),
            'live': False,
            'ad_account_id': qs.first().ad_account_id if qs.exists() else '',
            'synced_at': qs.first().synced_at.isoformat() if qs.exists() and qs.first().synced_at else None,
        }, message='ok')

    @extend_schema(summary=_('同步 Facebook Ads 广告系列'))
    @action(detail=False, methods=['post'], url_path='facebook-ads/sync')
    def facebook_ads_sync(self, request):
        write_app, err = self._write_app_id(request)
        if err:
            return err
        from tools.facebook_ads_service import sync_campaigns_to_db, is_configured
        if not is_configured(write_app):
            return ApiResponse(
                code=400,
                message='Facebook Ads 未配置：请到「三方配置」填写 Access Token / Ad Account ID',
            )
        result = sync_campaigns_to_db(write_app)
        if not result.get('ok'):
            return ApiResponse(code=400, message=result.get('error') or 'sync failed', data=result)
        return ApiResponse(data=result, message='ok')

    @extend_schema(summary=_('广告归因列表'))
    @action(detail=False, methods=['get'], url_path='ad-attributions')
    def ad_attributions(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        from tools.attribution_service import serialize_attribution
        qs = AdAttribution.objects.filter(**self._app_scope(request, app_id)).order_by('-id')
        status = (request.query_params.get('status') or '').strip()
        platform = (request.query_params.get('platform') or '').strip()
        if status and status != '*':
            qs = qs.filter(status=status)
        if platform and platform != '*':
            qs = qs.filter(platform=platform)
        q = (request.query_params.get('q') or '').strip()
        if q:
            qs = qs.filter(
                Q(campaign_id__icontains=q)
                | Q(campaign_name__icontains=q)
                | Q(click_id__icontains=q)
                | Q(tag__icontains=q)
                | Q(utm_campaign__icontains=q)
            )
        limit = min(int(request.query_params.get('limit') or 100), 500)
        rows = list(qs[:limit])
        return ApiResponse(data={
            'list': [serialize_attribution(r) for r in rows],
            'total': qs.count(),
        }, message='ok')

    @extend_schema(summary=_('解算 / 处理广告归因'))
    @action(detail=False, methods=['post'], url_path='ad-attributions/resolve')
    def ad_attributions_resolve(self, request):
        write_app, err = self._write_app_id(request)
        if err:
            return err
        from tools.attribution_service import (
            resolve_attribution, try_auto_match, batch_auto_match, serialize_attribution,
            STATUS_RESOLVED,
        )
        action_name = (request.data.get('action') or 'resolve').strip()
        if action_name == 'auto_match_all':
            result = batch_auto_match(write_app, limit=int(request.data.get('limit') or 200))
            return ApiResponse(data=result, message='ok')

        attr_id = request.data.get('id')
        if not attr_id:
            return ApiResponse(code=400, message='id required')
        row = AdAttribution.objects.filter(id=attr_id, **self._app_scope(request, write_app)).first()
        if not row:
            # also allow exact app write scope
            row = AdAttribution.objects.filter(id=attr_id, app_id=write_app).first()
        if not row:
            return ApiResponse(code=404, message='attribution not found')

        if action_name == 'auto_match':
            try_auto_match(row)
            row.refresh_from_db()
            return ApiResponse(data=serialize_attribution(row), message='ok')

        resolve_attribution(
            row,
            admin_user=request.user,
            status=request.data.get('status') or STATUS_RESOLVED,
            note=request.data.get('note') or '',
            campaign_id=request.data.get('campaign_id'),
            platform=request.data.get('platform'),
            user_id=request.data.get('user_id'),
        )
        row.refresh_from_db()
        return ApiResponse(data=serialize_attribution(row), message='ok')

    @extend_schema(summary=_('内容安全'))
    @action(detail=False, methods=['get', 'post'], url_path='safety')
    def safety(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        app_ids = accessible_app_ids(request.user) if is_all_app(app_id) else [app_id]
        if request.method == 'GET':
            pending = UserPhoto.objects.filter(
                audit_status='pending', user__app_id__in=app_ids,
            ).select_related('user').order_by('-id')[:50]
            reports = Report.objects.filter(
                Q(app_id__in=app_ids) | Q(reporter__app_id__in=app_ids) | Q(target_user__app_id__in=app_ids)
            ).order_by('-id')
            return ApiResponse(data={
                'reports': list(reports.values()[:50]),
                'words': list(WordFilter.objects.filter(app_id__in=app_ids).values()),
                'domains': list(DomainWhitelist.objects.filter(app_id__in=app_ids).values()),
                'photos': [{
                    'id': p.id, 'url': p.url, 'user_id': p.user_id,
                    'nickname': p.user.nickname or p.user.username,
                    'audit_status': p.audit_status, 'created_at': p.created_at.isoformat(),
                    'app_id': p.user.app_id,
                } for p in pending],
            }, message='ok')
        write_app, err = self._write_app_id(request)
        if err:
            return err
        kind = request.data.get('kind')
        if kind == 'word':
            WordFilter.objects.create(
                app_id=write_app,
                word=request.data.get('word'),
                country=request.data.get('country') or '*',
                kind=(request.data.get('filter_kind') or request.data.get('word_kind') or 'ban'),
            )
            from tools.spark_helpers import bump_wordfilter_cache
            bump_wordfilter_cache()
        elif kind == 'domain':
            DomainWhitelist.objects.create(app_id=write_app, domain=request.data.get('domain'))
        elif kind == 'report_status':
            Report.objects.filter(
                id=request.data.get('id')
            ).filter(
                Q(app_id__in=app_ids) | Q(reporter__app_id__in=app_ids) | Q(target_user__app_id__in=app_ids)
            ).update(status=request.data.get('status') or 'resolved')
        elif kind == 'photo_status':
            photo = UserPhoto.objects.filter(
                id=request.data.get('id'), user__app_id__in=app_ids,
            ).select_related('user').first()
            if not photo:
                return ApiResponse(message='not found', code=404)
            status = request.data.get('status') or 'approved'
            if status not in ('approved', 'rejected', 'pending'):
                return ApiResponse(message='invalid status', code=400)
            photo.audit_status = status
            photo.save(update_fields=['audit_status'])
            if status == 'approved' and (photo.is_primary or not photo.user.avatar_url):
                photo.user.avatar_url = photo.url
                photo.user.save(update_fields=['avatar_url'])
            if status == 'rejected' and photo.user.avatar_url == photo.url:
                alt = UserPhoto.objects.filter(user=photo.user, audit_status='approved').order_by('sort_order', 'id').first()
                photo.user.avatar_url = alt.url if alt else ''
                photo.user.save(update_fields=['avatar_url'])
        return ApiResponse(message='ok')

    @extend_schema(summary=_('App 配置'))
    @action(detail=False, methods=['get', 'post'], url_path='app-config')
    def app_config(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        obj, _ = AppConfig.objects.get_or_create(app_id=app_id, defaults={'name': 'SPARK'})
        if request.method == 'GET':
            return ApiResponse(data={
                'app_id': obj.app_id, 'name': obj.name, 'tos_url': obj.tos_url,
                'privacy_url': obj.privacy_url, 'config': obj.config,
            }, message='ok')
        for f in ('name', 'tos_url', 'privacy_url'):
            if f in request.data:
                setattr(obj, f, request.data.get(f))
        if 'config' in request.data:
            obj.config = request.data.get('config')
        obj.save()
        return ApiResponse(message='ok')

    @extend_schema(summary=_('产品规则 product_profile'))
    @action(detail=False, methods=['get', 'post'], url_path='product-profile')
    def product_profile(self, request):
        """Read/update messaging_mode, match_open_hours, display_tiers, feature flags."""
        if request.method == 'GET':
            app_id = request.query_params.get('app_id') or 'spark_main'
            if not can_access_app(request.user, app_id):
                return ApiResponse(code=403, message='forbidden')
            return ApiResponse(data={
                'app_id': app_id,
                'product_profile': get_product_profile(app_id),
            }, message='ok')
        write_app, err = self._write_app_id(request)
        if err:
            return err
        patch = request.data.get('product_profile')
        if patch is None:
            # allow flat body keys
            patch = {
                k: request.data[k]
                for k in (
                    'messaging_mode', 'match_open_hours', 'extend_enabled',
                    'compliment_enabled', 'feed_same_app_only', 'display_tiers',
                )
                if k in request.data
            }
        if not isinstance(patch, dict):
            return ApiResponse(code=400, message='product_profile object required')
        from tools.spark_helpers import validate_product_profile
        cleaned, errors = validate_product_profile(patch)
        if errors:
            return ApiResponse(code=400, message='invalid_product_profile', data={'errors': errors})
        profile = set_product_profile(write_app, cleaned)
        return ApiResponse(data={'app_id': write_app, 'product_profile': profile}, message='ok')

    @extend_schema(summary=_('发版审核'))
    @action(detail=False, methods=['get', 'post'], url_path='review-mode')
    def review_mode(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        if request.method == 'GET':
            return ApiResponse(data={'list': list(ReviewMode.objects.filter(**self._app_scope(request, app_id)).values())}, message='ok')
        write_app, err = self._write_app_id(request)
        if err:
            return err
        from tools.app_modules import DEFAULT_PACKAGE_BY_APP
        default_pkg = DEFAULT_PACKAGE_BY_APP.get(write_app, 'app.spark')
        ReviewMode.objects.update_or_create(
            app_id=write_app,
            platform=request.data.get('platform') or 'ios',
            package_name=request.data.get('package_name') or default_pkg,
            version=request.data.get('version') or '1.0.0',
            defaults={'enabled': bool(request.data.get('enabled'))},
        )
        return ApiResponse(message='ok')

    @extend_schema(summary=_('国家配置'))
    @action(detail=False, methods=['get', 'post'], url_path='country-config')
    def country_config(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or 'spark_main'
        if request.method == 'GET':
            return ApiResponse(data={'list': list(CountryConfig.objects.filter(**self._app_scope(request, app_id)).values())}, message='ok')
        write_app, err = self._write_app_id(request)
        if err:
            return err
        CountryConfig.objects.update_or_create(
            app_id=write_app, country=request.data.get('country') or '*',
            defaults={'config': request.data.get('config') or {}},
        )
        return ApiResponse(message='ok')

    @extend_schema(summary=_('埋点字典'))
    @action(detail=False, methods=['get'], url_path='events/dict')
    def events_dict(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        from tools.analytics_service import event_breakdown
        from tools.event_dict import full_dictionary
        data = event_breakdown(
            self._app_scope(request, app_id),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
        )
        return ApiResponse(data={
            'events': [r['event'] for r in data['list']],
            'list': data['list'],
            'pv_uv': data.get('pv_uv') or {},
            'catalog': full_dictionary(),
            'date_from': data['date_from'],
            'date_to': data['date_to'],
        }, message='ok')

    @extend_schema(summary=_('Analytics 总览'))
    @action(detail=False, methods=['get'], url_path='analytics/overview')
    def analytics_overview(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        from tools.analytics_service import overview
        data = overview(
            self._app_scope(request, app_id),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
        )
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('Analytics 事件排行'))
    @action(detail=False, methods=['get'], url_path='analytics/events')
    def analytics_events(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        from tools.analytics_service import event_breakdown
        data = event_breakdown(
            self._app_scope(request, app_id),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
            limit=int(request.query_params.get('limit') or 200),
        )
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('Analytics 转化漏斗'))
    @action(detail=False, methods=['get'], url_path='analytics/funnel')
    def analytics_funnel(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        from tools.analytics_service import funnel, DEFAULT_FUNNEL
        raw_steps = (request.query_params.get('steps') or '').strip()
        steps = [s for s in raw_steps.split(',') if s.strip()] if raw_steps else None
        data = funnel(
            self._app_scope(request, app_id),
            steps=steps,
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
        )
        data['default_steps'] = list(DEFAULT_FUNNEL)
        return ApiResponse(data=data, message='ok')

    @extend_schema(summary=_('Analytics 事件流'))
    @action(detail=False, methods=['get'], url_path='analytics/stream')
    def analytics_stream(self, request):
        app_id = request.query_params.get('app_id') or 'spark_main'
        from tools.analytics_service import event_stream
        data = event_stream(
            self._app_scope(request, app_id),
            date_from=request.query_params.get('date_from'),
            date_to=request.query_params.get('date_to'),
            event=request.query_params.get('event') or None,
            q=request.query_params.get('q') or None,
            limit=int(request.query_params.get('limit') or 100),
            offset=int(request.query_params.get('offset') or 0),
        )
        return ApiResponse(data=data, message='ok')

    def _serialize_push_config(self, row):
        return {
            'id': row.id,
            'app_id': row.app_id,
            'locale': row.locale,
            'event_type': row.event_type,
            'recall_day': row.recall_day,
            'title_template': row.title_template,
            'body_template': row.body_template,
            'enabled': row.enabled,
            'daily_push_cap': row.daily_push_cap,
            'delay_minutes_min': row.delay_minutes_min,
            'delay_minutes_max': row.delay_minutes_max,
            'deep_link': row.deep_link,
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
            'created_at': row.created_at.isoformat() if row.created_at else None,
        }

    @extend_schema(summary=_('系统通知配置列表'))
    @action(detail=False, methods=['get', 'post'], url_path='push-configs')
    def push_configs(self, request):
        app_id = request.query_params.get('app_id') or request.data.get('app_id') or ''
        if request.method == 'GET':
            qs = SystemPushConfig.objects.all().order_by('app_id', 'locale', 'event_type', 'recall_day')
            if app_id and not is_all_app(app_id):
                qs = qs.filter(app_id=app_id)
            elif app_id and is_all_app(app_id):
                qs = qs.filter(**self._app_scope(request, app_id))
            locale = request.query_params.get('locale')
            event_type = request.query_params.get('event_type')
            if locale and locale != '*':
                qs = qs.filter(locale=locale.lower())
            if event_type:
                qs = qs.filter(event_type=event_type)
            return ApiResponse(data={
                'list': [self._serialize_push_config(r) for r in qs],
            }, message='ok')

        write_app, err = self._write_app_id(request)
        if err:
            return err
        locale = (request.data.get('locale') or 'en').strip().lower()
        if not locale or locale == '*':
            return ApiResponse(code=400, message='locale required (not *)')
        event_type = (request.data.get('event_type') or '').strip()
        valid_events = {c[0] for c in SystemPushConfig.EVENT_CHOICES}
        if event_type not in valid_events:
            return ApiResponse(code=400, message='invalid event_type')
        recall_day = int(request.data.get('recall_day') or 0)
        if event_type == SystemPushConfig.EVENT_SILENT_RECALL:
            if recall_day not in (1, 3, 7):
                return ApiResponse(code=400, message='recall_day must be 1, 3, or 7')
        else:
            recall_day = 0
        clash = SystemPushConfig.objects.filter(
            app_id=write_app, locale=locale, event_type=event_type, recall_day=recall_day,
        ).exists()
        if clash:
            return ApiResponse(code=400, message='duplicate config for app/locale/event')
        row = SystemPushConfig.objects.create(
            app_id=write_app,
            locale=locale[:16],
            event_type=event_type,
            recall_day=recall_day,
            title_template=(request.data.get('title_template') or '')[:256],
            body_template=(request.data.get('body_template') or '')[:512],
            enabled=bool(request.data.get('enabled', True)),
            daily_push_cap=max(1, int(request.data.get('daily_push_cap') or 1)),
            delay_minutes_min=max(0, int(request.data.get('delay_minutes_min') or 0)),
            delay_minutes_max=max(0, int(request.data.get('delay_minutes_max') or 0)),
            deep_link=(request.data.get('deep_link') or '/pages/chat/index')[:256],
        )
        return ApiResponse(data=self._serialize_push_config(row), message='ok', code=201)

    @extend_schema(summary=_('系统通知配置详情'))
    @action(detail=False, methods=['put', 'patch', 'delete'], url_path=r'push-configs/(?P<cid>[^/.]+)')
    def push_config_item(self, request, cid=None):
        row = SystemPushConfig.objects.filter(id=cid).first()
        if not row:
            return ApiResponse(message='not found', code=404)
        if not can_access_app(request.user, row.app_id):
            return ApiResponse(code=403, message='forbidden')
        if request.method == 'DELETE':
            row.delete()
            return ApiResponse(message='ok')

        locale = request.data.get('locale')
        if locale is not None:
            locale = str(locale).strip().lower()
            if not locale or locale == '*':
                return ApiResponse(code=400, message='locale required (not *)')
            row.locale = locale[:16]
        if 'event_type' in request.data:
            event_type = (request.data.get('event_type') or '').strip()
            valid_events = {c[0] for c in SystemPushConfig.EVENT_CHOICES}
            if event_type not in valid_events:
                return ApiResponse(code=400, message='invalid event_type')
            row.event_type = event_type
        if 'recall_day' in request.data or 'event_type' in request.data:
            recall_day = int(request.data.get('recall_day', row.recall_day) or 0)
            if row.event_type == SystemPushConfig.EVENT_SILENT_RECALL:
                if recall_day not in (1, 3, 7):
                    return ApiResponse(code=400, message='recall_day must be 1, 3, or 7')
                row.recall_day = recall_day
            else:
                row.recall_day = 0
        for field in ('title_template', 'body_template', 'deep_link'):
            if field in request.data:
                setattr(row, field, (request.data.get(field) or '')[:512 if field == 'body_template' else 256])
        if 'enabled' in request.data:
            row.enabled = bool(request.data.get('enabled'))
        if 'daily_push_cap' in request.data:
            row.daily_push_cap = max(1, int(request.data.get('daily_push_cap') or 1))
        if 'delay_minutes_min' in request.data:
            row.delay_minutes_min = max(0, int(request.data.get('delay_minutes_min') or 0))
        if 'delay_minutes_max' in request.data:
            row.delay_minutes_max = max(0, int(request.data.get('delay_minutes_max') or 0))
        if 'app_id' in request.data:
            write_app, err = self._write_app_id(request)
            if err:
                return err
            row.app_id = write_app
        clash = SystemPushConfig.objects.filter(
            app_id=row.app_id, locale=row.locale, event_type=row.event_type, recall_day=row.recall_day,
        ).exclude(id=row.id).exists()
        if clash:
            return ApiResponse(code=400, message='duplicate config for app/locale/event')
        row.save()
        return ApiResponse(data=self._serialize_push_config(row), message='ok')

    @extend_schema(summary=_('功能模块目录'))
    @action(detail=False, methods=['get'], url_path='app-modules')
    def app_modules(self, request):
        return ApiResponse(data=modules_catalog_payload(), message='ok')

    @extend_schema(summary=_('APP 配置列表'))
    @action(detail=False, methods=['get', 'post', 'delete'], url_path='app-list')
    def app_list(self, request):
        if request.method == 'GET':
            rows = [
                serialize_app_config_row(a)
                for a in AppConfig.objects.all().order_by('app_id')
                if can_access_app(request.user, a.app_id)
            ]
            return ApiResponse(data={'list': rows}, message='ok')

        if request.method == 'DELETE':
            app_id = request.query_params.get('app_id') or request.data.get('app_id')
            if not app_id:
                return ApiResponse(code=400, message='app_id required')
            if not can_access_app(request.user, app_id):
                return ApiResponse(code=403, message='forbidden')
            obj = AppConfig.objects.filter(app_id=app_id).first()
            if not obj:
                return ApiResponse(code=404, message='not found')
            obj.delete()
            return ApiResponse(message='ok')

        # POST create / update
        app_id = (request.data.get('app_id') or '').strip()
        if not app_id:
            return ApiResponse(code=400, message='app_id required')
        exists = AppConfig.objects.filter(app_id=app_id).exists()
        is_super = getattr(request.user, 'role', None) == 'super_admin'
        if exists:
            if not can_access_app(request.user, app_id):
                return ApiResponse(code=403, message='forbidden')
        elif not is_super and not can_access_app(request.user, app_id):
            # only super_admin (or users who already have this app in scope) may create
            return ApiResponse(code=403, message='仅超管可新增 APP')

        name = (request.data.get('name') or app_id).strip()
        from tools.app_modules import DEFAULT_PACKAGE_BY_APP
        package_name = (request.data.get('package_name') or '').strip() or DEFAULT_PACKAGE_BY_APP.get(app_id) or None
        modules = request.data.get('enabled_modules')
        if modules is None:
            modules = default_enabled_modules()
        if not isinstance(modules, list):
            return ApiResponse(code=400, message='enabled_modules must be a list')
        modules = [k for k in modules if k in ALL_MODULE_KEYS]

        obj, created = AppConfig.objects.get_or_create(
            app_id=app_id,
            defaults={
                'name': name,
                'package_name': package_name,
                'tos_url': request.data.get('tos_url') or '',
                'privacy_url': request.data.get('privacy_url') or '',
                'config': {'enabled_modules': modules},
            },
        )
        if not created:
            obj.name = name
            if 'package_name' in request.data:
                obj.package_name = package_name
            if 'tos_url' in request.data:
                obj.tos_url = request.data.get('tos_url') or ''
            if 'privacy_url' in request.data:
                obj.privacy_url = request.data.get('privacy_url') or ''
            cfg = dict(obj.config or {})
            cfg['enabled_modules'] = modules
            obj.config = cfg
            obj.save()

        patch = request.data.get('product_profile')
        if isinstance(patch, dict) and patch:
            set_product_profile(app_id, patch)

        maps_patch = request.data.get('maps')
        if isinstance(maps_patch, dict):
            from tools.maps_helpers import normalize_maps_config
            obj = AppConfig.objects.filter(app_id=app_id).first()
            if obj:
                cfg = dict(obj.config or {})
                cfg['maps'] = normalize_maps_config(maps_patch)
                obj.config = cfg
                obj.save(update_fields=['config'])

        obj = AppConfig.objects.filter(app_id=app_id).first()
        return ApiResponse(
            data=serialize_app_config_row(obj),
            message='ok',
            code=201 if created else 200,
        )

    @extend_schema(summary=_('三方供应商配置列表'))
    @action(detail=False, methods=['get'], url_path='providers')
    def providers(self, request):
        """Card grid: catalog + status for current workspace app (global providers included)."""
        app_id, err = self._write_app_id(request)
        if err:
            return err
        from tools.provider_helpers import list_provider_statuses
        return ApiResponse(data={
            'app_id': app_id,
            'list': list_provider_statuses(app_id),
        }, message='ok')

    @extend_schema(summary=_('三方供应商配置详情 / 保存'))
    @action(detail=False, methods=['get', 'post'], url_path=r'providers/(?P<provider_key>[^/.]+)')
    def provider_detail(self, request, provider_key=None):
        from tools.provider_catalog import (
            get_provider_def, serialize_config_for_admin, merge_config_update, config_status,
            GLOBAL_APP_ID,
        )
        from tools.provider_helpers import resolve_storage_app_id, sync_maps_client_keys_to_app

        pdef = get_provider_def(provider_key)
        if not pdef:
            return ApiResponse(code=404, message='unknown provider')

        if request.method == 'GET':
            app_id = resolve_request_app_id(request, default='spark_main')
            if not can_access_app(request.user, app_id):
                return ApiResponse(message='无权访问该 App', code=403)
            storage_app = resolve_storage_app_id(provider_key, concrete_app_id(request.user, app_id))
            row = ProviderConfig.objects.filter(provider_key=provider_key, app_id=storage_app).first()
            cfg = dict(row.config or {}) if row else {}
            reveal = str(request.query_params.get('reveal') or '') in ('1', 'true', 'yes')
            return ApiResponse(data={
                'provider': pdef,
                'app_id': storage_app,
                'config': serialize_config_for_admin(provider_key, cfg, reveal=reveal),
                'status': config_status(provider_key, cfg),
                'notes': (row.notes if row else '') or '',
                'updated_at': row.updated_at.isoformat() if row and row.updated_at else None,
            }, message='ok')

        write_app, err = self._write_app_id(request)
        if err:
            return err
        storage_app = resolve_storage_app_id(provider_key, write_app)
        if pdef.get('scope') == 'global':
            storage_app = GLOBAL_APP_ID

        row = ProviderConfig.objects.filter(provider_key=provider_key, app_id=storage_app).first()
        existing = dict(row.config or {}) if row else {}
        patch = request.data.get('config')
        if not isinstance(patch, dict):
            return ApiResponse(code=400, message='config object required')
        merged = merge_config_update(provider_key, existing, patch)
        notes = request.data.get('notes')
        if notes is None and row:
            notes = row.notes
        notes = (notes or '')[:512]

        obj, _created = ProviderConfig.objects.update_or_create(
            app_id=storage_app,
            provider_key=provider_key,
            defaults={'config': merged, 'notes': notes},
        )
        if storage_app != GLOBAL_APP_ID:
            sync_maps_client_keys_to_app(storage_app, provider_key, merged)

        return ApiResponse(data={
            'provider': pdef,
            'app_id': storage_app,
            'config': serialize_config_for_admin(provider_key, merged, reveal=False),
            'status': config_status(provider_key, merged),
            'notes': obj.notes or '',
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
        }, message='ok')

    @extend_schema(summary=_('三方供应商连通性测试'))
    @action(detail=False, methods=['post'], url_path=r'providers/(?P<provider_key>[^/.]+)/test')
    def provider_test(self, request, provider_key=None):
        """Test live credentials. Currently: google_translate, google_ads."""
        write_app, err = self._write_app_id(request)
        if err:
            return err
        if provider_key == 'google_translate':
            from tools.translate_service import test_connection
            sample = (request.data.get('sample') or 'Hello').strip()[:200] or 'Hello'
            result = test_connection(sample)
            if result.get('ok'):
                return ApiResponse(data=result, message='ok')
            return ApiResponse(
                code=400,
                message=result.get('error') or 'translate test failed',
                data=result,
            )
        if provider_key == 'google_ads':
            from tools.google_ads_service import test_connection as ads_test
            result = ads_test(write_app)
            if result.get('ok'):
                return ApiResponse(data=result, message='ok')
            return ApiResponse(
                code=400,
                message=result.get('error') or 'google ads test failed',
                data=result,
            )
        if provider_key == 'facebook_ads':
            from tools.facebook_ads_service import test_connection as fb_test
            result = fb_test(write_app)
            if result.get('ok'):
                return ApiResponse(data=result, message='ok')
            return ApiResponse(
                code=400,
                message=result.get('error') or 'facebook ads test failed',
                data=result,
            )
        return ApiResponse(code=400, message=f'test not supported for {provider_key}')

    # ─── Parallel social domains (admin) ────────────────────────────────────

    @extend_schema(summary=_('速配池监控'))
    @action(detail=False, methods=['get'], url_path='quick-match')
    def quick_match_admin(self, request):
        app_id, err = self._app_id(request)
        if err:
            return err
        scope = self._app_scope(request, app_id)
        waiting = QmTicket.objects.filter(**scope, status=QmTicket.STATUS_WAITING).count()
        pairs_qs = QmPair.objects.filter(**scope).select_related(
            'user_a', 'user_b', 'conversation',
        ).order_by('-matched_at')
        status_f = request.query_params.get('status')
        if status_f:
            pairs_qs = pairs_qs.filter(status=status_f)
        page = CustomPagination()
        result = page.paginate_queryset(pairs_qs, request)
        data = [{
            'id': p.id,
            'app_id': p.app_id,
            'status': p.status,
            'conversation_id': p.conversation_id,
            'matched_at': p.matched_at.isoformat() if p.matched_at else None,
            'ended_at': p.ended_at.isoformat() if p.ended_at else None,
            'user_a': {
                'id': p.user_a_id,
                'nickname': p.user_a.nickname or p.user_a.username,
            },
            'user_b': {
                'id': p.user_b_id,
                'nickname': p.user_b.nickname or p.user_b.username,
            },
        } for p in result]
        tickets = list(
            QmTicket.objects.filter(**scope, status=QmTicket.STATUS_WAITING)
            .select_related('user').order_by('created_at')[:50]
        )
        ticket_rows = [{
            'id': t.id,
            'user_id': t.user_id,
            'nickname': t.user.nickname or t.user.username,
            'status': t.status,
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'expire_at': t.expire_at.isoformat() if t.expire_at else None,
        } for t in tickets]
        resp = page.get_paginated_response(data)
        body = resp.data
        body['waiting_count'] = waiting
        body['waiting_tickets'] = ticket_rows
        return resp

    @extend_schema(summary=_('速配强制操作'))
    @action(detail=False, methods=['post'], url_path='quick-match/action')
    def quick_match_action(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        action_name = request.data.get('action')
        if action_name == 'cancel_ticket':
            tid = request.data.get('ticket_id')
            t = QmTicket.objects.filter(id=tid, app_id=app_id, status=QmTicket.STATUS_WAITING).first()
            if not t:
                return ApiResponse(message='not found', code=404)
            t.status = QmTicket.STATUS_CANCELLED
            t.save(update_fields=['status'])
            return ApiResponse(data={'ticket_id': t.id, 'status': t.status}, message='ok')
        if action_name == 'end_pair':
            pid = request.data.get('pair_id')
            p = QmPair.objects.filter(id=pid, app_id=app_id, status=QmPair.STATUS_ACTIVE).first()
            if not p:
                return ApiResponse(message='not found', code=404)
            p.status = QmPair.STATUS_ENDED
            p.ended_at = timezone.now()
            p.save(update_fields=['status', 'ended_at'])
            return ApiResponse(data={'pair_id': p.id, 'status': p.status}, message='ok')
        if action_name == 'purge_stale':
            now = timezone.now()
            n = QmTicket.objects.filter(
                app_id=app_id, status=QmTicket.STATUS_WAITING, expire_at__lt=now,
            ).update(status=QmTicket.STATUS_CANCELLED)
            return ApiResponse(data={'purged': n}, message='ok')
        return ApiResponse(message='unknown action', code=400)

    @extend_schema(summary=_('群聊列表'))
    @action(detail=False, methods=['get'], url_path='groups')
    def groups_admin(self, request):
        app_id, err = self._app_id(request)
        if err:
            return err
        scope = self._app_scope(request, app_id)
        qs = ChatRoom.objects.filter(**scope).select_related('owner').annotate(
            member_count=Count('members'),
            message_count=Count('messages'),
        ).order_by('-id')
        status_f = request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f)
        q = (request.query_params.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(owner__nickname__icontains=q))
        page = CustomPagination()
        result = page.paginate_queryset(qs, request)
        data = [{
            'id': r.id,
            'app_id': r.app_id,
            'name': r.name,
            'status': r.status,
            'avatar': r.avatar or '',
            'max_members': r.max_members,
            'member_count': r.member_count,
            'message_count': r.message_count,
            'owner_id': r.owner_id,
            'owner_nickname': r.owner.nickname or r.owner.username,
            'last_message': r.last_message or '',
            'last_at': r.last_at.isoformat() if r.last_at else None,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in result]
        return page.get_paginated_response(data)

    @extend_schema(summary=_('群聊详情 / 消息 / 状态'))
    @action(detail=False, methods=['get', 'post'], url_path=r'groups/(?P<rid>[^/.]+)')
    def group_admin_detail(self, request, rid=None):
        room = ChatRoom.objects.select_related('owner').filter(id=rid).first()
        if not room:
            return ApiResponse(message='not found', code=404)
        if not can_access_app(request.user, room.app_id or 'spark_main'):
            return ApiResponse(message=_('无权查看该群'), code=403)
        if request.method == 'POST':
            status = request.data.get('status')
            if status not in (
                ChatRoom.STATUS_ACTIVE, ChatRoom.STATUS_DISSOLVED, ChatRoom.STATUS_MUTED,
            ):
                return ApiResponse(message='invalid status', code=400)
            room.status = status
            room.save(update_fields=['status'])
            return ApiResponse(data={'id': room.id, 'status': room.status}, message='ok')
        members = [{
            'user_id': m.user_id,
            'role': m.role,
            'nickname': m.user.nickname or m.user.username,
            'joined_at': m.joined_at.isoformat() if m.joined_at else None,
        } for m in room.members.select_related('user').order_by('id')]
        msgs = ChatRoomMessage.objects.filter(room=room).select_related('sender').order_by('-id')[:100]
        messages = [{
            'id': m.id,
            'sender_id': m.sender_id,
            'sender_nickname': m.sender.nickname or m.sender.username,
            'msg_type': m.msg_type,
            'content': m.content,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        } for m in reversed(list(msgs))]
        return ApiResponse(data={
            'id': room.id,
            'app_id': room.app_id,
            'name': room.name,
            'status': room.status,
            'owner_id': room.owner_id,
            'members': members,
            'messages': messages,
        }, message='ok')

    @extend_schema(summary=_('社区话题'))
    @action(detail=False, methods=['get', 'post'], url_path='topics')
    def topics_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            rows = Topic.objects.filter(**scope).order_by('sort', 'id')
            return ApiResponse(data={'list': [{
                'id': t.id,
                'app_id': t.app_id,
                'title': t.title,
                'cover': t.cover or '',
                'sort': t.sort,
                'is_active': t.is_active,
                'created_at': t.created_at.isoformat() if t.created_at else None,
            } for t in rows]}, message='ok')
        app_id, err = self._write_app_id(request)
        if err:
            return err
        tid = request.data.get('id')
        title = (request.data.get('title') or '').strip()
        if not title and not tid:
            return ApiResponse(message='title required', code=400)
        if tid:
            t = Topic.objects.filter(id=tid, app_id=app_id).first()
            if not t:
                return ApiResponse(message='not found', code=404)
            if title:
                t.title = title[:128]
            if 'cover' in request.data:
                t.cover = (request.data.get('cover') or '')[:512]
            if 'sort' in request.data:
                t.sort = int(request.data.get('sort') or 0)
            if 'is_active' in request.data:
                t.is_active = bool(request.data.get('is_active'))
            t.save()
        else:
            t = Topic.objects.create(
                app_id=app_id,
                title=title[:128],
                cover=(request.data.get('cover') or '')[:512],
                sort=int(request.data.get('sort') or 0),
                is_active=bool(request.data.get('is_active', True)),
            )
        return ApiResponse(data={
            'id': t.id, 'app_id': t.app_id, 'title': t.title,
            'cover': t.cover, 'sort': t.sort, 'is_active': t.is_active,
        }, message='ok', code=201 if not tid else 200)

    @extend_schema(summary=_('社区内容审核'))
    @action(detail=False, methods=['get', 'post'], url_path='posts')
    def posts_admin(self, request):
        if request.method == 'GET':
            app_id, err = self._app_id(request)
            if err:
                return err
            scope = self._app_scope(request, app_id)
            qs = Post.objects.filter(**scope).select_related('author', 'topic').order_by('-id')
            post_type = request.query_params.get('post_type')
            if post_type:
                qs = qs.filter(post_type=post_type)
            status_f = request.query_params.get('status')
            if status_f:
                qs = qs.filter(status=status_f)
            q = (request.query_params.get('q') or '').strip()
            if q:
                qs = qs.filter(Q(text__icontains=q) | Q(author__nickname__icontains=q))
            page = CustomPagination()
            result = page.paginate_queryset(qs, request)
            data = [{
                'id': p.id,
                'app_id': p.app_id,
                'post_type': p.post_type,
                'status': p.status,
                'text': (p.text or '')[:200],
                'like_count': p.like_count,
                'comment_count': p.comment_count,
                'topic_id': p.topic_id,
                'topic_title': p.topic.title if p.topic_id else '',
                'author_id': p.author_id,
                'author_nickname': p.author.nickname or p.author.username,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            } for p in result]
            return page.get_paginated_response(data)
        app_id, err = self._write_app_id(request)
        if err:
            return err
        # batch hide/delete
        ids = request.data.get('ids') or []
        if ids and isinstance(ids, list):
            status = request.data.get('status') or Post.STATUS_HIDDEN
            if status not in (Post.STATUS_VISIBLE, Post.STATUS_HIDDEN, Post.STATUS_DELETED):
                return ApiResponse(message='invalid status', code=400)
            n = Post.objects.filter(id__in=ids, app_id=app_id).update(status=status)
            return ApiResponse(data={'updated': n, 'status': status}, message='ok')
        pid = request.data.get('id') or request.data.get('post_id')
        post = Post.objects.filter(id=pid, app_id=app_id).first()
        if not post:
            return ApiResponse(message='not found', code=404)
        status = request.data.get('status')
        if status not in (Post.STATUS_VISIBLE, Post.STATUS_HIDDEN, Post.STATUS_DELETED):
            return ApiResponse(message='invalid status', code=400)
        post.status = status
        post.save(update_fields=['status', 'updated_at'])
        return ApiResponse(data={'id': post.id, 'status': post.status}, message='ok')

    @extend_schema(summary=_('删除评论'))
    @action(detail=False, methods=['post'], url_path='posts/comments/delete')
    def posts_comment_delete(self, request):
        app_id, err = self._write_app_id(request)
        if err:
            return err
        cid = request.data.get('comment_id')
        c = PostComment.objects.select_related('post').filter(id=cid).first()
        if not c or c.post.app_id != app_id:
            return ApiResponse(message='not found', code=404)
        c.status = 'deleted'
        c.save(update_fields=['status'])
        return ApiResponse(data={'id': c.id, 'status': c.status}, message='ok')

