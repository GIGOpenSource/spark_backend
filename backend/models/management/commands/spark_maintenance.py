from datetime import timedelta
import logging
import sys

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from models.models import Match, MatchQA, SayHi, BoostSession, User, Swipe, Conversation, Message
from tools.spark_helpers import (
    ensure_daily_likes, clear_vip_grant_balances, apply_vip_subscription_grants,
    get_product_profile,
)
from tools.push_service import process_silent_recalls

logger = logging.getLogger(__name__)


def _silent_match_cutoff(now):
    """Use match_open_hours from product profiles; fall back to 7 days."""
    hours_candidates = []
    for app_id in ('spark_main', 'swipe_main', 'matchup_main', 'ember_main', 'flick_main'):
        try:
            profile = get_product_profile(app_id)
            hours = profile.get('match_open_hours')
            if hours is not None:
                hours_candidates.append(int(hours))
        except Exception:
            pass
    if hours_candidates:
        # Use the max configured window so we don't expire early for longer shells
        return now - timedelta(hours=max(hours_candidates))
    return now - timedelta(days=7)


class Command(BaseCommand):
    help = 'Expire matches/sayhi/boosts/likes and refresh subscription grants (spark DB only)'

    def handle(self, *args, **options):
        try:
            self._run()
        except Exception:
            logger.exception('spark_maintenance failed')
            self.stderr.write(self.style.ERROR('spark_maintenance failed — see logs'))
            sys.exit(1)

    def _run(self):
        now = timezone.now()
        # heal: opened chats never expire
        opened_ids = set(
            Conversation.objects.filter(match_id__isnull=False)
            .exclude(Q(last_message='') | Q(last_message__isnull=True))
            .values_list('match_id', flat=True)
        )
        opened_ids |= set(
            Message.objects.filter(conversation__match_id__isnull=False)
            .values_list('conversation__match_id', flat=True)
        )
        # QA approved counts as opened for expire purposes
        qa_opened = set(
            MatchQA.objects.filter(status=MatchQA.STATUS_APPROVED).values_list('match_id', flat=True)
        )
        opened_ids |= qa_opened
        if opened_ids:
            Match.objects.filter(id__in=opened_ids, status='active').exclude(expire_at__isnull=True).update(
                expire_at=None,
            )
            # stamp opened_at for women_first / any match that already has messages
            Match.objects.filter(
                id__in=opened_ids, status='active', opened_at__isnull=True,
            ).update(opened_at=now)

        # Collect matches about to hard-expire (for QA termination + WS broadcast)
        expiring_qs = Match.objects.filter(status='active', expire_at__lt=now).exclude(id__in=opened_ids)
        expiring_ids = list(expiring_qs.values_list('id', flat=True)[:500])
        m = expiring_qs.update(status='expired')
        # women_first: also expire active matches past expire_at with no opener message
        wf = Match.objects.filter(
            status='active',
            messaging_mode='women_first',
            opened_at__isnull=True,
            expire_at__lt=now,
        ).update(status='expired')
        if wf:
            m = max(m, wf) if isinstance(m, int) else m

        # 她说：到期硬终态 — 未完成 QA 一并终止并广播
        qa_expired = 0
        pending_qa = MatchQA.objects.filter(
            status__in=(
                MatchQA.STATUS_NEED_QUESTION,
                MatchQA.STATUS_NEED_ANSWER,
                MatchQA.STATUS_NEED_REVIEW,
            ),
        ).filter(
            Q(expire_at__lt=now) | Q(match_id__in=expiring_ids) | Q(match__status='expired'),
        )
        from Apps.views.match.consumers import broadcast_match_qa
        for qa in pending_qa.select_related('match', 'match__user_a', 'match__user_b')[:500]:
            qa.status = MatchQA.STATUS_EXPIRED
            qa.save(update_fields=['status', 'updated_at'])
            match = qa.match
            if match.status == 'active' and match.opened_at is None:
                match.status = 'expired'
                match.save(update_fields=['status'])
            try:
                broadcast_match_qa(match)
            except Exception:
                pass
            qa_expired += 1

        s = SayHi.objects.filter(status='pending', expire_at__lt=now).update(status='expired')
        b = BoostSession.objects.filter(is_active=True, end_at__lt=now).update(is_active=False)

        # 14d one-way likes: do NOT is_undone (keep visible as expired in sent)
        like_cutoff = now - timedelta(days=14)
        likes_expired = Swipe.objects.filter(
            is_undone=False,
            action__in=('like', 'super_like'),
            created_at__lt=like_cutoff,
        ).count()

        silent_cutoff = _silent_match_cutoff(now)
        silent = 0
        for match in Match.objects.filter(status='active', created_at__lt=silent_cutoff).select_related(
            'user_a', 'user_b'
        )[:500]:
            # Prefer per-app match_open_hours when available
            try:
                app_id = getattr(match.user_a, 'app_id', None) or getattr(match.user_b, 'app_id', None)
                if app_id:
                    hours = get_product_profile(app_id).get('match_open_hours')
                    if hours is not None:
                        app_cutoff = now - timedelta(hours=int(hours))
                        if match.created_at >= app_cutoff:
                            continue
            except Exception:
                pass
            conv = Conversation.objects.filter(match=match).first()
            if not conv:
                match.status = 'expired'
                match.save(update_fields=['status'])
                silent += 1
                continue
            if not conv.messages.exists() and (not conv.last_at or conv.last_at < silent_cutoff):
                match.status = 'expired'
                match.save(update_fields=['status'])
                silent += 1

        # VIP expired → clear grant pool (keep purchased).
        # Lifetime VIP: vip_expire_at IS NULL must NOT be treated as expired (BE-019).
        cleared = 0
        for user in User.objects.filter(
            vip_tier__in=['plus', 'gold', 'platinum'],
            vip_expire_at__isnull=False,
            vip_expire_at__lte=now,
        ):
            clear_vip_grant_balances(user)
            if user.vip_tier != 'none':
                user.vip_tier = 'none'
                user.save(update_fields=['vip_tier'])
                cleared += 1

        refreshed = 0
        granted_sl = 0
        granted_boost = 0
        for user in User.objects.filter(vip_tier__in=['plus', 'gold', 'platinum']).filter(
            Q(vip_expire_at__isnull=True) | Q(vip_expire_at__gt=now)
        ):
            ensure_daily_likes(user)
            sl_ok, boost_ok = apply_vip_subscription_grants(user, user.vip_tier)
            if sl_ok:
                granted_sl += 1
            if boost_ok:
                granted_boost += 1
            refreshed += 1

        push_result = process_silent_recalls(limit=200)

        summary = (
            f'expired matches={m} qa_expired={qa_expired} silent_matches={silent} say_hi={s} '
            f'boosts={b} likes_stale={likes_expired}; vip_cleared={cleared}; '
            f'refreshed_users={refreshed} super_like_grants={granted_sl} boost_grants={granted_boost}; '
            f'silent_push={push_result}'
        )
        logger.info('spark_maintenance ok: %s', summary)
        self.stdout.write(self.style.SUCCESS(summary))
