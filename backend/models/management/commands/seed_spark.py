import os
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from models.models import (
    User, UserPhoto, AppConfig, DiscoverParam, FunnelPool, SkuMap,
    CountryConfig, EntitlementLedger, Swipe, Match, Conversation, Message,
    ReviewMode, WordFilter, Report, SayHi, DomainWhitelist, SystemPushConfig,
)
from tools.spark_helpers import grant_ledger, ensure_daily_likes, get_or_create_pair_match, default_product_profile, set_product_profile
from tools.app_modules import DEFAULT_PACKAGE_BY_APP, default_enabled_modules


DEMO_PHOTOS = [
    'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800',
    'https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=800',
    'https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=800',
]


class Command(BaseCommand):
    help = 'Seed Spark demo data (writes only to configured spark DB). Use --reset-demo / --sync-profile for destructive ops.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-demo',
            action='store_true',
            help='Delete and recreate FunnelPool demo robots (destructive).',
        )
        parser.add_argument(
            '--sync-profile',
            action='store_true',
            help='Overwrite product_profile keys with defaults (may clobber ops overrides).',
        )

    def handle(self, *args, **options):
        reset_demo = bool(options.get('reset_demo'))
        sync_profile = bool(options.get('sync_profile'))
        apps = [
            ('spark_main', 'Spark', 'https://spark.app'),
            ('swipe_main', 'bee', 'https://bee.app'),
            ('ember_main', 'Ember', 'https://ember.app'),
            ('matchup_main', 'MatchUp', 'https://matchup.app'),
            ('flick_main', 'Flick', 'https://flick.app'),
        ]
        for app_id, name, base_url in apps:
            pkg = DEFAULT_PACKAGE_BY_APP.get(app_id, f'app.{app_id}')
            app, created = AppConfig.objects.get_or_create(
                app_id=app_id,
                defaults={
                    'name': name,
                    'package_name': pkg,
                    'tos_url': f'{base_url}/tos',
                    'privacy_url': f'{base_url}/privacy',
                    'config': {
                        'product_profile': default_product_profile(app_id),
                        'enabled_modules': default_enabled_modules(),
                    },
                },
            )
            if not created:
                cfg = dict(app.config or {})
                # Keep package_name / display name in sync with frontend brand defaults
                app.package_name = pkg
                if app.name != name:
                    app.name = name
                if 'enabled_modules' not in cfg:
                    cfg['enabled_modules'] = default_enabled_modules()
                    app.config = cfg
                app.save(update_fields=['package_name', 'name', 'config'])
            # Only push default product_profile keys when explicitly requested (or brand-new app)
            if created or sync_profile:
                set_product_profile(app_id, default_product_profile(app_id))
            elif 'product_profile' not in (app.config or {}):
                set_product_profile(app_id, default_product_profile(app_id))
            DiscoverParam.objects.get_or_create(app_id=app_id, country='*')
            CountryConfig.objects.get_or_create(app_id=app_id, country='*', defaults={'config': {}})

        skus = [
            ('plus_1m', 'subscription', 'plus', 1, 30, 'Plus 1 Month'),
            ('plus_6m', 'subscription', 'plus', 1, 180, 'Plus 6 Months'),
            ('plus_12m', 'subscription', 'plus', 1, 365, 'Plus 12 Months'),
            ('gold_1m', 'subscription', 'gold', 1, 30, 'Gold 1 Month'),
            ('gold_6m', 'subscription', 'gold', 1, 180, 'Gold 6 Months'),
            ('gold_12m', 'subscription', 'gold', 1, 365, 'Gold 12 Months'),
            ('platinum_1m', 'subscription', 'platinum', 1, 30, 'Platinum 1 Month'),
            ('platinum_6m', 'subscription', 'platinum', 1, 180, 'Platinum 6 Months'),
            ('platinum_12m', 'subscription', 'platinum', 1, 365, 'Platinum 12 Months'),
            ('super_like_3', 'consumable', 'super_like', 3, None, 'Super Like x3'),
            ('super_like_5', 'consumable', 'super_like', 5, None, 'Super Like x5'),
            ('super_like_15', 'consumable', 'super_like', 15, None, 'Super Like x15'),
            ('boost_3', 'consumable', 'boost', 3, None, 'Boost x3'),
            ('boost_5', 'consumable', 'boost', 5, None, 'Boost x5'),
            ('boost_10', 'consumable', 'boost', 10, None, 'Boost x10'),
            ('extend_1', 'consumable', 'extend', 1, None, 'Extend x1'),
            ('extend_3', 'consumable', 'extend', 3, None, 'Extend x3'),
            ('extend_5', 'consumable', 'extend', 5, None, 'Extend x5'),
            ('rematch_1', 'consumable', 'rematch', 1, None, 'Rematch x1'),
            ('rematch_3', 'consumable', 'rematch', 3, None, 'Rematch x3'),
            ('hive_1', 'consumable', 'hive', 1, None, 'Hive access'),
            ('connect_1', 'consumable', 'connect', 1, None, 'Connect boost'),
            ('date_night_1', 'consumable', 'date_night', 1, None, 'Date Night'),
            ('rewind_3', 'consumable', 'rewind', 3, None, 'Rewind x3'),
            ('rewind_5', 'consumable', 'rewind', 5, None, 'Rewind x5'),
            ('rewind_15', 'consumable', 'rewind', 15, None, 'Rewind x15'),
            ('likes_unlock_1', 'consumable', 'likes_unlock', 1, None, 'Likes Unlock x1'),
            ('likes_unlock_5', 'consumable', 'likes_unlock', 5, None, 'Likes Unlock x5'),
        ]
        swipe_titles = {
            'plus_1m': 'Premium 1 Month', 'plus_6m': 'Premium 6 Months', 'plus_12m': 'Premium 12 Months',
            'gold_1m': 'Premium+ 1 Month', 'gold_6m': 'Premium+ 6 Months', 'gold_12m': 'Premium+ 12 Months',
            'platinum_1m': 'Premium+ Spotlight 1 Month', 'platinum_6m': 'Premium+ Spotlight 6 Months',
            'platinum_12m': 'Premium+ Spotlight 12 Months',
            'super_like_3': 'Compliment x3', 'super_like_5': 'Compliment x5', 'super_like_15': 'Compliment x15',
            'boost_3': 'Spotlight x3', 'boost_5': 'Spotlight x5', 'boost_10': 'Spotlight x10',
            'extend_1': 'Extend x1', 'extend_3': 'Extend x3', 'extend_5': 'Extend x5',
            'rematch_1': 'Rematch x1', 'rematch_3': 'Rematch x3',
            'hive_1': 'Hive', 'connect_1': 'Connect', 'date_night_1': 'Date Night',
            'rewind_3': 'Rewind x3', 'rewind_5': 'Rewind x5', 'rewind_15': 'Rewind x15',
            'likes_unlock_1': 'See Who Likes You x1', 'likes_unlock_5': 'See Who Likes You x5',
        }
        matchup_titles = {
            'plus_1m': '会员·月卡', 'plus_6m': '会员·半年卡', 'plus_12m': '会员·年卡',
            'gold_1m': '高级会员·月卡', 'gold_6m': '高级会员·半年卡', 'gold_12m': '高级会员·年卡',
            'platinum_1m': '至尊会员·月卡', 'platinum_6m': '至尊会员·半年卡', 'platinum_12m': '至尊会员·年卡',
            'super_like_3': '超级喜欢×3', 'super_like_5': '超级喜欢×5', 'super_like_15': '超级喜欢×15',
            'boost_3': '曝光加速×3', 'boost_5': '曝光加速×5', 'boost_10': '曝光加速×10',
            'rewind_3': '撤回×3', 'rewind_5': '撤回×5', 'rewind_15': '撤回×15',
            'likes_unlock_1': '解锁喜欢×1', 'likes_unlock_5': '解锁喜欢×5',
        }
        app_sku_titles = {
            'spark_main': {pid: title for pid, st, tier, qty, days, title in skus},
            'swipe_main': swipe_titles,
            'matchup_main': matchup_titles,
        }

        for app_id, title_map in app_sku_titles.items():
            for pid, st, tier, qty, days, default_title in skus:
                title = title_map.get(pid, default_title)
                SkuMap.objects.update_or_create(
                    app_id=app_id, product_id=pid,
                    defaults={
                        'sku_type': st, 'tier': tier, 'quantity': qty,
                        'duration_days': days, 'title': title, 'is_active': True,
                    },
                )
            SkuMap.objects.filter(app_id=app_id, product_id='boost_1').update(is_active=False)

        # O-04: ember/flick inherit spark SkuMap when missing
        spark_skus = list(SkuMap.objects.filter(app_id='spark_main', is_active=True))
        for target_app in ('ember_main', 'flick_main'):
            if SkuMap.objects.filter(app_id=target_app).exists():
                continue
            for row in spark_skus:
                SkuMap.objects.create(
                    app_id=target_app,
                    product_id=row.product_id,
                    sku_type=row.sku_type,
                    tier=row.tier,
                    quantity=row.quantity,
                    duration_days=row.duration_days,
                    title=row.title,
                    is_active=row.is_active,
                )
            self.stdout.write(f'copied SkuMap spark_main → {target_app} ({len(spark_skus)} rows)')

        default_admin_pw = 'SparkAdmin1'
        admin_password = os.environ.get('SEED_ADMIN_PASSWORD') or default_admin_pw
        if admin_password == default_admin_pw:
            self.stdout.write(self.style.WARNING(
                'Using default admin password SparkAdmin1; set SEED_ADMIN_PASSWORD for non-local envs'
            ))

        admin, created = User.objects.get_or_create(
            email='admin@spark.app',
            defaults={
                'username': 'spark_admin',
                'password': admin_password,
                'role': 'super_admin',
                'nickname': 'Admin',
                'profile_complete': True,
            },
        )
        if created:
            self.stdout.write(f'created admin@spark.app (password from SEED_ADMIN_PASSWORD or default)')
        elif os.environ.get('SEED_ADMIN_PASSWORD'):
            admin.password = admin_password
            admin.save(update_fields=['password'])
            self.stdout.write('updated admin password from SEED_ADMIN_PASSWORD')

        # legacy App Admin role removed — migrate leftover accounts
        from models.models import AdminRolePermission
        migrated = User.objects.filter(role='admin').update(role='operator')
        AdminRolePermission.objects.filter(role='admin').delete()
        if migrated:
            self.stdout.write(f'migrated {migrated} App Admin → operator')

        test, created = User.objects.get_or_create(
            email='test@spark.app',
            defaults={
                'username': 'spark_test',
                'password': 'SparkTest1',
                'role': 'user',
                'nickname': 'Tester',
                'birthday': date(1998, 5, 1),
                'gender': 'male',
                'job': 'Engineer',
                'city': 'Shanghai',
                'bio': 'Looking for genuine connections.',
                'profile_complete': True,
                'is_verified': True,
                'mbti': 'INTJ',
                'zodiac': 'Taurus',
                'relationship': 'Serious',
                'avatar_url': DEMO_PHOTOS[0],
            },
        )
        # always refresh password for demo convenience
        test.password = 'SparkTest1'
        test.profile_complete = True
        test.save()
        if not test.photos.exists():
            for i, url in enumerate(DEMO_PHOTOS):
                UserPhoto.objects.create(
                    user=test, url=url, sort_order=i, is_primary=i == 0, audit_status='approved',
                )
        else:
            test.photos.filter(audit_status='pending').update(audit_status='approved')
        ensure_daily_likes(test)
        grant_ledger(test, EntitlementLedger.SUPER_LIKE, 5)
        grant_ledger(test, EntitlementLedger.BOOST, 2)
        grant_ledger(test, EntitlementLedger.REWIND, 3)
        self.stdout.write('ready test@spark.app / SparkTest1')

        demo_users = []
        for i, name in enumerate(['Nina', 'Ava', 'Mia', 'Zoe', 'Luna']):
            email = f'{name.lower()}@spark.demo'
            u, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': f'demo_{name.lower()}',
                    'password': 'SparkDemo1',
                    'nickname': name,
                    'birthday': date(2000, 3, 15 + i),
                    'gender': 'female',
                    'job': 'UX Desinger' if i == 0 else 'Designer',
                    'city': 'California',
                    'bio': 'I love museum stand-up comedy; sincerity comes first. Looking for someone who is sincere, gentle, somewhat introverted, and empathetic.',
                    'is_verified': True,
                    'is_traveling': True,
                    'profile_complete': True,
                    'mbti': 'ENTP',
                    'zodiac': 'Virgo',
                    'relationship': 'Open Relationship',
                    'avatar_url': DEMO_PHOTOS[i % len(DEMO_PHOTOS)],
                    'looking_for': 'Someone sincere and gentle',
                    'interests': ['Travel', 'Art', 'Coffee'],
                    'social_links': {'instagram': f'@{name.lower()}'},
                },
            )
            if not u.photos.exists():
                for j, url in enumerate(DEMO_PHOTOS):
                    UserPhoto.objects.create(
                        user=u, url=url, sort_order=j, is_primary=j == 0, audit_status='approved',
                    )
            else:
                u.photos.filter(audit_status='pending').update(audit_status='approved')
            demo_users.append(u)

        # incoming likes toward tester (for Likes tab)
        for u in demo_users[:3]:
            Swipe.objects.filter(actor=u, target=test, is_undone=False).update(is_undone=True)
            Swipe.objects.create(actor=u, target=test, action='like')

        # mutual match with Nina + conversation
        nina = demo_users[0]
        Swipe.objects.filter(actor=test, target=nina, is_undone=False).update(is_undone=True)
        Swipe.objects.create(actor=test, target=nina, action='like')
        a, b = sorted([test.id, nina.id])
        match, _ = get_or_create_pair_match(a, b, expire_days=7)
        match.status = 'active'
        match.expire_at = timezone.now() + timedelta(days=7)
        match.save(update_fields=['status', 'expire_at'])
        conv, _ = Conversation.objects.get_or_create(
            match=match,
            defaults={'user_a_id': a, 'user_b_id': b},
        )
        if not conv.messages.exists():
            Message.objects.create(conversation=conv, sender=nina, content='Hey! Nice to meet you ✨')
            conv.last_message = 'Hey! Nice to meet you ✨'
            conv.last_at = timezone.now()
            conv.save(update_fields=['last_message', 'last_at'])

        # Robot funnel cards — only wipe when --reset-demo
        if reset_demo:
            FunnelPool.objects.filter(app_id='spark_main').delete()
            for i in range(8):
                FunnelPool.objects.create(
                    app_id='spark_main', pool='robot', nickname=['Nina', 'Ava', 'Mia', 'Zoe'][i % 4],
                    age=22 + i, job='UX Desinger', city='California',
                    bio='I love museum stand-up comedy; sincerity comes first.',
                    photo_urls=DEMO_PHOTOS, tags=['Travel', 'Art'], mbti='ENTP', zodiac='Virgo',
                    relationship='Open Relationship', is_traveling=True, is_verified=True,
                    sort_order=i,
                    linked_user=demo_users[i % len(demo_users)],
                )
            for i in range(5):
                FunnelPool.objects.create(
                    app_id='spark_main', pool='robot', nickname=f'Like{i}', age=24,
                    photo_urls=DEMO_PHOTOS[:1], sort_order=100 + i,
                )
            self.stdout.write('reset FunnelPool demo robots')
        elif not FunnelPool.objects.filter(app_id='spark_main', pool='robot').exists():
            for i in range(8):
                FunnelPool.objects.create(
                    app_id='spark_main', pool='robot', nickname=['Nina', 'Ava', 'Mia', 'Zoe'][i % 4],
                    age=22 + i, job='UX Desinger', city='California',
                    bio='I love museum stand-up comedy; sincerity comes first.',
                    photo_urls=DEMO_PHOTOS, tags=['Travel', 'Art'], mbti='ENTP', zodiac='Virgo',
                    relationship='Open Relationship', is_traveling=True, is_verified=True,
                    sort_order=i,
                    linked_user=demo_users[i % len(demo_users)],
                )
            self.stdout.write('seeded FunnelPool (was empty)')

        from models.models import FunnelAbcRule, UserRecommendStat
        FunnelAbcRule.objects.update_or_create(
            app_id='spark_main', country='*', locale='*',
            defaults={'a_percent': 20, 'b_percent': 40, 'c_percent': 40, 'priority': 0},
        )
        # Seed recommend stats so ABC ranking has data
        for i, u in enumerate(demo_users):
            impressions = 100 - i * 8
            rights = max(5, 80 - i * 12)
            rate = rights / impressions if impressions else 0
            UserRecommendStat.objects.update_or_create(
                user=u,
                defaults={
                    'app_id': 'spark_main',
                    'impression_count': impressions,
                    'right_swipe_count': rights,
                    'rate': rate,
                    'grade': 'C',
                },
            )
        from tools.spark_helpers import recompute_abc_grades
        recompute_abc_grades('spark_main', '*')

        # Review mode rows — package_name must match AppConfig / client (O-03)
        from tools.app_modules import DEFAULT_PACKAGE_BY_APP
        for app_id, pkg in DEFAULT_PACKAGE_BY_APP.items():
            for platform in ('ios', 'android'):
                ReviewMode.objects.update_or_create(
                    app_id=app_id, platform=platform,
                    package_name=pkg, version='1.0.0',
                    defaults={'enabled': False},
                )
        # Remove legacy mismatched package rows
        ReviewMode.objects.filter(package_name='com.spark.app').delete()

        # Safety demo words
        for w in ('scamxxx', 'spamlink', 'fraudpay'):
            WordFilter.objects.get_or_create(
                app_id='spark_main', country='*', word=w,
                defaults={'kind': 'ban'},
            )

        for d in ('instagram.com', 'spotify.com', 'twitter.com', 'x.com'):
            DomainWhitelist.objects.get_or_create(app_id='spark_main', domain=d)

        # Pending report for Safety admin
        if demo_users:
            Report.objects.get_or_create(
                reporter=test, target_user=demo_users[-1],
                defaults={
                    'app_id': 'spark_main',
                    'reason': 'spam',
                    'detail': 'Seed demo report',
                    'status': 'pending',
                },
            )
            # One pending photo for Safety audit queue demo
            if not UserPhoto.objects.filter(user=test, audit_status='pending').exists():
                UserPhoto.objects.create(
                    user=test,
                    url='https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400',
                    sort_order=99,
                    is_primary=False,
                    audit_status='pending',
                )

        # Expired Say Hi for Sent list demo
        zoe = demo_users[3] if len(demo_users) > 3 else demo_users[-1]
        Swipe.objects.filter(actor=test, target=zoe, is_undone=False).update(is_undone=True)
        Swipe.objects.create(actor=test, target=zoe, action='like')
        SayHi.objects.filter(sender=test, receiver=zoe).delete()
        SayHi.objects.create(
            sender=test, receiver=zoe, message='Hi!', status='expired',
            expire_at=timezone.now() - timedelta(days=1),
        )

        self._seed_push_configs()

        self.stdout.write(self.style.SUCCESS('Spark seed completed (likes/match/chat/safety/push ready)'))

    def _seed_push_configs(self):
        """Default system push templates for Spark / Swipe / MatchUp × en/zh."""
        copy = {
            'spark_main': {
                'en': {
                    'new_like': ('Someone liked you', '{nickname} liked you. See who it is.', '/pages/likes/index'),
                    'new_match': ("It's a match!", 'You and {nickname} liked each other.', '/pages/chat/index'),
                    'new_message': ('New message', '{nickname}: {preview}', '/pages/chat/index'),
                    'silent_recall': {
                        1: ('Miss you already', 'Come back — someone may be waiting.', '/pages/discover/index'),
                        3: ('New people nearby', 'Open Spark and keep swiping.', '/pages/discover/index'),
                        7: ('We saved your spot', 'Your matches miss you on Spark.', '/pages/chat/index'),
                    },
                },
                'zh': {
                    'new_like': ('有人喜欢了你', '{nickname} 喜欢了你，去看看是谁', '/pages/likes/index'),
                    'new_match': ('配对成功！', '你和 {nickname} 互相喜欢了', '/pages/chat/index'),
                    'new_message': ('新消息', '{nickname}：{preview}', '/pages/chat/index'),
                    'silent_recall': {
                        1: ('有点想你了', '回来看看吧，也许有人在等你', '/pages/discover/index'),
                        3: ('附近有新人', '打开 Spark 继续滑动', '/pages/discover/index'),
                        7: ('位置还在', '你的匹配们在 Spark 等你', '/pages/chat/index'),
                    },
                },
            },
            'swipe_main': {
                'en': {
                    'new_like': ('New like', '{nickname} liked you — open while you can.', '/pages/likes/index'),
                    'new_match': ('You matched', 'Say hi to {nickname} first — the window is open.', '/pages/chat/index'),
                    'new_message': ('Message', '{nickname}: {preview}', '/pages/chat/index'),
                    'silent_recall': {
                        1: ('Your match window', 'Open bee before connections cool off.', '/pages/chat/index'),
                        3: ('Still waiting', 'Someone may still want to hear from you.', '/pages/discover/index'),
                        7: ('Come back to bee', 'Fresh faces and open chats await.', '/pages/discover/index'),
                    },
                },
                'zh': {
                    'new_like': ('新的喜欢', '{nickname} 喜欢了你，趁热打开看看', '/pages/likes/index'),
                    'new_match': ('匹配成功', '先和 {nickname} 打个招呼，开场窗还开着', '/pages/chat/index'),
                    'new_message': ('新消息', '{nickname}：{preview}', '/pages/chat/index'),
                    'silent_recall': {
                        1: ('开场还在', '回到 bee，别让连接冷却', '/pages/chat/index'),
                        3: ('还在等你', '也许有人仍想听到你的消息', '/pages/discover/index'),
                        7: ('回到 bee', '新面孔和未读聊天线等着你', '/pages/discover/index'),
                    },
                },
            },
            'matchup_main': {
                'en': {
                    'new_like': ('New spark', '{nickname} is interested — take a look.', '/pages/likes/index'),
                    'new_match': ('Heart matched', 'Continue the Q&A with {nickname}.', '/pages/chat/index'),
                    'new_message': ('Reply waiting', '{nickname}: {preview}', '/pages/chat/index'),
                    'qa_need_question': ('Your turn to ask', 'Ask {nickname} a question to open the chat.', '/pages/chat/index'),
                    'qa_need_answer': ('Please answer', '{nickname} asked you a question — answer to continue.', '/pages/chat/index'),
                    'qa_need_review': ('Please review', '{nickname} answered — review to open chat.', '/pages/chat/index'),
                    'silent_recall': {
                        1: ('Unfinished chat', 'Your 她说 thread is waiting.', '/pages/chat/index'),
                        3: ('Someone liked your vibe', 'Come back and keep the conversation going.', '/pages/discover/index'),
                        7: ('Missed connections', 'Open 她说 for hearts you left behind.', '/pages/likes/index'),
                    },
                },
                'zh': {
                    'new_like': ('新的心动', '{nickname} 对你有兴趣，去看看', '/pages/likes/index'),
                    'new_match': ('心动配对', '继续和 {nickname} 的问答吧', '/pages/chat/index'),
                    'new_message': ('有人回复', '{nickname}：{preview}', '/pages/chat/index'),
                    'qa_need_question': ('请出题', '给 {nickname} 出一道题，开启问答', '/pages/chat/index'),
                    'qa_need_answer': ('请回答', '{nickname} 向你提问了，认真回答吧', '/pages/chat/index'),
                    'qa_need_review': ('请审阅', '{nickname} 已回答，去决定是否开聊', '/pages/chat/index'),
                    'silent_recall': {
                        1: ('未完成的对话', '你的她说会话还在等你', '/pages/chat/index'),
                        3: ('有人喜欢你的感觉', '回来继续聊下去', '/pages/discover/index'),
                        7: ('错过的心动', '打开她说说看留下的喜欢', '/pages/likes/index'),
                    },
                },
            },
        }
        for app_id, locales in copy.items():
            for locale, events in locales.items():
                for event_type, payload in events.items():
                    if event_type == 'silent_recall':
                        for day, (title, body, link) in payload.items():
                            SystemPushConfig.objects.update_or_create(
                                app_id=app_id, locale=locale, event_type=event_type, recall_day=day,
                                defaults={
                                    'title_template': title,
                                    'body_template': body,
                                    'deep_link': link,
                                    'enabled': True,
                                    'daily_push_cap': 1,
                                },
                            )
                    else:
                        title, body, link = payload
                        SystemPushConfig.objects.update_or_create(
                            app_id=app_id, locale=locale, event_type=event_type, recall_day=0,
                            defaults={
                                'title_template': title,
                                'body_template': body,
                                'deep_link': link,
                                'enabled': True,
                                'daily_push_cap': 1,
                            },
                        )
