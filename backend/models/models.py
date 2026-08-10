from django.db import models
from django.db.models import Q
from django.utils import timezone
from tools.password_hasher import hash_password


class User(models.Model):
    """用户表"""
    VIP_NONE = 'none'
    VIP_PLUS = 'plus'
    VIP_GOLD = 'gold'
    VIP_PLATINUM = 'platinum'
    VIP_CHOICES = [
        (VIP_NONE, 'None'),
        (VIP_PLUS, 'Plus'),
        (VIP_GOLD, 'Gold'),
        (VIP_PLATINUM, 'Platinum'),
    ]

    LOGIN_EMAIL = 'email'
    LOGIN_GOOGLE = 'google'
    LOGIN_APPLE = 'apple'
    LOGIN_FACEBOOK = 'facebook'
    LOGIN_PHONE = 'phone'
    LOGIN_WECHAT = 'wechat'
    LOGIN_CHOICES = [
        (LOGIN_EMAIL, 'Email'),
        (LOGIN_GOOGLE, 'Google'),
        (LOGIN_APPLE, 'Apple'),
        (LOGIN_FACEBOOK, 'Facebook'),
        (LOGIN_PHONE, 'Phone'),
        (LOGIN_WECHAT, 'WeChat'),
    ]

    username = models.CharField(max_length=64, unique=True, verbose_name="用户名")
    # S-13 DEFERRED: global unique blocks same person across shells.
    # Do NOT change to (app_id, email) without a migration + login/token plan.
    email = models.EmailField(unique=True, verbose_name="邮箱")
    password = models.CharField(max_length=256, verbose_name="密码")
    role = models.CharField(max_length=20, default="user", verbose_name="角色")
    status = models.IntegerField(default=1, verbose_name="状态")
    firebase_uid = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    phone = models.CharField(max_length=32, null=True, blank=True, unique=True, db_index=True)
    login_type = models.CharField(
        max_length=16, default=LOGIN_EMAIL, choices=LOGIN_CHOICES, db_index=True,
        verbose_name="登录方式",
    )
    nickname = models.CharField(max_length=64, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    job = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=64, null=True, blank=True)
    country = models.CharField(max_length=64, null=True, blank=True, default='*')
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    passport_city = models.CharField(max_length=64, null=True, blank=True)
    passport_lat = models.FloatField(null=True, blank=True)
    passport_lng = models.FloatField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_traveling = models.BooleanField(default=False)
    online_at = models.DateTimeField(null=True, blank=True)
    has_recharged = models.BooleanField(default=False)
    vip_tier = models.CharField(max_length=16, default=VIP_NONE, choices=VIP_CHOICES)
    vip_expire_at = models.DateTimeField(null=True, blank=True)
    invisible_mode = models.BooleanField(default=False)
    hide_age = models.BooleanField(default=False)
    discovery_enabled = models.BooleanField(default=True)
    global_mode = models.BooleanField(default=False)
    orientation = models.CharField(max_length=64, null=True, blank=True)
    pronouns = models.CharField(max_length=64, null=True, blank=True)
    school = models.CharField(max_length=128, null=True, blank=True)
    height_cm = models.IntegerField(null=True, blank=True)
    languages = models.JSONField(default=list, blank=True)
    invite_code = models.CharField(max_length=16, null=True, blank=True, unique=True, db_index=True)
    looking_for_intent = models.CharField(max_length=32, null=True, blank=True)  # dating|bff|long_term|…
    mbti = models.CharField(max_length=8, null=True, blank=True)
    zodiac = models.CharField(max_length=16, null=True, blank=True)
    relationship = models.CharField(max_length=64, null=True, blank=True)
    looking_for = models.TextField(null=True, blank=True)
    lifestyle = models.JSONField(default=dict, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    interests = models.JSONField(default=list, blank=True)
    interest_votes = models.JSONField(default=dict, blank=True)  # {interest: count}
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    profile_complete = models.BooleanField(default=False)
    locale = models.CharField(max_length=16, default='en')
    avatar_url = models.CharField(max_length=512, null=True, blank=True)
    admin_app_ids = models.JSONField(default=list, blank=True)
    admin_permissions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('$2b$'):
            self.password = hash_password(self.password[:72])
        super().save(*args, **kwargs)

    @property
    def age(self):
        if not self.birthday:
            return None
        today = timezone.now().date()
        return today.year - self.birthday.year - (
            (today.month, today.day) < (self.birthday.month, self.birthday.day)
        )

    @property
    def is_online(self):
        if not self.online_at:
            return False
        return (timezone.now() - self.online_at).total_seconds() < 300

    @property
    def effective_vip(self):
        if self.vip_tier == self.VIP_NONE:
            return self.VIP_NONE
        if self.vip_expire_at and self.vip_expire_at < timezone.now():
            return self.VIP_NONE
        return self.vip_tier

    class Meta:
        db_table = 't_user'
        verbose_name = "用户"
        indexes = [
            models.Index(
                fields=['app_id', 'status', 'gender', 'invisible_mode', 'has_recharged'],
                name='t_user_discover_filter_idx',
            ),
        ]


class Example(models.Model):
    STATUS_DRAFT = 0
    STATUS_ACTIVE = 1
    STATUS_DISABLED = 2
    STATUS_CHOICES = [
        (STATUS_DRAFT, '草稿'),
        (STATUS_ACTIVE, '启用'),
        (STATUS_DISABLED, '禁用'),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    status = models.IntegerField(default=STATUS_ACTIVE, choices=STATUS_CHOICES)
    sort_order = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    remark = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_example'
        ordering = ['sort_order', '-created_at']


class UserPhoto(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photos')
    url = models.CharField(max_length=512)
    sort_order = models.IntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    audit_status = models.CharField(max_length=16, default='approved')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_user_photo'
        ordering = ['sort_order', 'id']


class UserFilter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='filters')
    gender = models.CharField(max_length=16, null=True, blank=True)
    age_min = models.IntegerField(default=18)
    age_max = models.IntegerField(default=50)
    distance_km = models.IntegerField(default=100)
    relationship = models.CharField(max_length=64, null=True, blank=True)
    language = models.CharField(max_length=32, null=True, blank=True)
    zodiac = models.CharField(max_length=16, null=True, blank=True)
    education = models.CharField(max_length=64, null=True, blank=True)
    mbti = models.CharField(max_length=8, null=True, blank=True)
    recommend_type = models.CharField(max_length=16, default='precise')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_user_filter'


class Block(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks')
    blocked_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_block'
        unique_together = ('user', 'blocked_user')


class Report(models.Model):
    REASON_SPAM = 'spam'
    REASON_HARASSMENT = 'harassment'
    REASON_INAPPROPRIATE = 'inappropriate'
    REASON_FAKE = 'fake'
    REASON_UNDERAGE = 'underage'
    REASON_OTHER = 'other'
    REASON_CHOICES = [
        (REASON_SPAM, 'Spam'),
        (REASON_HARASSMENT, 'Harassment'),
        (REASON_INAPPROPRIATE, 'Inappropriate'),
        (REASON_FAKE, 'Fake profile'),
        (REASON_UNDERAGE, 'Underage'),
        (REASON_OTHER, 'Other'),
    ]
    ALLOWED_REASONS = {c[0] for c in REASON_CHOICES}

    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received', null=True)
    target_type = models.CharField(max_length=32, default='user')
    reason = models.CharField(max_length=128, default=REASON_OTHER)
    detail = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=16, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_report'


class EmergencyContact(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='emergency_contact')
    name = models.CharField(max_length=64, blank=True, default='')
    phone = models.CharField(max_length=32, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_emergency_contact'


class DateShare(models.Model):
    """Share date venue/time with a trusted contact (link + optional SMS log)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='date_shares')
    peer_name = models.CharField(max_length=64, blank=True, default='')
    place = models.CharField(max_length=256, blank=True, default='')
    venue = models.CharField(max_length=256, blank=True, default='')
    when_text = models.CharField(max_length=128, blank=True, default='')
    meet_at = models.DateTimeField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    note = models.TextField(blank=True, default='')
    share_token = models.CharField(max_length=64, null=True, blank=True, unique=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    sms_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_date_share'
        ordering = ['-id']


class Swipe(models.Model):
    LIKE = 'like'
    PASS = 'pass'
    SUPER = 'super_like'
    ACTION_CHOICES = [(LIKE, 'Like'), (PASS, 'Pass'), (SUPER, 'Super Like')]

    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swipes_made')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swipes_received')
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    is_priority = models.BooleanField(default=False)  # Platinum Priority Like → receiver feed boost
    is_undone = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_swipe'
        indexes = [
            models.Index(fields=['actor', 'target', 'is_undone']),
            models.Index(fields=['target', 'is_priority', 'is_undone']),
            models.Index(fields=['target', 'action', 'is_undone', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['actor', 'target'],
                condition=Q(is_undone=False),
                name='t_swipe_actor_target_active_uniq',
            ),
        ]


class Match(models.Model):
    MSG_ANY = 'any'
    MSG_WOMEN_FIRST = 'women_first'
    MSG_QA_GATE = 'qa_gate'
    MESSAGING_CHOICES = [
        (MSG_ANY, 'Any'),
        (MSG_WOMEN_FIRST, 'Women first'),
        (MSG_QA_GATE, 'QA gate (她说)'),
    ]

    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_a')
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_b')
    status = models.CharField(max_length=16, default='active')
    expire_at = models.DateTimeField(null=True, blank=True)
    messaging_mode = models.CharField(max_length=32, default=MSG_ANY, choices=MESSAGING_CHOICES)
    opener_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches_as_opener',
    )
    opened_at = models.DateTimeField(null=True, blank=True)
    extend_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_match'
        constraints = [
            models.UniqueConstraint(fields=['user_a', 'user_b'], name='t_match_user_a_user_b_uniq'),
        ]
        indexes = [
            models.Index(fields=['status', 'expire_at']),
            models.Index(fields=['user_a', 'status']),
            models.Index(fields=['user_b', 'status']),
        ]


class MatchQA(models.Model):
    """她说-style: female asks → male answers → female approves → free chat."""
    STATUS_NEED_QUESTION = 'need_question'
    STATUS_NEED_ANSWER = 'need_answer'
    STATUS_NEED_REVIEW = 'need_review'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_NEED_QUESTION, 'Need question'),
        (STATUS_NEED_ANSWER, 'Need answer'),
        (STATUS_NEED_REVIEW, 'Need review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='qa')
    asker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qa_asked')
    answerer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qa_answered')
    question = models.CharField(max_length=500, blank=True, default='')
    answer = models.CharField(max_length=1000, blank=True, default='')
    status = models.CharField(max_length=32, default=STATUS_NEED_QUESTION, choices=STATUS_CHOICES)
    expire_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_match_qa'


class Compliment(models.Model):
    """Bumble-like pre-match compliment on a photo/bio (consumes super_like ledger)."""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compliments_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compliments_received')
    photo_url = models.CharField(max_length=512, null=True, blank=True)
    target_kind = models.CharField(max_length=32, default='photo')  # photo|bio|prompt
    message = models.CharField(max_length=150)
    status = models.CharField(max_length=16, default='pending')  # pending|matched|expired
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_compliment'
        indexes = [models.Index(fields=['receiver', 'status'])]


class SayHi(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='say_hi_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='say_hi_received')
    message = models.CharField(max_length=256, null=True, blank=True)
    status = models.CharField(max_length=16, default='pending')
    expire_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_say_hi'


class EntitlementLedger(models.Model):
    SUPER_LIKE = 'super_like'
    BOOST = 'boost'
    DAILY_LIKE = 'daily_like'
    REWIND = 'rewind'
    DAILY_FEED = 'daily_feed'
    LIKES_UNLOCK = 'likes_unlock'
    EXTEND = 'extend'
    REMATCH = 'rematch'
    HIVE = 'hive'
    CONNECT = 'connect'
    DATE_NIGHT = 'date_night'
    KIND_CHOICES = [
        (SUPER_LIKE, 'Super Like'),
        (BOOST, 'Boost'),
        (DAILY_LIKE, 'Daily Like'),
        (REWIND, 'Rewind'),
        (DAILY_FEED, 'Daily Feed Cap'),
        (LIKES_UNLOCK, 'Likes Unlock'),
        (EXTEND, 'Extend'),
        (REMATCH, 'Rematch'),
        (HIVE, 'Hive'),
        (CONNECT, 'Connect'),
        (DATE_NIGHT, 'Date Night'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='entitlements')
    kind = models.CharField(max_length=32, choices=KIND_CHOICES)
    balance = models.IntegerField(default=0)
    period_key = models.CharField(max_length=32, default='', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_entitlement_ledger'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'kind', 'period_key'],
                name='t_entitlement_user_kind_period_uniq',
            ),
        ]


class BoostSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='boosts')
    start_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    impressions = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    matches = models.IntegerField(default=0)

    class Meta:
        db_table = 't_boost_session'
        indexes = [
            models.Index(fields=['is_active', 'end_at']),
            models.Index(fields=['user', 'is_active', 'end_at']),
        ]


class TopPicksSnapshot(models.Model):
    """Daily Top Picks set per user (Gold+)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='top_picks')
    pick_ids = models.JSONField(default=list, blank=True)
    refresh_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_top_picks_snapshot'
        indexes = [models.Index(fields=['user', 'refresh_at'])]


class LikeUnlock(models.Model):
    """One-off reveal of a received like without Gold."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='like_unlocks')
    swipe = models.ForeignKey(Swipe, on_delete=models.CASCADE, related_name='unlocks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_like_unlock'
        unique_together = ('user', 'swipe')


class UserSafetyPref(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='safety_pref')
    emergency_contact = models.JSONField(default=dict, blank=True)  # {name, phone}
    blocked_words = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_user_safety_pref'


class SwipeNightSession(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=16, default='open')  # open|closed|settled
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_swipe_night_session'


class SwipeNightPick(models.Model):
    session = models.ForeignKey(SwipeNightSession, on_delete=models.CASCADE, related_name='picks')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='night_picks_made')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='night_picks_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_swipe_night_pick'
        unique_together = ('session', 'actor', 'target')


class MatchmakerInvite(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_MATCHED = 'matched'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_DECLINED, 'Declined'),
        (STATUS_MATCHED, 'Matched'),
    ]
    matchmaker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matchmaker_invites')
    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matchmaker_as_a')
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matchmaker_as_b')
    message = models.CharField(max_length=256, blank=True, default='')
    a_status = models.CharField(max_length=16, default=STATUS_PENDING, choices=STATUS_CHOICES)
    b_status = models.CharField(max_length=16, default=STATUS_PENDING, choices=STATUS_CHOICES)
    match = models.ForeignKey(Match, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_matchmaker_invite'


class CampusProfile(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_VERIFIED = 'verified'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='campus')
    school = models.CharField(max_length=128)
    edu_email = models.EmailField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    status = models.CharField(max_length=16, default=STATUS_PENDING, choices=STATUS_CHOICES, db_index=True)
    reject_reason = models.CharField(max_length=256, blank=True, default='')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_campus_profile'

    def sync_verified_flag(self):
        self.verified = self.status == self.STATUS_VERIFIED



class SelectQueue(models.Model):
    STATUS_APPLIED = 'applied'
    STATUS_SELECTED = 'selected'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_SELECTED, 'Selected'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='select_queue')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    status = models.CharField(max_length=16, default=STATUS_APPLIED, choices=STATUS_CHOICES)
    note = models.CharField(max_length=256, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_select_queue'
        unique_together = ('user', 'app_id')


class FaceToFaceSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='f2f_sessions')
    lat = models.FloatField()
    lng = models.FloatField()
    radius_km = models.FloatField(default=2.0)
    start_at = models.DateTimeField(auto_now_add=True)
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 't_face_to_face_session'


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    product_id = models.CharField(max_length=128)
    platform = models.CharField(max_length=16, default='mock')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default='USD')
    status = models.CharField(max_length=16, default='pending')
    firebase_order_id = models.CharField(max_length=128, null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_order'


class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    status = models.CharField(max_length=16, default='success')
    transaction_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_payment'


class SkuMap(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main')
    product_id = models.CharField(max_length=128)
    sku_type = models.CharField(max_length=32)
    tier = models.CharField(max_length=16, null=True, blank=True)
    quantity = models.IntegerField(default=1)
    duration_days = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 't_sku_map'
        unique_together = ('app_id', 'product_id')


class AppConfig(models.Model):
    app_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    package_name = models.CharField(max_length=128, null=True, blank=True)
    tos_url = models.CharField(max_length=512, null=True, blank=True)
    privacy_url = models.CharField(max_length=512, null=True, blank=True)
    config = models.JSONField(default=dict, blank=True)  # product_profile, enabled_modules
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_app'


class CountryConfig(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main')
    country = models.CharField(max_length=16, default='*')
    config = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_country_config'
        unique_together = ('app_id', 'country')


class FunnelPool(models.Model):
    """Robot / bot recommendation cards for the funnel."""
    POOL_ROBOT = 'robot'
    POOL_A = 'A'  # legacy alias → treat as robot
    POOL_B = 'B'  # legacy → robot
    POOL_C = 'C'  # legacy
    POOL_CHOICES = [
        (POOL_ROBOT, 'Robot'),
        (POOL_A, 'A (legacy)'),
        (POOL_B, 'B (legacy)'),
        (POOL_C, 'C (legacy)'),
    ]
    app_id = models.CharField(max_length=64, default='spark_main')
    country = models.CharField(max_length=16, default='*')
    locale = models.CharField(max_length=16, default='en')
    pool = models.CharField(max_length=16, choices=POOL_CHOICES, default=POOL_ROBOT)
    nickname = models.CharField(max_length=64)
    age = models.IntegerField(default=24)
    job = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=64, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    photo_urls = models.JSONField(default=list)
    tags = models.JSONField(default=list, blank=True)
    mbti = models.CharField(max_length=8, null=True, blank=True)
    zodiac = models.CharField(max_length=16, null=True, blank=True)
    relationship = models.CharField(max_length=64, null=True, blank=True)
    is_traveling = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=True)
    # Legacy DB field; blur is a client display concern, not a card type.
    blur = models.BooleanField(default=False)
    linked_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_funnel_pool'

    @property
    def is_robot(self):
        return self.pool in (self.POOL_ROBOT, self.POOL_A, self.POOL_B, self.POOL_C)


class FunnelAbcRule(models.Model):
    """Real-user recommend rule: A/B/C mix by region × language."""
    app_id = models.CharField(max_length=64, default='spark_main')
    country = models.CharField(max_length=16, default='*')  # region
    locale = models.CharField(max_length=16, default='*')  # language, * = all
    priority = models.IntegerField(default=0, db_index=True)  # larger = higher
    a_percent = models.IntegerField(default=20)  # A share in feed
    b_percent = models.IntegerField(default=40)  # B share in feed
    c_percent = models.IntegerField(default=40)  # C share in feed
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_funnel_abc_rule'
        unique_together = ('app_id', 'country', 'locale')
        ordering = ['-priority', '-id']


class RobotRecommendList(models.Model):
    """Which robot cards are served for an App × country × language."""
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    country = models.CharField(max_length=16, default='*')
    locale = models.CharField(max_length=16, default='en')
    priority = models.IntegerField(default=0, db_index=True)  # larger = higher
    name = models.CharField(max_length=128, default='')
    robot_ids = models.JSONField(default=list, blank=True)  # FunnelPool ids
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_robot_recommend_list'
        unique_together = ('app_id', 'country', 'locale')
        ordering = ['-priority', '-id']


class UserRecommendStat(models.Model):
    """Per-user funnel metrics for ABC ranking."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='recommend_stat')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    impression_count = models.IntegerField(default=0)
    right_swipe_count = models.IntegerField(default=0)
    rate = models.FloatField(default=0)  # right / impression
    grade = models.CharField(max_length=1, default='C')  # A / B / C
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_user_recommend_stat'


class ReviewMode(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main')
    platform = models.CharField(max_length=16)
    package_name = models.CharField(max_length=128)
    version = models.CharField(max_length=32)
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_review_mode'
        unique_together = ('app_id', 'platform', 'package_name', 'version')


class AdLink(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    country = models.CharField(max_length=16, default='*')
    name = models.CharField(max_length=128)
    deep_link = models.CharField(max_length=512)
    tag = models.CharField(max_length=64, null=True, blank=True)
    campaign_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    source = models.CharField(max_length=32, default='manual')  # manual | google_ads
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_ad_link'


class WordFilter(models.Model):
    """Chat text filter. kind='ban' blocks; kind='allow' whitelist strips before ban match (O-12)."""
    app_id = models.CharField(max_length=64, default='spark_main')
    country = models.CharField(max_length=16, default='*')
    word = models.CharField(max_length=128)
    kind = models.CharField(max_length=32, default='ban')  # ban | allow

    class Meta:
        db_table = 't_word_filter'


class DomainWhitelist(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main')
    domain = models.CharField(max_length=128)

    class Meta:
        db_table = 't_domain_whitelist'


class AnalyticsEvent(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    event = models.CharField(max_length=64, db_index=True)
    props = models.JSONField(default=dict, blank=True)
    app_version = models.CharField(max_length=32, null=True, blank=True)
    device_locale = models.CharField(max_length=16, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 't_event'
        indexes = [
            models.Index(fields=['app_id', 'created_at'], name='t_event_app_created_idx'),
            models.Index(fields=['app_id', 'event', 'created_at'], name='t_event_app_evt_created_idx'),
        ]


class Conversation(models.Model):
    ORIGIN_DATING = 'dating'
    ORIGIN_QUICK_MATCH = 'quick_match'
    ORIGIN_CHOICES = [
        (ORIGIN_DATING, 'Dating'),
        (ORIGIN_QUICK_MATCH, 'Quick match'),
    ]

    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='conversation', null=True, blank=True)
    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_a')
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_b')
    origin = models.CharField(max_length=32, default=ORIGIN_DATING, choices=ORIGIN_CHOICES, db_index=True)
    last_message = models.CharField(max_length=512, null=True, blank=True)
    last_at = models.DateTimeField(null=True, blank=True, db_index=True)
    unread_count_a = models.IntegerField(default=0)
    unread_count_b = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_conversation'
        indexes = [
            models.Index(fields=['-last_at', '-id'], name='t_conversation_last_at_id_idx'),
        ]

    def unread_for(self, user):
        uid = getattr(user, 'id', user)
        if uid == self.user_a_id:
            return self.unread_count_a
        if uid == self.user_b_id:
            return self.unread_count_b
        return 0


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    msg_type = models.CharField(max_length=16, default='text')  # text|image|photo|voice|audio|gif
    content = models.TextField()
    # Voice duration in milliseconds (0 for non-voice / unknown).
    duration_ms = models.IntegerField(default=0)
    translated = models.TextField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_message'
        ordering = ['id']
        indexes = [
            models.Index(fields=['conversation', '-id'], name='t_message_conv_id_desc_idx'),
        ]


class DiscoverParam(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main')
    country = models.CharField(max_length=16, default='*')
    daily_like_limit = models.IntegerField(default=50)
    match_expire_days = models.IntegerField(default=7)
    say_hi_expire_days = models.IntegerField(default=14)
    free_say_hi_replies = models.IntegerField(default=2)
    like_bonus_threshold = models.IntegerField(default=3)
    like_bonus_count = models.IntegerField(default=3)
    config = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_discover_param'
        unique_together = ('app_id', 'country')


class AdminRolePermission(models.Model):
    """Persisted role → menu permission overrides, scoped by app."""
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    role = models.CharField(max_length=32)
    permissions = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_admin_role_permission'
        unique_together = ('app_id', 'role')


class SystemPushConfig(models.Model):
    """Per-app × locale system push templates and caps."""
    EVENT_NEW_LIKE = 'new_like'
    EVENT_NEW_MATCH = 'new_match'
    EVENT_NEW_MESSAGE = 'new_message'
    EVENT_SILENT_RECALL = 'silent_recall'
    EVENT_QA_NEED_QUESTION = 'qa_need_question'
    EVENT_QA_NEED_ANSWER = 'qa_need_answer'
    EVENT_QA_NEED_REVIEW = 'qa_need_review'
    EVENT_CHOICES = [
        (EVENT_NEW_LIKE, 'New Like'),
        (EVENT_NEW_MATCH, 'New Match'),
        (EVENT_NEW_MESSAGE, 'New Message'),
        (EVENT_SILENT_RECALL, 'Silent Recall'),
        (EVENT_QA_NEED_QUESTION, 'QA Need Question'),
        (EVENT_QA_NEED_ANSWER, 'QA Need Answer'),
        (EVENT_QA_NEED_REVIEW, 'QA Need Review'),
    ]

    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    locale = models.CharField(max_length=16, default='en')
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES, db_index=True)
    recall_day = models.IntegerField(default=0)  # 1|3|7 for silent_recall; else 0
    title_template = models.CharField(max_length=256, default='')
    body_template = models.CharField(max_length=512, default='')
    enabled = models.BooleanField(default=True)
    daily_push_cap = models.IntegerField(default=1)
    delay_minutes_min = models.IntegerField(default=0)
    delay_minutes_max = models.IntegerField(default=0)
    deep_link = models.CharField(max_length=256, default='/pages/chat/index')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_system_push_config'
        unique_together = ('app_id', 'locale', 'event_type', 'recall_day')


class UserPushToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_tokens')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    platform = models.CharField(max_length=16, default='android')  # ios / android / h5
    client_id = models.CharField(max_length=256)
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_user_push_token'
        unique_together = ('user', 'app_id', 'platform')


class UserPushLedger(models.Model):
    """Daily push count for frequency control."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_ledgers')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    day = models.CharField(max_length=16)  # YYYY-MM-DD local
    push_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_user_push_ledger'
        unique_together = ('user', 'app_id', 'day')


class UserSilentRecallState(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='silent_recall_states')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    last_active_at = models.DateTimeField(null=True, blank=True)
    d1_sent_at = models.DateTimeField(null=True, blank=True)
    d3_sent_at = models.DateTimeField(null=True, blank=True)
    d7_sent_at = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_user_silent_recall'
        unique_together = ('user', 'app_id')


class ProviderConfig(models.Model):
    """Third-party vendor credentials (IAP / OAuth / Maps / Push / Translate / Verify).

    Global providers use app_id='_global_'. Secrets live in JSON config; admin API masks them.
    """
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    provider_key = models.CharField(max_length=64, db_index=True)
    config = models.JSONField(default=dict, blank=True)
    notes = models.CharField(max_length=512, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_provider_config'
        unique_together = ('app_id', 'provider_key')


class GoogleAdsCampaign(models.Model):
    """Cached Google Ads campaign + LAST_30_DAYS metrics for admin."""
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    customer_id = models.CharField(max_length=32, db_index=True)
    campaign_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=256, default='')
    status = models.CharField(max_length=32, default='')
    channel_type = models.CharField(max_length=64, default='')
    bidding_strategy_type = models.CharField(max_length=64, default='')
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    cost_micros = models.BigIntegerField(default=0)
    conversions = models.FloatField(default=0)
    ctr = models.FloatField(default=0)
    average_cpc = models.FloatField(default=0)
    metrics_window = models.CharField(max_length=32, default='LAST_30_DAYS')
    raw = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_google_ads_campaign'
        unique_together = ('app_id', 'customer_id', 'campaign_id')


class FacebookAdsCampaign(models.Model):
    """Cached Meta/Facebook Ads campaign + last_30d insights."""
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    ad_account_id = models.CharField(max_length=64, db_index=True)
    campaign_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=256, default='')
    status = models.CharField(max_length=64, default='')
    objective = models.CharField(max_length=64, default='')
    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    spend = models.FloatField(default=0)
    conversions = models.FloatField(default=0)
    ctr = models.FloatField(default=0)
    cpc = models.FloatField(default=0)
    reach = models.BigIntegerField(default=0)
    metrics_window = models.CharField(max_length=32, default='last_30d')
    raw = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_facebook_ads_campaign'
        unique_together = ('app_id', 'ad_account_id', 'campaign_id')


class AdAttribution(models.Model):
    """Install / open attribution for admin resolution (FB / Google / UTM)."""
    STATUS_PENDING = 'pending'
    STATUS_MATCHED = 'matched'
    STATUS_RESOLVED = 'resolved'
    STATUS_DISCARDED = 'discarded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_MATCHED, 'Matched'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_DISCARDED, 'Discarded'),
    ]
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('google', 'Google'),
        ('other', 'Other'),
    ]

    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='ad_attributions')
    platform = models.CharField(max_length=16, default='other', choices=PLATFORM_CHOICES, db_index=True)
    status = models.CharField(max_length=16, default=STATUS_PENDING, choices=STATUS_CHOICES, db_index=True)
    campaign_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    campaign_name = models.CharField(max_length=256, blank=True, default='')
    adset_id = models.CharField(max_length=64, null=True, blank=True)
    ad_id = models.CharField(max_length=64, null=True, blank=True)
    click_id = models.CharField(max_length=256, null=True, blank=True, db_index=True)
    utm_source = models.CharField(max_length=128, null=True, blank=True)
    utm_medium = models.CharField(max_length=128, null=True, blank=True)
    utm_campaign = models.CharField(max_length=128, null=True, blank=True)
    utm_content = models.CharField(max_length=128, null=True, blank=True)
    utm_term = models.CharField(max_length=128, null=True, blank=True)
    deep_link = models.CharField(max_length=512, null=True, blank=True)
    tag = models.CharField(max_length=64, null=True, blank=True)
    ad_link = models.ForeignKey(AdLink, null=True, blank=True, on_delete=models.SET_NULL, related_name='attributions')
    device_id = models.CharField(max_length=128, null=True, blank=True)
    props = models.JSONField(default=dict, blank=True)
    resolve_note = models.CharField(max_length=512, blank=True, default='')
    matched_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='resolved_attributions',
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_ad_attribution'
        indexes = [
            models.Index(fields=['app_id', 'status', '-created_at']),
            models.Index(fields=['app_id', 'platform', 'campaign_id']),
        ]


# ─── Parallel social domains (opt-in modules) ───────────────────────────────


class QmTicket(models.Model):
    """One-click match pool ticket — independent of dating Swipe/Match."""
    STATUS_WAITING = 'waiting'
    STATUS_MATCHED = 'matched'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_WAITING, 'Waiting'),
        (STATUS_MATCHED, 'Matched'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qm_tickets')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    status = models.CharField(max_length=16, default=STATUS_WAITING, choices=STATUS_CHOICES, db_index=True)
    prefer = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expire_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 't_qm_ticket'
        indexes = [models.Index(fields=['app_id', 'status', 'created_at'])]


class QmPair(models.Model):
    """Quick-match pair linked to a free-chat Conversation (origin=quick_match)."""
    STATUS_ACTIVE = 'active'
    STATUS_ENDED = 'ended'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ENDED, 'Ended'),
    ]

    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qm_pairs_a')
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qm_pairs_b')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    conversation = models.OneToOneField(
        Conversation, on_delete=models.CASCADE, related_name='qm_pair', null=True, blank=True,
    )
    status = models.CharField(max_length=16, default=STATUS_ACTIVE, choices=STATUS_CHOICES, db_index=True)
    matched_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 't_qm_pair'
        indexes = [models.Index(fields=['app_id', 'status', 'matched_at'])]


class ChatRoom(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_DISSOLVED = 'dissolved'
    STATUS_MUTED = 'muted'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_DISSOLVED, 'Dissolved'),
        (STATUS_MUTED, 'Muted'),
    ]

    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    name = models.CharField(max_length=128)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_chat_rooms')
    avatar = models.CharField(max_length=512, blank=True, default='')
    status = models.CharField(max_length=16, default=STATUS_ACTIVE, choices=STATUS_CHOICES, db_index=True)
    max_members = models.IntegerField(default=200)
    last_message = models.CharField(max_length=512, blank=True, default='')
    last_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_chat_room'


class ChatRoomMember(models.Model):
    ROLE_OWNER = 'owner'
    ROLE_ADMIN = 'admin'
    ROLE_MEMBER = 'member'
    ROLE_CHOICES = [
        (ROLE_OWNER, 'Owner'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MEMBER, 'Member'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_room_memberships')
    role = models.CharField(max_length=16, default=ROLE_MEMBER, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_chat_room_member'
        unique_together = ('room', 'user')


class ChatRoomMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_room_messages')
    msg_type = models.CharField(max_length=16, default='text')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_chat_room_message'
        ordering = ['id']


class Topic(models.Model):
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    title = models.CharField(max_length=128)
    cover = models.CharField(max_length=512, blank=True, default='')
    sort = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_topic'
        indexes = [models.Index(fields=['app_id', 'is_active', 'sort'])]


class Post(models.Model):
    TYPE_MOMENT = 'moment'
    TYPE_COMMUNITY = 'community'
    TYPE_VIDEO = 'video'
    TYPE_CHOICES = [
        (TYPE_MOMENT, 'Moment'),
        (TYPE_COMMUNITY, 'Community'),
        (TYPE_VIDEO, 'Video'),
    ]
    STATUS_VISIBLE = 'visible'
    STATUS_HIDDEN = 'hidden'
    STATUS_DELETED = 'deleted'
    STATUS_CHOICES = [
        (STATUS_VISIBLE, 'Visible'),
        (STATUS_HIDDEN, 'Hidden'),
        (STATUS_DELETED, 'Deleted'),
    ]

    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    post_type = models.CharField(max_length=16, choices=TYPE_CHOICES, db_index=True)
    text = models.TextField(blank=True, default='')
    status = models.CharField(max_length=16, default=STATUS_VISIBLE, choices=STATUS_CHOICES, db_index=True)
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_post'
        indexes = [models.Index(fields=['app_id', 'post_type', 'status', 'created_at'])]


class PostMedia(models.Model):
    MEDIA_IMAGE = 'image'
    MEDIA_VIDEO = 'video'
    MEDIA_CHOICES = [
        (MEDIA_IMAGE, 'Image'),
        (MEDIA_VIDEO, 'Video'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=16, choices=MEDIA_CHOICES, default=MEDIA_IMAGE)
    url = models.CharField(max_length=512)
    cover_url = models.CharField(max_length=512, blank=True, default='')
    duration_ms = models.IntegerField(default=0)
    sort = models.IntegerField(default=0)

    class Meta:
        db_table = 't_post_media'
        ordering = ['sort', 'id']


class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    text = models.CharField(max_length=1000)
    status = models.CharField(max_length=16, default='visible')  # visible|deleted
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_post_comment'
        ordering = ['id']


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_post_like'
        unique_together = ('post', 'user')


class PasswordResetToken(models.Model):
    """Email password-reset codes (hashed)."""
    email = models.EmailField(db_index=True)
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_password_reset_token'
        indexes = [models.Index(fields=['email', 'app_id', 'expires_at'])]


class UserNotificationPref(models.Model):
    """Per-user push preference switches (like / match / message / marketing)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notif_pref')
    likes = models.BooleanField(default=True)
    matches = models.BooleanField(default=True)
    messages = models.BooleanField(default=True)
    marketing = models.BooleanField(default=True)
    silent_recall = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 't_user_notif_pref'


class VerifyInquiry(models.Model):
    """Persona (or mock) identity verification inquiry lifecycle."""
    STATUS_CREATED = 'created'
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_CREATED, 'Created'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DECLINED, 'Declined'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verify_inquiries')
    app_id = models.CharField(max_length=64, default='spark_main', db_index=True)
    provider = models.CharField(max_length=32, default='persona')
    inquiry_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=32, default=STATUS_CREATED, choices=STATUS_CHOICES)
    raw = models.JSONField(default=dict, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_verify_inquiry'
        indexes = [models.Index(fields=['user', 'status'])]


class OpsBanner(models.Model):
    """Ops-managed home/discover banners per app."""
    PLACEMENT_DISCOVER_HOME = 'discover_home'
    PLACEMENT_CHOICES = [
        (PLACEMENT_DISCOVER_HOME, 'Discover Home'),
    ]
    app_id = models.CharField(max_length=64, db_index=True)
    placement = models.CharField(max_length=32, default=PLACEMENT_DISCOVER_HOME, choices=PLACEMENT_CHOICES)
    title = models.CharField(max_length=128)
    subtitle = models.CharField(max_length=256, blank=True, default='')
    image_url = models.URLField(blank=True, default='')
    deep_link = models.CharField(max_length=512, blank=True, default='')
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True)
    sort = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_ops_banner'
        indexes = [models.Index(fields=['app_id', 'placement', 'enabled', 'sort'])]


class QaTemplate(models.Model):
    """Operable Match QA question templates; falls back to qa_templates.py when empty."""
    app_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    locale = models.CharField(max_length=16, default='zh', db_index=True)
    text = models.CharField(max_length=500)
    tags = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    sort = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 't_qa_template'
        indexes = [models.Index(fields=['locale', 'enabled', 'sort'])]

