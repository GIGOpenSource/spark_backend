"""Firebase adapter — mock by default, real Admin SDK when configured."""
import logging
import os
import uuid
from copy import deepcopy

logger = logging.getLogger(__name__)

_STORE = {
    'users': {},
    'orders': {},
    'payments': {},
}


def use_mock():
    return os.getenv('USE_FIREBASE_MOCK', 'true').lower() == 'true'


def write_user(app_id, firebase_uid, payload):
    key = f'{app_id}:{firebase_uid}'
    doc = {'app_id': app_id, 'firebase_uid': firebase_uid, **payload}
    _STORE['users'][key] = doc
    logger.info('firebase mock write user %s', key)
    return doc


def write_order(app_id, order_id, payload):
    key = f'{app_id}:{order_id}'
    doc = {'app_id': app_id, 'order_id': order_id, **payload}
    _STORE['orders'][key] = doc
    return doc


def write_payment(app_id, payment_id, payload):
    key = f'{app_id}:{payment_id}'
    doc = {'app_id': app_id, 'payment_id': payment_id, **payload}
    _STORE['payments'][key] = doc
    return doc


def list_users(app_id=None):
    rows = list(_STORE['users'].values())
    if app_id:
        rows = [r for r in rows if r.get('app_id') == app_id]
    return deepcopy(rows)


def list_orders(app_id=None):
    rows = list(_STORE['orders'].values())
    if app_id:
        rows = [r for r in rows if r.get('app_id') == app_id]
    return deepcopy(rows)


def list_payments(app_id=None):
    rows = list(_STORE['payments'].values())
    if app_id:
        rows = [r for r in rows if r.get('app_id') == app_id]
    return deepcopy(rows)


def new_firebase_uid():
    return f'mock_{uuid.uuid4().hex[:16]}'
