"""B-05: Precompute per-app feed candidate user ids into Redis.

Maintenance / cron can call:
  python manage.py precompute_feed_candidates --settings=...
  python manage.py precompute_feed_candidates --app-id spark_main --limit 500

Writes JSON list of user ids to Redis key ``feed_cand:{app_id}`` (TTL 6h).
Recommend feed prefers these ids when the key exists.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from models.models import User, AppConfig
from tools.token_tools import _redis


FEED_CAND_TTL = 6 * 3600
DEFAULT_LIMIT = 500


class Command(BaseCommand):
    help = 'Precompute feed candidate user ids per app_id into Redis feed_cand:{app_id}'

    def add_arguments(self, parser):
        parser.add_argument('--app-id', default='', help='Single app_id (default: all AppConfig)')
        parser.add_argument('--limit', type=int, default=DEFAULT_LIMIT, help='Top N user ids per app')

    def handle(self, *args, **options):
        limit = max(1, int(options.get('limit') or DEFAULT_LIMIT))
        app_id = (options.get('app_id') or '').strip()
        if app_id:
            app_ids = [app_id]
        else:
            app_ids = list(AppConfig.objects.values_list('app_id', flat=True))
            if not app_ids:
                app_ids = ['spark_main', 'swipe_main', 'matchup_main']

        written = 0
        for aid in app_ids:
            ids = list(
                User.objects.filter(
                    role='user', status=1, profile_complete=True,
                    invisible_mode=False, discovery_enabled=True,
                    app_id=aid,
                )
                .order_by('-online_at', '-updated_at', '-id')
                .values_list('id', flat=True)[:limit]
            )
            key = f'feed_cand:{aid}'
            try:
                import json
                _redis.setKey(key, json.dumps([int(i) for i in ids]), ex=FEED_CAND_TTL)
                written += 1
                self.stdout.write(f'{key} <- {len(ids)} ids (ttl={FEED_CAND_TTL}s)')
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'failed {aid}: {e}'))
        self.stdout.write(self.style.SUCCESS(
            f'precompute_feed_candidates done apps={written} at {timezone.now().isoformat()}'
        ))
