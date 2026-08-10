"""
Product analytics aggregations over AnalyticsEvent (t_event).

Used by admin「Analytics」panel — overview / trend / top events / funnel / stream.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

# Default product funnel (aligned with client EVENT_ALIASES / PRD)
DEFAULT_FUNNEL = [
    'app_first_open',
    'welcome_view',
    'auth_result',
    'onboarding_complete',
    'paywall_show',
    'pay_success',
]


def parse_range(date_from: str | None, date_to: str | None, default_days: int = 7):
    today = timezone.localdate()
    end = parse_date(date_to) if date_to else today
    start = parse_date(date_from) if date_from else (end - timedelta(days=default_days - 1))
    if not end:
        end = today
    if not start:
        start = end - timedelta(days=default_days - 1)
    if start > end:
        start, end = end, start
    # inclusive end → next day exclusive for DateTimeField
    start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end + timedelta(days=1), datetime.min.time()))
    return start, end, start_dt, end_dt


def scoped_events(app_scope: dict, start_dt, end_dt, event: str | None = None):
    from models.models import AnalyticsEvent
    qs = AnalyticsEvent.objects.filter(**app_scope, created_at__gte=start_dt, created_at__lt=end_dt)
    if event:
        qs = qs.filter(event=event)
    return qs


def overview(app_scope: dict, date_from: str | None = None, date_to: str | None = None) -> dict:
    start, end, start_dt, end_dt = parse_range(date_from, date_to, default_days=7)
    qs = scoped_events(app_scope, start_dt, end_dt)

    total_events = qs.count()
    dau = qs.exclude(user_id__isnull=True).values('user_id').distinct().count()
    unique_events = qs.values('event').distinct().count()

    # previous period of same length for delta
    span = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    _, _, prev_start_dt, prev_end_dt = parse_range(
        prev_start.isoformat(), prev_end.isoformat(), default_days=span,
    )
    prev_qs = scoped_events(app_scope, prev_start_dt, prev_end_dt)
    prev_total = prev_qs.count()
    prev_dau = prev_qs.exclude(user_id__isnull=True).values('user_id').distinct().count()

    from tools.event_dict import enrich_list_with_labels
    top = enrich_list_with_labels(list(
        qs.values('event').annotate(count=Count('id')).order_by('-count')[:20]
    ))
    pv_qs = qs.filter(event='page_view')
    btn_qs = qs.filter(event='btn_click')
    page_pv = pv_qs.count()
    page_uv = pv_qs.exclude(user_id__isnull=True).values('user_id').distinct().count()
    btn_pv = btn_qs.count()
    btn_uv = btn_qs.exclude(user_id__isnull=True).values('user_id').distinct().count()

    by_day = list(
        qs.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'), users=Count('user_id', distinct=True))
        .order_by('day')
    )
    trend = [
        {
            'day': (r['day'].isoformat() if hasattr(r['day'], 'isoformat') else str(r['day'])),
            'count': r['count'],
            'users': r['users'] or 0,
        }
        for r in by_day
    ]

    by_locale = list(
        qs.exclude(device_locale__isnull=True)
        .exclude(device_locale='')
        .values('device_locale')
        .annotate(count=Count('id'))
        .order_by('-count')[:15]
    )
    by_version = list(
        qs.exclude(app_version__isnull=True)
        .exclude(app_version='')
        .values('app_version')
        .annotate(count=Count('id'))
        .order_by('-count')[:15]
    )

    def delta(cur, prev):
        if prev == 0:
            return {'abs': cur, 'pct': None}
        return {'abs': cur - prev, 'pct': round((cur - prev) * 100.0 / prev, 1)}

    return {
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
        'kpis': {
            'events': total_events,
            'events_delta': delta(total_events, prev_total),
            'dau': dau,
            'dau_delta': delta(dau, prev_dau),
            'unique_event_names': unique_events,
            'avg_events_per_user': round(total_events / dau, 2) if dau else 0,
            'page_pv': page_pv,
            'page_uv': page_uv,
            'btn_pv': btn_pv,
            'btn_uv': btn_uv,
        },
        'top_events': top,
        'trend': trend,
        'by_locale': [{'locale': r['device_locale'], 'count': r['count']} for r in by_locale],
        'by_version': [{'version': r['app_version'], 'count': r['count']} for r in by_version],
    }


def event_breakdown(app_scope: dict, date_from=None, date_to=None, limit=200) -> dict:
    from tools.event_dict import enrich_list_with_labels

    start, end, start_dt, end_dt = parse_range(date_from, date_to, default_days=30)
    qs = scoped_events(app_scope, start_dt, end_dt)
    rows = list(
        qs.values('event')
        .annotate(
            count=Count('id'),
            users=Count('user_id', distinct=True),
        )
        .order_by('-count')[:limit]
    )
    # PV / UV shortcuts for page_view & btn_click
    pv_qs = qs.filter(event='page_view')
    btn_qs = qs.filter(event='btn_click')
    return {
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
        'list': enrich_list_with_labels([
            {'event': r['event'], 'count': r['count'], 'users': r['users'] or 0}
            for r in rows
        ]),
        'pv_uv': {
            'page_view_pv': pv_qs.count(),
            'page_view_uv': pv_qs.exclude(user_id__isnull=True).values('user_id').distinct().count(),
            'btn_click_pv': btn_qs.count(),
            'btn_click_uv': btn_qs.exclude(user_id__isnull=True).values('user_id').distinct().count(),
        },
    }


def funnel(
    app_scope: dict,
    steps: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    start, end, start_dt, end_dt = parse_range(date_from, date_to, default_days=7)
    steps = [s.strip() for s in (steps or DEFAULT_FUNNEL) if s and s.strip()]
    if not steps:
        steps = list(DEFAULT_FUNNEL)

    from models.models import AnalyticsEvent
    base = AnalyticsEvent.objects.filter(**app_scope, created_at__gte=start_dt, created_at__lt=end_dt)

    result_steps = []
    prev_users = None
    for i, name in enumerate(steps):
        users = (
            base.filter(event=name)
            .exclude(user_id__isnull=True)
            .values_list('user_id', flat=True)
            .distinct()
        )
        # For step > 0, optionally intersect with previous step users (strict funnel)
        user_set = set(users)
        if i > 0 and prev_users is not None:
            user_set = user_set & prev_users
        count = len(user_set)
        events_count = base.filter(event=name).count()
        conv = None
        if i == 0:
            conv = 100.0 if count else 0.0
        elif prev_users is not None and len(prev_users):
            conv = round(count * 100.0 / len(prev_users), 2)
        else:
            conv = 0.0
        result_steps.append({
            'step': i,
            'event': name,
            'users': count,
            'events': events_count,
            'conversion_from_prev': conv,
            'conversion_from_start': (
                round(count * 100.0 / result_steps[0]['users'], 2)
                if result_steps and result_steps[0]['users']
                else (100.0 if i == 0 and count else 0.0)
            ),
        })
        prev_users = user_set

    return {
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
        'steps': result_steps,
    }


def event_stream(
    app_scope: dict,
    date_from=None,
    date_to=None,
    event: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    start, end, start_dt, end_dt = parse_range(date_from, date_to, default_days=1)
    qs = scoped_events(app_scope, start_dt, end_dt, event=event)
    if q:
        qs = qs.filter(
            Q(event__icontains=q)
            | Q(app_version__icontains=q)
            | Q(device_locale__icontains=q)
        )
    total = qs.count()
    limit = min(max(int(limit or 100), 1), 500)
    offset = max(int(offset or 0), 0)
    rows = list(
        qs.select_related('user').order_by('-id')[offset:offset + limit]
    )
    return {
        'date_from': start.isoformat(),
        'date_to': end.isoformat(),
        'total': total,
        'list': [
            {
                'id': r.id,
                'event': r.event,
                'user_id': r.user_id,
                'app_id': r.app_id,
                'app_version': r.app_version or '',
                'device_locale': r.device_locale or '',
                'props': r.props or {},
                'created_at': r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
