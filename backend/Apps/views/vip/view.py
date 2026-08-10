from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from django.utils.translation import gettext as _

from tools.permissions import IsTokenValid, RequireAppModule
from tools.utils import ApiResponse
from tools.spark_helpers import grant_ledger, serialize_user_card, period_day_key, spendable_balances, apply_vip_subscription_grants, get_product_profile
from tools.firebase_mock import write_order, write_payment
from models.models import SkuMap, Order, Payment, BoostSession, EntitlementLedger, User


MOCK_PRICES = {
    'plus_1m': {'price': '9.99', 'currency': 'USD', 'title': 'Plus 1 Month'},
    'plus_6m': {'price': '44.99', 'currency': 'USD', 'title': 'Plus 6 Months'},
    'plus_12m': {'price': '71.99', 'currency': 'USD', 'title': 'Plus 12 Months'},
    'gold_1m': {'price': '19.99', 'currency': 'USD', 'title': 'Gold 1 Month'},
    'gold_6m': {'price': '89.99', 'currency': 'USD', 'title': 'Gold 6 Months'},
    'gold_12m': {'price': '143.99', 'currency': 'USD', 'title': 'Gold 12 Months'},
    'platinum_1m': {'price': '29.99', 'currency': 'USD', 'title': 'Platinum 1 Month'},
    'platinum_6m': {'price': '134.99', 'currency': 'USD', 'title': 'Platinum 6 Months'},
    'platinum_12m': {'price': '215.99', 'currency': 'USD', 'title': 'Platinum 12 Months'},
    'super_like_3': {'price': '4.99', 'currency': 'USD', 'title': 'Super Like x3'},
    'super_like_5': {'price': '7.99', 'currency': 'USD', 'title': 'Super Like x5'},
    'super_like_15': {'price': '19.99', 'currency': 'USD', 'title': 'Super Like x15'},
    'boost_3': {'price': '9.99', 'currency': 'USD', 'title': 'Boost x3'},
    'boost_5': {'price': '14.99', 'currency': 'USD', 'title': 'Boost x5'},
    'boost_10': {'price': '24.99', 'currency': 'USD', 'title': 'Boost x10'},
    'extend_1': {'price': '3.99', 'currency': 'USD', 'title': 'Extend x1'},
    'extend_3': {'price': '8.99', 'currency': 'USD', 'title': 'Extend x3'},
    'extend_5': {'price': '12.99', 'currency': 'USD', 'title': 'Extend x5'},
    'rematch_1': {'price': '4.99', 'currency': 'USD', 'title': 'Rematch x1'},
    'rematch_3': {'price': '9.99', 'currency': 'USD', 'title': 'Rematch x3'},
    'hive_1': {'price': '14.99', 'currency': 'USD', 'title': 'Hive access'},
    'connect_1': {'price': '9.99', 'currency': 'USD', 'title': 'Connect boost'},
    'date_night_1': {'price': '6.99', 'currency': 'USD', 'title': 'Date Night'},
    'rewind_3': {'price': '3.99', 'currency': 'USD', 'title': 'Rewind x3'},
    'rewind_5': {'price': '5.99', 'currency': 'USD', 'title': 'Rewind x5'},
    'rewind_15': {'price': '14.99', 'currency': 'USD', 'title': 'Rewind x15'},
    'likes_unlock_1': {'price': '1.99', 'currency': 'USD', 'title': 'Likes Unlock x1'},
    'likes_unlock_5': {'price': '7.99', 'currency': 'USD', 'title': 'Likes Unlock x5'},
}


@extend_schema(tags=[_('商业化')])
class VipViewSet(viewsets.ViewSet):
    permission_classes = [IsTokenValid, RequireAppModule]

    def get_permissions(self):
        if self.action == 'webhook':
            return []
        return [IsTokenValid(), RequireAppModule()]

    @extend_schema(summary=_('商品列表'))
    @action(detail=False, methods=['get'], url_path='products')
    def products(self, request):
        app_id = request.user.app_id
        profile = get_product_profile(app_id)
        display_tiers = profile.get('display_tiers') or {}
        skus = list(SkuMap.objects.filter(app_id=app_id, is_active=True))
        cn_mode = (profile.get('pay_channel') or '') == 'cn' or app_id == 'matchup_main'
        cny_map = {
            'plus_1m': '28.00', 'plus_6m': '128.00', 'plus_12m': '198.00',
            'gold_1m': '58.00', 'gold_6m': '258.00', 'gold_12m': '398.00',
            'platinum_1m': '88.00', 'platinum_6m': '398.00', 'platinum_12m': '598.00',
        }
        if not skus:
            data = []
            for k, v in MOCK_PRICES.items():
                row = {
                    'product_id': k, **v,
                    'sku_type': 'subscription' if 'm' in k else 'consumable',
                    'display_tier': display_tiers.get(k.split('_')[0]),
                }
                if cn_mode and k in cny_map:
                    row['price'] = cny_map[k]
                    row['currency'] = 'CNY'
                    row['price_string'] = f"¥{cny_map[k]}"
                data.append(row)
        else:
            data = []
            for s in skus:
                price = MOCK_PRICES.get(s.product_id, {'price': '0.00', 'currency': 'USD'})
                currency = 'CNY' if cn_mode else price.get('currency')
                amount = cny_map.get(s.product_id) if cn_mode else price.get('price')
                if cn_mode and not amount:
                    amount = price.get('price')
                data.append({
                    'product_id': s.product_id,
                    'title': s.title,
                    'sku_type': s.sku_type,
                    'tier': s.tier,
                    'display_tier': display_tiers.get(s.tier) if s.tier else None,
                    'quantity': s.quantity,
                    'duration_days': s.duration_days,
                    'price': amount,
                    'currency': currency,
                    'price_string': (f"¥{amount}" if currency == 'CNY' else f"{currency} {amount}"),
                })
        return ApiResponse(data={
            'list': data,
            'display_tiers': display_tiers,
            'pay_channel': 'cn' if cn_mode else 'iap',
            'product_profile': {
                'messaging_mode': profile.get('messaging_mode'),
                'compliment_enabled': profile.get('compliment_enabled'),
                'extend_enabled': profile.get('extend_enabled'),
                'pay_channel': profile.get('pay_channel'),
            },
        }, message='ok')

    @extend_schema(summary=_('权益余额'))
    @action(detail=False, methods=['get'], url_path='entitlements')
    def entitlements(self, request):
        user = request.user
        rows = EntitlementLedger.objects.filter(user=user)
        data = {f"{r.kind}:{r.period_key or 'all'}": r.balance for r in rows}
        spendable = spendable_balances(user)
        return ApiResponse(data={
            'vip_tier': user.effective_vip,
            'vip_tier_display': (get_product_profile(user.app_id).get('display_tiers') or {}).get(user.effective_vip) or user.effective_vip,
            'display_tiers': get_product_profile(user.app_id).get('display_tiers') or {},
            'vip_expire_at': user.vip_expire_at.isoformat() if user.vip_expire_at else None,
            'has_recharged': user.has_recharged,
            'balances': data,
            'spendable': {
                'super_like': spendable.get(EntitlementLedger.SUPER_LIKE, 0),
                'boost': spendable.get(EntitlementLedger.BOOST, 0),
                'rewind': spendable.get(EntitlementLedger.REWIND, 0),
                'likes_unlock': spendable.get(EntitlementLedger.LIKES_UNLOCK, 0),
                'extend': spendable.get(EntitlementLedger.EXTEND, 0),
                'rematch': spendable.get(EntitlementLedger.REMATCH, 0),
                'hive': spendable.get(EntitlementLedger.HIVE, 0),
                'connect': spendable.get(EntitlementLedger.CONNECT, 0),
                'date_night': spendable.get(EntitlementLedger.DATE_NIGHT, 0),
            },
        }, message='ok')

    @extend_schema(summary=_('购买（StoreKit/Play 验单）'))
    @action(detail=False, methods=['post'], url_path='purchase')
    def purchase(self, request):
        from django.conf import settings
        from tools.iap_service import verify_purchase_payload

        user = request.user
        product_id = (request.data.get('product_id') or '').strip()
        if not product_id:
            return ApiResponse(message='product_id required', code=400)

        allow_mock = bool(getattr(settings, 'USE_IAP_MOCK', False))
        verified = verify_purchase_payload(user.app_id, request.data, allow_mock=allow_mock)
        if not verified.get('ok'):
            return ApiResponse(code=400, message=verified.get('error') or 'verify_failed', data=verified)

        # Prefer store product id when present
        product_id = (verified.get('product_id') or product_id).strip()
        platform = (verified.get('platform') or request.data.get('platform') or 'mock').strip().lower()
        tx_id = (
            verified.get('transaction_id')
            or verified.get('order_id')
            or verified.get('purchase_token')
            or f'{platform}_{timezone.now().timestamp()}'
        )
        # Idempotent: same transaction must not double-grant
        existing = Payment.objects.filter(transaction_id=str(tx_id)[:128]).select_related('order').first()
        if existing and existing.status == 'success':
            return ApiResponse(data={
                'order_id': existing.order_id,
                'user': serialize_user_card(user),
                'entitlements': 'unchanged',
                'idempotent': True,
                'mock': bool(verified.get('mock')),
            }, message='ok')

        sku = SkuMap.objects.filter(app_id=user.app_id, product_id=product_id, is_active=True).first()
        price_info = MOCK_PRICES.get(product_id, {'price': '0.00', 'currency': 'USD'})
        order = Order.objects.create(
            user=user,
            app_id=user.app_id,
            product_id=product_id,
            platform=platform[:16],
            amount=Decimal(price_info['price']),
            currency=price_info['currency'],
            status='pending',
            firebase_order_id=f'iap_{tx_id}'[:128],
            raw={'verify': {k: v for k, v in verified.items() if k != 'info'}, 'client': dict(request.data)},
        )
        write_order(user.app_id, order.firebase_order_id, {
            'product_id': product_id, 'status': 'pending', 'user_id': user.id, 'platform': platform,
        })
        order.status = 'success'
        order.save(update_fields=['status', 'updated_at'])
        payment = Payment.objects.create(
            order=order, user=user, app_id=user.app_id, status='success',
            transaction_id=str(tx_id)[:128],
            raw=verified.get('info') or {},
        )
        write_payment(user.app_id, payment.transaction_id, {
            'order_id': order.firebase_order_id, 'status': 'success',
        })
        self._grant(user, sku, product_id)
        user.has_recharged = True
        user.save(update_fields=['has_recharged'])
        return ApiResponse(data={
            'order_id': order.id,
            'user': serialize_user_card(user),
            'entitlements': 'refreshed',
            'mock': bool(verified.get('mock')),
            'warning': verified.get('warning'),
            'platform': platform,
        }, message='ok')

    def _grant(self, user, sku, product_id):
        tier = None
        days = 30
        qty = 1
        sku_type = 'consumable'
        if sku:
            tier = sku.tier
            days = sku.duration_days or 30
            qty = sku.quantity or 1
            sku_type = sku.sku_type
        else:
            if product_id.startswith('plus'):
                tier = 'plus'
            elif product_id.startswith('gold'):
                tier = 'gold'
            elif product_id.startswith('platinum'):
                tier = 'platinum'
            elif 'super_like' in product_id:
                n = 3
                if product_id.split('_')[-1].isdigit():
                    n = int(product_id.split('_')[-1])
                grant_ledger(user, EntitlementLedger.SUPER_LIKE, max(n, 1), period_key='purchased')
                return
            elif 'boost' in product_id:
                n = 1
                if product_id.split('_')[-1].isdigit():
                    n = int(product_id.split('_')[-1])
                grant_ledger(user, EntitlementLedger.BOOST, max(n, 1), period_key='purchased')
                return
            elif product_id.startswith('extend'):
                n = 1
                if product_id.split('_')[-1].isdigit():
                    n = int(product_id.split('_')[-1])
                grant_ledger(user, EntitlementLedger.EXTEND, max(n, 1), period_key='purchased')
                return
            elif product_id.startswith('rematch'):
                n = 1
                if product_id.split('_')[-1].isdigit():
                    n = int(product_id.split('_')[-1])
                grant_ledger(user, EntitlementLedger.REMATCH, max(n, 1), period_key='purchased')
                return
            elif product_id.startswith('hive'):
                grant_ledger(user, EntitlementLedger.HIVE, 1, period_key='purchased')
                return
            elif product_id.startswith('connect'):
                grant_ledger(user, EntitlementLedger.CONNECT, 1, period_key='purchased')
                return
            elif product_id.startswith('date_night'):
                grant_ledger(user, EntitlementLedger.DATE_NIGHT, 1, period_key='purchased')
                return
            elif product_id.startswith('rewind'):
                n = 3
                if product_id.split('_')[-1].isdigit():
                    n = int(product_id.split('_')[-1])
                grant_ledger(user, EntitlementLedger.REWIND, max(n, 1), period_key='purchased')
                return
            elif product_id.startswith('likes_unlock'):
                n = 1
                if product_id.split('_')[-1].isdigit():
                    n = int(product_id.split('_')[-1])
                grant_ledger(user, EntitlementLedger.LIKES_UNLOCK, max(n, 1), period_key='purchased')
                return
            if product_id.endswith('_12m'):
                days = 365
            elif product_id.endswith('_6m'):
                days = 180
            else:
                days = 30
        if tier in ('plus', 'gold', 'platinum'):
            user.vip_tier = tier
            base = user.vip_expire_at if user.vip_expire_at and user.vip_expire_at > timezone.now() else timezone.now()
            user.vip_expire_at = base + timedelta(days=days)
            user.save(update_fields=['vip_tier', 'vip_expire_at'])
            if tier in ('gold', 'platinum'):
                apply_vip_subscription_grants(user, tier)
            from tools.spark_helpers import top_up_daily_entitlements_after_vip, ensure_daily_feed
            top_up_daily_entitlements_after_vip(user)
            if tier == 'plus':
                # Plus rewind is unlimited via vip gate; no consumable stock needed
                ensure_daily_feed(user)
            return
        # consumables via SKU map
        if sku_type == 'consumable' or (sku and sku.tier in (
            'super_like', 'boost', 'extend', 'rematch', 'hive', 'connect', 'date_night',
            'rewind', 'likes_unlock',
        )):
            kind_map = {
                'super_like': EntitlementLedger.SUPER_LIKE,
                'boost': EntitlementLedger.BOOST,
                'extend': EntitlementLedger.EXTEND,
                'rematch': EntitlementLedger.REMATCH,
                'hive': EntitlementLedger.HIVE,
                'connect': EntitlementLedger.CONNECT,
                'date_night': EntitlementLedger.DATE_NIGHT,
                'rewind': EntitlementLedger.REWIND,
                'likes_unlock': EntitlementLedger.LIKES_UNLOCK,
            }
            tier_key = (sku.tier if sku else None) or ''
            for key, kind in kind_map.items():
                if tier_key == key or key in product_id:
                    grant_ledger(user, kind, max(qty, 1), period_key='purchased')
                    return
    @extend_schema(summary=_('开启 Boost'))
    @action(detail=False, methods=['post'], url_path='boost')
    def boost(self, request):
        user = request.user
        from tools.spark_helpers import consume_ledger
        ok, ledger = consume_ledger(user, EntitlementLedger.BOOST)
        if not ok:
            return ApiResponse(code=403, message='need_boost', data={'need_shop': True})
        # W-09: end other active sessions so only one Boost is live
        now = timezone.now()
        BoostSession.objects.filter(user=user, is_active=True).update(is_active=False, end_at=now)
        session = BoostSession.objects.create(user=user, end_at=now + timedelta(minutes=30))
        return ApiResponse(data={
            'end_at': session.end_at.isoformat(),
            'start_at': session.start_at.isoformat() if session.start_at else None,
            'impressions': 0,
            'likes': 0,
            'matches': 0,
        }, message='ok')

    @extend_schema(summary=_('Boost 曝光报告'))
    @action(detail=False, methods=['get'], url_path='boost/report')
    def boost_report(self, request):
        user = request.user
        from tools.spark_helpers import active_boost as _active_boost
        session = _active_boost(user)
        if not session:
            session = BoostSession.objects.filter(user=user).order_by('-id').first()
        if not session:
            return ApiResponse(data={'session': None}, message='ok')
        return ApiResponse(data={
            'session': {
                'id': session.id,
                'start_at': session.start_at.isoformat() if session.start_at else None,
                'end_at': session.end_at.isoformat() if session.end_at else None,
                'is_active': bool(session.is_active and session.end_at and session.end_at > timezone.now()),
                'impressions': session.impressions,
                'likes': session.likes,
                'matches': session.matches,
            },
        }, message='ok')

    @extend_schema(summary=_('恢复购买'))
    @action(detail=False, methods=['post'], url_path='restore')
    def restore(self, request):
        """Re-verify optional store receipts, then re-assert successful orders."""
        from django.conf import settings
        from tools.iap_service import verify_purchase_payload

        user = request.user
        allow_mock = bool(getattr(settings, 'USE_IAP_MOCK', False))
        receipts = request.data.get('receipts') or request.data.get('purchases') or []
        if isinstance(receipts, dict):
            receipts = [receipts]
        verified_products = []
        granted_order_ids = set()

        def _mark_restored(order):
            raw = dict(order.raw) if isinstance(order.raw, dict) else {}
            raw['restored'] = True
            raw['restored_at'] = timezone.now().isoformat()
            order.raw = raw
            order.save(update_fields=['raw', 'updated_at'])

        for item in receipts:
            if not isinstance(item, dict):
                continue
            result = verify_purchase_payload(user.app_id, item, allow_mock=allow_mock)
            if result.get('ok') and result.get('product_id'):
                verified_products.append(result['product_id'])
                # Ensure order exists for verified receipt
                tid = str(
                    result.get('transaction_id')
                    or result.get('order_id')
                    or result.get('purchase_token')
                    or ''
                )[:128]
                if tid and not Payment.objects.filter(transaction_id=tid).exists():
                    sku = SkuMap.objects.filter(
                        app_id=user.app_id, product_id=result['product_id'], is_active=True,
                    ).first()
                    price_info = MOCK_PRICES.get(result['product_id'], {'price': '0.00', 'currency': 'USD'})
                    order = Order.objects.create(
                        user=user, app_id=user.app_id, product_id=result['product_id'],
                        platform=(result.get('platform') or 'restore')[:16],
                        amount=Decimal(price_info['price']), currency=price_info['currency'],
                        status='success', firebase_order_id=f'restore_{tid}'[:128],
                        raw={'restore': True},
                    )
                    Payment.objects.create(
                        order=order, user=user, app_id=user.app_id, status='success',
                        transaction_id=tid, raw=result.get('info') or {},
                    )
                    self._grant(user, sku, result['product_id'])
                    granted_order_ids.add(order.id)
                    _mark_restored(order)

        orders = Order.objects.filter(user=user, status='success').order_by('-id')[:20]
        restored = list(verified_products)
        for order in orders:
            raw = order.raw if isinstance(order.raw, dict) else {}
            # Skip already-restored / already-granted this call
            if order.id in granted_order_ids or raw.get('restored'):
                if order.product_id not in restored:
                    restored.append(order.product_id)
                continue
            sku = SkuMap.objects.filter(app_id=user.app_id, product_id=order.product_id, is_active=True).first()
            self._grant(user, sku, order.product_id)
            granted_order_ids.add(order.id)
            _mark_restored(order)
            if order.product_id not in restored:
                restored.append(order.product_id)
        user.refresh_from_db()
        rows = EntitlementLedger.objects.filter(user=user)
        balances = {f"{r.kind}:{r.period_key or 'all'}": r.balance for r in rows}
        return ApiResponse(data={
            'restored_products': restored,
            'vip_tier': user.effective_vip,
            'vip_expire_at': user.vip_expire_at.isoformat() if user.vip_expire_at else None,
            'balances': balances,
            'mock': allow_mock and not receipts,
        }, message='ok')

    @extend_schema(summary=_('IAP Webhook（Apple/Google 通知）'))
    @action(detail=False, methods=['post'], url_path='webhook', permission_classes=[])
    def webhook(self, request):
        """Handle App Store Server Notifications / Play RTDN (best-effort).

        Refund / revoke → mark related payment + drop subscription if product maps to VIP.
        """
        import logging
        import os
        from django.conf import settings

        log = logging.getLogger(__name__)
        secret = (
            getattr(settings, 'IAP_WEBHOOK_SECRET', None)
            or os.getenv('IAP_WEBHOOK_SECRET', '')
            or ''
        ).strip()
        incoming = (
            request.headers.get('X-Webhook-Secret')
            or request.META.get('HTTP_X_WEBHOOK_SECRET')
            or ''
        ).strip()
        if secret:
            if incoming != secret:
                return ApiResponse(code=403, message='invalid_webhook_secret')
        else:
            if getattr(settings, 'DEBUG', False):
                log.warning('IAP webhook accepted without IAP_WEBHOOK_SECRET (DEBUG/dev)')
            else:
                log.warning('IAP webhook accepted without IAP_WEBHOOK_SECRET')

        payload = request.data if isinstance(request.data, dict) else {}
        notification_type = (
            payload.get('notificationType')
            or (payload.get('message') or {}).get('data')
            or payload.get('event')
            or ''
        )
        signed = payload.get('signedPayload') or ''
        info = {}
        if signed:
            from tools.iap_service import _decode_jws_payload
            outer = _decode_jws_payload(signed)
            data = outer.get('data') or {}
            tx = data.get('signedTransactionInfo') or ''
            if tx:
                info = _decode_jws_payload(tx)
            notification_type = outer.get('notificationType') or notification_type
        refund_types = {
            'REFUND', 'REVOKE', 'EXPIRED', 'DID_FAIL_TO_RENEW',
            'subscription_revoked', 'subscription_canceled',
        }
        tid = str(info.get('originalTransactionId') or info.get('transactionId') or '')[:128]
        nt = str(notification_type or '').upper()
        if tid and (nt in refund_types or any(t in nt for t in refund_types)):
            pay = Payment.objects.filter(transaction_id=tid).select_related('order', 'user').first()
            if pay:
                pay.status = 'refunded'
                pay.save(update_fields=['status'])
                pay.order.status = 'refunded'
                pay.order.save(update_fields=['status', 'updated_at'])
                # Best-effort: expire VIP if order was subscription
                pid = pay.order.product_id or ''
                if any(pid.startswith(t) for t in ('plus', 'gold', 'platinum')):
                    u = pay.user
                    u.vip_expire_at = timezone.now()
                    u.save(update_fields=['vip_expire_at'])
        return ApiResponse(data={'received': True, 'type': notification_type}, message='ok')

    @extend_schema(summary=_('国内支付（微信/支付宝）'))
    @action(detail=False, methods=['post'], url_path='cn-pay')
    def cn_pay(self, request):
        """Create CN pay order. Grant only via mock or real gateway — never client confirm alone."""
        from django.conf import settings
        from tools.provider_helpers import get_provider_field, provider_enabled

        user = request.user
        product_id = (request.data.get('product_id') or '').strip()
        channel = (request.data.get('channel') or 'wechat').strip().lower()
        confirm = bool(request.data.get('confirm') or request.data.get('paid'))
        order_id = request.data.get('order_id')
        if channel not in ('wechat', 'alipay', 'wx', 'zfb'):
            return ApiResponse(code=400, message='invalid_channel')
        if channel in ('wx',):
            channel = 'wechat'
        if channel in ('zfb',):
            channel = 'alipay'

        allow_mock = bool(getattr(settings, 'USE_IAP_MOCK', False))

        # Client confirm alone is insecure — reject unless explicit mock
        if confirm and order_id:
            if not allow_mock:
                return ApiResponse(
                    code=403,
                    message='confirm_requires_gateway',
                    data={'hint': 'await_webhook_or_gateway'},
                )
            order = Order.objects.filter(id=order_id, user=user).first()
            if not order:
                return ApiResponse(code=404, message='order_not_found')
            if order.status == 'success':
                return ApiResponse(data={'order_id': order.id, 'idempotent': True, 'mock': True}, message='ok')
            order.status = 'success'
            order.save(update_fields=['status', 'updated_at'])
            pay = Payment.objects.filter(order=order).first()
            if pay:
                pay.status = 'success'
                pay.save(update_fields=['status'])
            user.has_recharged = True
            user.save(update_fields=['has_recharged'])
            sku = SkuMap.objects.filter(app_id=user.app_id, product_id=order.product_id, is_active=True).first()
            self._grant(user, sku, order.product_id)
            return ApiResponse(data={
                'order_id': order.id,
                'channel': order.platform,
                'mock': True,
                'user': serialize_user_card(user),
            }, message='ok')

        if not product_id:
            return ApiResponse(code=400, message='product_id required')

        mch = get_provider_field('cn_pay', 'mch_id', user.app_id, env_keys=('CN_PAY_MCH_ID',))
        key = get_provider_field('cn_pay', 'api_key', user.app_id, env_keys=('CN_PAY_API_KEY',))
        configured = bool(mch and key and provider_enabled('cn_pay', user.app_id, default=True))

        cny = {
            'plus_1m': '28.00', 'plus_6m': '128.00', 'plus_12m': '198.00',
            'gold_1m': '58.00', 'gold_6m': '258.00', 'gold_12m': '398.00',
            'platinum_1m': '88.00', 'platinum_6m': '398.00', 'platinum_12m': '598.00',
        }
        price = Decimal(cny.get(product_id) or MOCK_PRICES.get(product_id, {}).get('price') or '9.90')
        tx_id = f'cn_{channel}_{user.id}_{product_id}_{int(timezone.now().timestamp())}'

        if not configured and not allow_mock:
            return ApiResponse(code=503, message='cn_pay_not_configured')

        # Mock path: immediate success (explicit USE_IAP_MOCK only)
        if allow_mock and (not configured or request.data.get('mock', True)):
            order = Order.objects.create(
                user=user,
                app_id=user.app_id or 'matchup_main',
                product_id=product_id,
                amount=price,
                currency='CNY',
                status='success',
                platform=channel[:16],
                firebase_order_id=tx_id[:128],
                raw={'mock': True, 'channel': channel},
            )
            Payment.objects.create(
                order=order,
                user=user,
                app_id=user.app_id or 'matchup_main',
                transaction_id=tx_id[:128],
                status='success',
                raw={'mock': True, 'channel': channel},
            )
            user.has_recharged = True
            user.save(update_fields=['has_recharged'])
            sku = SkuMap.objects.filter(app_id=user.app_id, product_id=product_id, is_active=True).first()
            self._grant(user, sku, product_id)
            write_order(user.app_id, str(order.id), {'product_id': product_id, 'channel': channel, 'cny': str(price)})
            write_payment(user.app_id, tx_id, {'order_id': order.id, 'channel': channel})
            return ApiResponse(data={
                'order_id': order.id,
                'channel': channel,
                'currency': 'CNY',
                'price': str(price),
                'mock': True,
                'user': serialize_user_card(user),
            }, message='ok')

        # Production: create pending order for native bridge to pay
        order = Order.objects.create(
            user=user,
            app_id=user.app_id or 'matchup_main',
            product_id=product_id,
            amount=price,
            currency='CNY',
            status='pending',
            platform=channel[:16],
            firebase_order_id=tx_id[:128],
            raw={'channel': channel, 'mch_id': mch},
        )
        Payment.objects.create(
            order=order,
            user=user,
            app_id=user.app_id or 'matchup_main',
            transaction_id=tx_id[:128],
            status='pending',
            raw={'channel': channel},
        )
        return ApiResponse(data={
            'order_id': order.id,
            'channel': channel,
            'currency': 'CNY',
            'price': str(price),
            'status': 'pending',
            'pay_params': {
                'mch_id': mch,
                'out_trade_no': tx_id[:128],
                'product_id': product_id,
            },
            'mock': False,
        }, message='ok', code=201)
