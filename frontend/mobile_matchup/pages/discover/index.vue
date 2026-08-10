<template>
	<view class="discover-page">
		<view class="top-bar">
			<view class="logo-wrap">
				<view class="heart-mark" />
				<text class="logo">{{ $t('brand.name') }}</text>
			</view>
			<view class="top-actions">
				<view class="quota-col" v-if="feedLeft !== null || dailyLeft !== null">
					<text class="likes-left" v-if="feedLeft !== null">推荐 {{ feedLeft }}/{{ feedCap || 21 }}</text>
					<text class="likes-left sub" v-if="dailyLeft !== null">喜欢 {{ dailyLeft }}</text>
					<text class="likes-left sub" v-if="vipBonusText">{{ vipBonusText }}</text>
				</view>
				<view class="icon-btn boost-ico" @click="doBoost">
					<text class="boost-glyph">⚡</text>
					<view class="dock-badge top" v-if="inv.boost > 0"><text>{{ inv.boost > 9 ? '9+' : inv.boost }}</text></view>
				</view>
				<view class="icon-btn" @click="openPassport"><view class="ico pin" /></view>
				<view class="icon-btn" @click="openFilter"><view class="ico sliders" /></view>
			</view>
		</view>

		<view class="mode-tabs">
			<view class="mode-tab" :class="{ on: feedMode === 'recommend' }" @click="setFeedMode('recommend')"><text>推荐</text></view>
			<view class="mode-tab" :class="{ on: feedMode === 'explore' }" @click="setFeedMode('explore')"><text>探索</text></view>
		</view>

		<HomeBanner
			v-if="feedMode === 'recommend'"
			:items="opsBanners"
			@action="onBannerAction"
		/>

		<view class="boost-banner" v-if="boostActive && feedMode === 'recommend'">
			<text>曝光加速中，更多人会看到你</text>
		</view>
		<view class="boost-banner passport" v-if="passportCity && feedMode === 'recommend'">
			<text>正在浏览 {{ passportCity }}</text>
		</view>

		<!-- 探索：浏览网格（不消耗每日 21 推荐额度） -->
		<scroll-view v-if="feedMode === 'explore'" scroll-y class="explore-scroll" @scrolltolower="maybePrefetch">
			<text class="explore-title">探索附近</text>
			<text class="explore-sub">随便看看 · 不占用今日推荐名额</text>
			<view class="explore-filters">
				<view class="ef" :class="{ on: exploreSort === 'near' }" @click="exploreSort = 'near'"><text>附近</text></view>
				<view class="ef" :class="{ on: exploreSort === 'new' }" @click="exploreSort = 'new'"><text>最新</text></view>
				<view class="ef" :class="{ on: exploreSort === 'online' }" @click="exploreSort = 'online'"><text>在线</text></view>
			</view>
			<view class="explore-grid">
				<view
					v-for="(item, idx) in exploreList"
					:key="item.id"
					class="ex-card"
					:class="{ tall: idx % 5 === 0 || idx % 5 === 3 }"
					@click="openExplore(item)"
				>
					<image class="ex-img" :src="pickPhoto(item)" mode="aspectFill" />
					<view class="ex-fade" />
					<view class="ex-online" v-if="item.is_online" />
					<view class="ex-verified" v-if="item.is_verified"><text>✓</text></view>
					<view class="ex-meta">
						<text class="ex-name">{{ item.nickname }}{{ item.age ? `, ${item.age}` : '' }}</text>
						<text class="ex-city" v-if="item.city">{{ item.city }}</text>
					</view>
					<view class="ex-like" @click.stop="likeExplore(item)"><text>♥</text></view>
				</view>
			</view>
			<view v-if="loading" class="empty explore-empty"><text class="empty-title">加载中…</text></view>
			<view v-else-if="!exploreList.length" class="empty explore-empty">
				<text class="empty-title">探索暂无更多</text>
				<view class="reload" @click="loadFeed(true)"><text>刷新</text></view>
			</view>
		</scroll-view>

		<template v-else>
		<view class="card-stage" v-if="current">
			<view class="profile-card peek" v-if="nextCard">
				<image class="card-photo" :src="peekPhoto" mode="aspectFill" />
			</view>

			<view
				class="profile-card front"
				:class="{ flying: flying }"
				:style="cardStyle"
				@touchstart="onTouchStart"
				@touchmove="onTouchMove"
				@touchend="onTouchEnd"
				@mousedown="onMouseDown"
			>
				<image class="card-photo" :src="currentPhoto" mode="aspectFill" />
				<view class="fade" />
				<view class="tap-left" @click.stop="prevPhoto" />
				<view class="tap-right" @click.stop="nextPhoto" />
				<view class="stamp like-stamp" :style="{ opacity: likeOpacity }"><text>喜欢</text></view>
				<view class="stamp nope-stamp" :style="{ opacity: nopeOpacity }"><text>跳过</text></view>
				<view class="stamp super-stamp" :style="{ opacity: superOpacity }"><text>心动</text></view>
				<view class="photo-progress" v-if="photos.length > 1">
					<view v-for="(p, i) in photos" :key="i" class="prog-seg" :class="{ on: i === photoIndex }" />
				</view>
				<view class="card-info" @click="openDetail">
					<view class="name-row">
						<text class="name">{{ current.nickname }}</text>
						<text class="age">{{ current.age }}</text>
						<view v-if="current.is_verified" class="verified"><text class="v-star">✓</text></view>
						<view v-if="current.is_online" class="online-dot" />
					</view>
					<view class="pill-row">
						<view class="pill" v-if="infoPills[0]"><text>{{ infoPills[0] }}</text></view>
						<view class="pill" v-if="infoPills[1]"><text>{{ infoPills[1] }}</text></view>
						<view class="pill" v-if="infoPills[2]"><text>{{ infoPills[2] }}</text></view>
					</view>
				</view>
			</view>
		</view>
		<view v-else-if="loading" class="empty">
			<text class="empty-title">正在为你寻找附近的人…</text>
		</view>
		<view v-else class="empty">
			<text class="empty-title">{{ emptyTitle }}</text>
			<text class="empty-sub" v-if="reviewMode">应用审核期间推荐为空</text>
			<text class="empty-sub" v-else-if="feedLeft === 0">明天再来继续遇见新的人吧</text>
			<view class="empty-actions" v-if="!reviewMode && feedLeft === 0">
				<view class="reload explore-cta" @click="setFeedMode('explore')"><text>去探索</text></view>
				<view class="reload vip-cta" @click="openFeedVip"><text>会员加量</text></view>
			</view>
			<view class="reload" v-else-if="!reviewMode && feedLeft !== 0" @click="loadFeed(true)"><text>刷新</text></view>
		</view>

		<view class="action-dock" v-if="current">
			<view class="dock-btn nope" @click="flyOut('pass')">
				<text>×</text>
				<text class="dock-label">跳过</text>
			</view>
			<view class="dock-btn super" @click="flyOut('super_like')">
				<text>★</text>
				<text class="dock-label">心动</text>
				<view class="dock-badge" v-if="inv.super_like > 0"><text>{{ inv.super_like > 9 ? '9+' : inv.super_like }}</text></view>
			</view>
			<view class="dock-btn like" @click="flyOut('like')">
				<text>♥</text>
				<text class="dock-label light">喜欢</text>
			</view>
		</view>
		</template>

		<VipSheet v-if="showVip" v-model:show="showVip" :reason="vipReason" @purchased="onPurchased" />
		<FilterSheet v-model:show="showFilter" @saved="reloadFeed" />
		<PassportSheet v-model:show="showPassport" @saved="reloadFeed" />
		<MatchModal
			v-if="showMatch"
			v-model:show="showMatch"
			:user="matchedUser"
			:match-id="matchMeta.matchId"
			:conversation-id="matchedConversationId"
			:i-am-opener="matchMeta.iAmOpener"
			:expire-at="matchMeta.expireAt"
			:messaging-mode="matchMeta.messagingMode"
			@chat="goChat"
		/>
		<SparkTabBar :current="0" />
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { onShow } from '@dcloudio/uni-app'
import { apiFeed, apiSwipe, apiRewind } from '@/api/recommend.js'
import { apiBoost, apiEntitlements } from '@/api/vip.js'
import { apiHeartbeat } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { PACKAGE_NAME } from '@/config/config.js'
import { superLikeLabel, boostLabel, vipFeedBonusLabel, discoverFeedMeta } from '@/utils/productProfile.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import FilterSheet from '@/components/FilterSheet/FilterSheet.vue'
import PassportSheet from '@/components/PassportSheet/PassportSheet.vue'
import MatchModal from '@/components/MatchModal/MatchModal.vue'
import HomeBanner from '@/components/HomeBanner/HomeBanner.vue'

const list = ref([])
const photoIndex = ref(0)
const showVip = ref(false)
const showFilter = ref(false)
const showPassport = ref(false)
const showMatch = ref(false)
const vipReason = ref('')
const matchedUser = ref(null)
const matchedConversationId = ref(null)
const matchMeta = ref({ matchId: null, iAmOpener: null, expireAt: '', messagingMode: '' })
const reviewMode = ref(false)
const boostActive = ref(false)
const passportCity = ref('')
const dailyLeft = ref(null)
const feedLeft = ref(null)
const feedCap = ref(null)
const feedMode = ref('recommend')
const exploreSort = ref('near')
const loading = ref(false)
const inv = ref({ super_like: 0, boost: 0, rewind: 0 })
const opsBanners = ref([])
const vipTier = ref((uni.getStorageSync('userInfo') || {}).vip_tier || 'none')
let feedLock = false
let swipeBusy = false
let lastExploreLoadAt = 0
const EXPLORE_COOLDOWN_MS = 4000
const FEED_SOFT_CAP = 60
const FEED_LOW_WATER = 4

const vipBonusText = computed(() => vipFeedBonusLabel(vipTier.value))

const emptyTitle = computed(() => {
	if (reviewMode.value) return '审核模式'
	if (feedLeft.value === 0) return `今日 ${feedCap.value || 21} 人已看完`
	return feedMode.value === 'explore' ? '探索暂无更多' : '暂时没有更多推荐'
})

const exploreList = computed(() => {
	const arr = list.value.slice()
	if (exploreSort.value === 'online') {
		arr.sort((a, b) => Number(!!b.is_online) - Number(!!a.is_online))
	} else if (exploreSort.value === 'new') {
		arr.sort((a, b) => Number(b.id || 0) - Number(a.id || 0))
	}
	return arr
})

const dx = ref(0)
const dy = ref(0)
const dragging = ref(false)
const flying = ref(false)
let startX = 0
let startY = 0
let moved = false

const current = computed(() => list.value[0] || null)
const nextCard = computed(() => list.value[1] || null)
const photos = computed(() => (current.value && current.value.photos) || [])
const currentPhoto = computed(() => {
	if (!photos.value.length) return current.value?.avatar_url || ''
	return photos.value[Math.min(photoIndex.value, photos.value.length - 1)].url
})
const peekPhoto = computed(() => {
	const n = nextCard.value
	if (!n) return ''
	if (n.photos && n.photos.length) return n.photos[0].url
	return n.avatar_url || ''
})

const cardStyle = computed(() => {
	const rot = dx.value / 28
	return {
		transform: `translate(${dx.value}px, ${dy.value}px) rotate(${rot}deg)`,
		transition: dragging.value ? 'none' : 'transform 0.25s ease'
	}
})
const likeOpacity = computed(() => Math.min(1, Math.max(0, dx.value / 120)))
const nopeOpacity = computed(() => Math.min(1, Math.max(0, -dx.value / 120)))
const superOpacity = computed(() => {
	if (flying.value && dy.value < -80) return 1
	return Math.min(1, Math.max(0, -dy.value / 140))
})

const INFO_TYPES = ['basic', 'bio', 'looking', 'interest', 'lifestyle']
const infoPills = computed(() => {
	const c = current.value
	if (!c) return []
	const t = INFO_TYPES[Math.min(photoIndex.value, INFO_TYPES.length - 1)]
	let pills = []
	if (t === 'basic') {
		pills = [c.job, c.city ? `📍 ${c.city}` : '', c.is_traveling ? '✈ 旅行中' : '']
	} else if (t === 'bio') {
		pills = [c.bio ? c.bio.slice(0, 28) : '', c.city ? `📍 ${c.city}` : '', '']
	} else if (t === 'looking') {
		pills = [c.looking_for, c.relationship, '']
	} else if (t === 'interest') {
		const ints = c.interests || []
		pills = [ints[0], ints[1], ints[2]]
	} else {
		pills = [c.mbti, c.zodiac, c.relationship]
	}
	return pills.filter(Boolean)
})

function onTouchStart(e) {
	if (flying.value) return
	const t = e.touches[0]
	startX = t.clientX
	startY = t.clientY
	dragging.value = true
	moved = false
}

function onTouchMove(e) {
	if (!dragging.value || flying.value) return
	const t = e.touches[0]
	dx.value = t.clientX - startX
	dy.value = t.clientY - startY
	if (Math.abs(dx.value) > 8 || Math.abs(dy.value) > 8) moved = true
}

function onTouchEnd() {
	if (!dragging.value || flying.value) return
	dragging.value = false
	if (!moved) {
		dx.value = 0
		dy.value = 0
		return
	}
	if (dy.value < -120 && Math.abs(dy.value) > Math.abs(dx.value)) {
		flyOut('super_like')
	} else if (dx.value > 110) {
		flyOut('like')
	} else if (dx.value < -110) {
		flyOut('pass')
	} else {
		dx.value = 0
		dy.value = 0
	}
}

// H5 / Chrome desktop: mouse drag fallback (device toolbar or desktop window)
function onMouseDown(e) {
	if (flying.value) return
	startX = e.clientX
	startY = e.clientY
	dragging.value = true
	moved = false
	if (typeof document === 'undefined') return
	const onMove = (ev) => {
		if (!dragging.value || flying.value) return
		dx.value = ev.clientX - startX
		dy.value = ev.clientY - startY
		if (Math.abs(dx.value) > 8 || Math.abs(dy.value) > 8) moved = true
	}
	const onUp = () => {
		document.removeEventListener('mousemove', onMove)
		document.removeEventListener('mouseup', onUp)
		onTouchEnd()
	}
	document.addEventListener('mousemove', onMove)
	document.addEventListener('mouseup', onUp)
}

function flyOut(action) {
	if (flying.value || swipeBusy || !current.value) return
	const btnMap = { like: 'swipe_like', pass: 'swipe_pass', super_like: 'swipe_super' }
	if (btnMap[action]) trackClick(btnMap[action])
	flying.value = true
	dx.value = action === 'like' ? 480 : action === 'pass' ? -480 : 0
	dy.value = action === 'super_like' ? -480 : (action === 'like' || action === 'pass' ? dy.value : 0)
	setTimeout(async () => {
		await doSwipe(action)
		dx.value = 0
		dy.value = 0
		flying.value = false
	}, 220)
}

function prevPhoto() {
	if (moved || flying.value) return
	if (!photos.value.length || photoIndex.value <= 0) {
		openDetail()
		return
	}
	photoIndex.value -= 1
}

function nextPhoto() {
	if (moved || flying.value) return
	if (!photos.value.length || photoIndex.value >= photos.value.length - 1) {
		openDetail()
		return
	}
	photoIndex.value += 1
}

async function loadFeed(reset = true) {
	const token = uni.getStorageSync('token')
	if (!token) {
		uni.reLaunch({ url: '/pages/auth/welcome' })
		return
	}
	if (flying.value || swipeBusy || feedLock) return
	if (feedMode.value === 'explore') {
		const now = Date.now()
		if (lastExploreLoadAt && now - lastExploreLoadAt < EXPLORE_COOLDOWN_MS) {
			return
		}
		lastExploreLoadAt = now
	}
	feedLock = true
	if (reset && !list.value.length) loading.value = true
	try {
		const sys = uni.getSystemInfoSync()
		const platform = sys.uniPlatform === 'app' || sys.uniPlatform === 'app-plus'
			? (sys.platform === 'ios' ? 'ios' : 'android')
			: 'h5'
		const res = await apiFeed({
			limit: 20,
			platform,
			package_name: PACKAGE_NAME,
			app_version: '1.0.0',
			mode: feedMode.value,
		})
		const data = res.results || {}
		const incoming = data.list || []
		const slim = (u, keepAll) => {
			if (!u || !Array.isArray(u.photos) || u.photos.length <= 1) return u
			if (keepAll) return u
			return { ...u, photos: u.photos.slice(0, 1), _photos_truncated: true }
		}
		if (reset) {
			list.value = incoming.map((u, i) => slim(u, i === 0))
			photoIndex.value = 0
		} else {
			const seen = {}
			list.value.forEach((u) => { if (u && u.id != null) seen[u.id] = true })
			const merged = list.value.slice()
			incoming.forEach((u) => {
				if (!u || u.id == null || seen[u.id]) return
				if (merged.length >= FEED_SOFT_CAP) return
				seen[u.id] = true
				merged.push(slim(u, false))
			})
			list.value = merged
		}
		reviewMode.value = !!data.review_mode
		boostActive.value = !!data.boost_active
		passportCity.value = data.passport_city || ''
		dailyLeft.value = data.daily_like_left
		feedLeft.value = data.daily_feed_left == null ? null : data.daily_feed_left
		feedCap.value = data.daily_feed_cap == null ? null : data.daily_feed_cap
		if (data.vip_tier) vipTier.value = data.vip_tier
		const hooks = data.banners || data.ops_banners || data.official || data.hooks || []
		const officialCards = (incoming || []).filter((c) => c && (c.source === 'official' || c.is_official || c.ops))
		opsBanners.value = Array.isArray(hooks) && hooks.length
			? hooks
			: officialCards.map((c) => ({
				title: c.banner_title || c.nickname || '官方推荐',
				subtitle: c.banner_subtitle || c.bio || '',
				url: c.banner_url || '',
				ops: true,
				raw: c,
			}))
		const boot = uni.getStorageSync('bootstrap') || {}
		if (boot.review_mode) reviewMode.value = true
		if (feedCap.value == null) {
			const meta = discoverFeedMeta()
			if (meta.daily_feed_cap != null) feedCap.value = meta.daily_feed_cap
		}
		loading.value = false
		feedLock = false
	} catch (e) {
		loading.value = false
		feedLock = false
		if (!list.value.length) {
		uni.showToast({ title: '加载失败', icon: 'none' })
	}
}
}

function setFeedMode(mode) {
	if (feedMode.value === mode) return
	feedMode.value = mode
	loadFeed(true)
}

function maybePrefetch() {
	if (list.value.length > 0 && list.value.length <= FEED_LOW_WATER) {
		loadFeed(false)
	}
}

function handleVipError(e) {
	const msg = (e && e.message) || ''
	const data = (e && e.results) || {}
	if (data.need_vip || data.need_shop || /need_|daily_like|limit/.test(msg)) {
		vipReason.value = msg || 'need_vip'
		showVip.value = true
		return true
	}
	return false
}

async function doSwipe(action) {
	if (!current.value || swipeBusy) return
	swipeBusy = true
	const target = current.value
	try {
		const res = await apiSwipe({ target_id: target.id, action, feed_mode: feedMode.value })
		const data = res.results || {}
		track('swipe', { action, target_id: target.id, matched: !!data.matched, feed_mode: feedMode.value })
		if (data.matched && data.match) {
			matchedUser.value = data.match.user
			matchedConversationId.value = data.match.conversation_id || null
			matchMeta.value = {
				matchId: data.match.match_id,
				iAmOpener: data.match.i_am_opener,
				expireAt: data.match.expire_at,
				messagingMode: data.match.messaging_mode,
			}
			showMatch.value = true
			track('match', { target_id: target.id, conversation_id: matchedConversationId.value })
		}
		list.value = list.value.slice(1)
		photoIndex.value = 0
		if (typeof data.daily_feed_left === 'number') feedLeft.value = data.daily_feed_left
		else if (feedMode.value === 'recommend' && typeof feedLeft.value === 'number' && feedLeft.value > 0) {
			feedLeft.value -= 1
		}
		if (typeof data.daily_like_left === 'number') dailyLeft.value = data.daily_like_left
		if (!list.value.length) loadFeed(true)
		else maybePrefetch()
	} catch (e) {
		dx.value = 0
		dy.value = 0
		flying.value = false
		if (e && e.message === 'daily_feed_limit') {
			feedLeft.value = 0
			list.value = []
			vipReason.value = 'need_feed'
			showVip.value = true
			uni.showToast({ title: '今日推荐已用完', icon: 'none' })
			return
		}
		if (!handleVipError(e)) {
			uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
		}
	} finally {
		swipeBusy = false
	}
}

async function doRewind() {
	trackClick('swipe_rewind')
	try {
		await apiRewind()
		await loadFeed(true)
		uni.showToast({ title: '已撤销', icon: 'none' })
	} catch (e) {
		if (!handleVipError(e)) {
			vipReason.value = 'need_plus'
			showVip.value = true
		}
	}
}

async function doBoost() {
	trackClick('swipe_boost')
	try {
		await apiBoost()
		boostActive.value = true
		uni.showToast({ title: '曝光已开启', icon: 'none' })
	} catch (e) {
		handleVipError(e) || ((vipReason.value = 'need_boost'), (showVip.value = true))
	}
}

function openDetail() {
	if (!current.value || flying.value) return
	const payload = encodeURIComponent(JSON.stringify(current.value))
	uni.navigateTo({
		url: `/pagesA/profile/detail?user_id=${current.value.id}&funnel=${payload}&photo=${photoIndex.value}`
	})
}

function pickPhoto(item) {
	if (!item) return ''
	if (item.photos && item.photos.length) return item.photos[0].url
	return item.avatar_url || ''
}

function openExplore(item) {
	if (!item) return
	const payload = encodeURIComponent(JSON.stringify(item))
	uni.navigateTo({
		url: `/pagesA/profile/detail?user_id=${item.id}&funnel=${payload}`
	})
}

async function likeExplore(item) {
	if (!item) return
	try {
		const res = await apiSwipe({ target_id: item.id, action: 'like', feed_mode: 'explore' })
		const data = res.results || {}
		list.value = list.value.filter((x) => x.id !== item.id)
		if (data.matched && data.match) {
			matchedUser.value = data.match.user
			matchedConversationId.value = data.match.conversation_id || null
			matchMeta.value = {
				matchId: data.match.match_id,
				iAmOpener: data.match.i_am_opener,
				expireAt: data.match.expire_at,
				messagingMode: data.match.messaging_mode,
			}
			showMatch.value = true
		} else {
			uni.showToast({ title: '已喜欢', icon: 'none' })
		}
		if (typeof data.daily_like_left === 'number') dailyLeft.value = data.daily_like_left
	} catch (e) {
		if (!handleVipError(e)) {
			uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
		}
	}
}

function goChat(payload) {
	showMatch.value = false
	const id = matchedConversationId.value
	const focusQa = !!(payload && (payload.focusAsk || payload.focus === 'qa'))
		|| !!(matchMeta.value && matchMeta.value.iAmOpener && matchMeta.value.messagingMode === 'qa_gate')
	if (id) {
		const q = focusQa ? '&focus=qa' : ''
		uni.navigateTo({ url: `/pagesA/chat/room?id=${id}${q}` })
		return
	}
	uni.switchTab({ url: '/pages/chat/index' })
}

function openFeedVip() {
	trackClick('open_vip')
	vipReason.value = 'need_feed'
	showVip.value = true
}

function openFilter() {
	trackClick('filter_open')
	showFilter.value = true
}

function openPassport() {
	trackClick('passport_open')
	showPassport.value = true
}

function onBannerAction(b) {
	const deep = (b && (b.deep_link || b.path || (b.raw && (b.raw.deep_link || b.raw.path)))) || ''
	const url = (b && b.url) || ''
	const path = deep || (url.startsWith('/pages') ? url : '')
	if (path && path.startsWith('/pages')) {
		const clean = path.split('?')[0]
		const tabs = ['/pages/discover/index', '/pages/likes/index', '/pages/chat/index', '/pages/me/index']
		if (tabs.includes(clean)) {
			try {
				const pages = getCurrentPages()
				const cur = pages && pages[pages.length - 1]
				const route = cur && cur.route ? `/${cur.route}` : ''
				if (route === clean) return
			} catch (e) {}
			uni.switchTab({ url: clean, fail: () => {} })
			return
		}
		uni.navigateTo({ url: path.startsWith('/') ? path : '/' + path })
		return
	}
	if (b && b.raw && b.raw.id) {
		uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${b.raw.id}` })
	}
}

async function loadInventory() {
	try {
		const res = await apiEntitlements()
		const s = (res.results && res.results.spendable) || {}
		inv.value = {
			super_like: Number(s.super_like || 0),
			boost: Number(s.boost || 0),
			rewind: Number(s.rewind || 0),
		}
	} catch (e) {}
}

function onPurchased() {
	showVip.value = false
	loadFeed(true)
	loadInventory()
}

function reloadFeed() {
	loadFeed(true)
}

onMounted(() => {
	loadFeed(true)
	loadInventory()
	apiHeartbeat().catch(() => {})
	import('@/utils/maps.js').then((m) => m.reportLocation({ updateCity: false })).catch(() => {})
})
onShow(() => {
	apiHeartbeat().catch(() => {})
	refreshTabBadges()
	loadInventory()
})
</script>

<style scoped>
.discover-page {
	min-height: 100vh;
	background: #FFF7FA;
	padding: 0;
	box-sizing: border-box;
	position: relative;
}
.top-bar {
	position: absolute;
	left: 0; right: 0;
	top: 0;
	z-index: 20;
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: space-between;
	padding: calc(env(safe-area-inset-top) + 8rpx) 28rpx 8rpx;
	pointer-events: none;
}
.top-bar .logo-wrap,
.top-bar .top-actions,
.top-bar .icon-btn,
.top-bar .likes-left { pointer-events: auto; }
.logo-wrap {
	display: flex;
	flex-direction: row;
	align-items: center;
}
.heart-mark {
	width: 36rpx; height: 32rpx; margin-right: 10rpx;
	background: #FF6B9A;
	border-radius: 18rpx 18rpx 4rpx 4rpx;
	transform: rotate(-45deg);
}
.flame-unused {
	width: 36rpx; height: 44rpx; margin-right: 10rpx;
	background: linear-gradient(180deg, #FF6B9A 0%, #FF8FB3 100%);
	border-radius: 40% 40% 48% 48%;
	clip-path: polygon(50% 0%, 88% 42%, 70% 100%, 30% 100%, 12% 42%);
}
.logo {
	font-size: 40rpx;
	font-weight: 800;
	letter-spacing: 2rpx;
	color: #FF6B9A;
}
.top-actions { display: flex; flex-direction: row; align-items: center; }
.likes-left {
	color: #FF6B9A; font-size: 24rpx; font-weight: 700; margin-right: 8rpx;
	min-width: 40rpx; text-align: right;
}
.vip-bonus { color: #C9A000; font-size: 20rpx; font-weight: 600; }
.mode-tabs {
	position: absolute;
	left: 0; right: 0;
	top: calc(env(safe-area-inset-top) + 72rpx);
	z-index: 22;
	display: flex;
	flex-direction: row;
	justify-content: center;
	
	padding: 0 24rpx 12rpx;
	pointer-events: none;
}
.mode-tabs .mode-tab + .mode-tab { margin-left: 12rpx; }
.mode-tabs .mode-tab { pointer-events: auto; }
.mode-tab {
	padding: 10rpx 28rpx;
	border-radius: 999rpx;
	background: rgba(255,107,154,0.1);
}
.mode-tab text { color: #888; font-size: 24rpx; }
.mode-tab.on { background: #FF6B9A; }
.mode-tab.on text { color: #fff; font-weight: 700; }
.icon-btn {
	width: 64rpx; height: 64rpx; border-radius: 50%;
	background: transparent; margin-left: 8rpx;
	display: flex; align-items: center; justify-content: center;
}
.ico.pin {
	width: 22rpx; height: 22rpx; border: 2rpx solid #ADAFB6;
	border-radius: 50% 50% 50% 0; transform: rotate(-45deg);
}
.ico.sliders {
	width: 30rpx; height: 22rpx;
	background:
		linear-gradient(#ADAFB6,#ADAFB6) 0 4rpx/100% 3rpx no-repeat,
		linear-gradient(#ADAFB6,#ADAFB6) 0 18rpx/100% 3rpx no-repeat,
		radial-gradient(circle,#ADAFB6 45%,transparent 46%) 8rpx 0/12rpx 12rpx no-repeat,
		radial-gradient(circle,#ADAFB6 45%,transparent 46%) 18rpx 12rpx/12rpx 12rpx no-repeat;
}
.boost-banner {
	position: absolute;
	left: 24rpx; right: 24rpx;
	top: calc(env(safe-area-inset-top) + 128rpx);
	z-index: 21;
	background: rgba(255,107,154,0.12);
	border: 1px solid rgba(255,107,154,0.35);
	border-radius: 16rpx;
	padding: 14rpx 18rpx;
}
.boost-banner.passport {
	background: rgba(110,168,254,0.14);
	border-color: rgba(110,168,254,0.4);
}
.boost-banner text { color:#FF6B9A; font-size:24rpx; }
.boost-banner.passport text { color:#FF6B9A; }
.card-stage {
	position: relative;
	height: 100vh;
	padding: calc(env(safe-area-inset-top) + 120rpx) 20rpx calc(200rpx + env(safe-area-inset-bottom));
	box-sizing: border-box;
}
.profile-card {
	position: absolute;
	left: 20rpx; right: 20rpx;
	top: calc(env(safe-area-inset-top) + 120rpx);
	bottom: calc(200rpx + env(safe-area-inset-bottom));
	border-radius: 24rpx;
	overflow: hidden;
	background: #FFFFFF;
	box-shadow: 0 12rpx 40rpx rgba(255,107,154,0.18);
	touch-action: none;
	user-select: none;
	cursor: grab;
}
.profile-card.front:active { cursor: grabbing; }
.profile-card.peek {
	transform: scale(0.985);
	opacity: 0.55;
}
.profile-card.front { z-index: 2; }
.card-photo { width: 100%; height: 100%; }
.fade {
	position: absolute; left: 0; right: 0; bottom: 0; height: 42%;
	background: linear-gradient(to top, rgba(0,0,0,0.88), transparent);
	z-index: 1;
	pointer-events: none;
}
.tap-left, .tap-right {
	position: absolute; top: 0; bottom: 200rpx; width: 38%; z-index: 3;
}
.tap-left { left: 0; }
.tap-right { right: 0; }
.stamp {
	position: absolute; top: 120rpx; z-index: 5;
	border: 6rpx solid; border-radius: 16rpx; padding: 10rpx 18rpx;
	transform: rotate(-18deg);
}
.stamp text { font-size: 36rpx; font-weight: 900; letter-spacing: 4rpx; }
.like-stamp { left: 36rpx; border-color: #2dd36f; }
.like-stamp text { color: #2dd36f; }
.nope-stamp { right: 36rpx; border-color: #fd5068; transform: rotate(18deg); }
.nope-stamp text { color: #fd5068; }
.super-stamp {
	left: 50%; top: 160rpx; transform: translateX(-50%) rotate(-8deg);
	border-color: #FFC629;
}
.super-stamp text { color: #E6A800; font-size: 36rpx; }
.photo-progress {
	position: absolute; left: 16rpx; right: 16rpx; top: 12rpx;
	display: flex; flex-direction: row; z-index: 4;
}
.prog-seg {
	flex: 1; height: 6rpx; border-radius: 4rpx;
	background: rgba(255,255,255,0.35); margin-right: 6rpx;
}
.prog-seg:last-child { margin-right: 0; }
.prog-seg.on { background: #fff; }
.card-info {
	position: absolute; left: 28rpx; bottom: 36rpx; right: 28rpx; z-index: 4;
}
.name-row {
	display: flex; flex-direction: row; align-items: flex-end; margin-bottom: 14rpx;
}
.name { font-size: 52rpx; color: #fff; font-weight: 700; margin-right: 12rpx; }
.age { font-size: 42rpx; color: #fff; font-weight: 500; margin-right: 12rpx; }
.verified {
	width: 34rpx; height: 34rpx; border-radius: 50%; background: #1DA1F2;
	display: flex; align-items: center; justify-content: center; margin-bottom: 8rpx;
}
.v-star { color: #fff; font-size: 20rpx; font-weight: 800; }
.online-dot {
	width: 16rpx; height: 16rpx; border-radius: 50%; background: #22C55E; margin-left: 10rpx; margin-bottom: 12rpx;
}
.pill-row { display: flex; flex-direction: row; flex-wrap: wrap; }
.pill {
	background: rgba(255,255,255,0.16);
	border-radius: 999rpx; padding: 10rpx 18rpx; margin-right: 10rpx; margin-bottom: 8rpx;
}
.pill text { color: #fff; font-size: 22rpx; }
.action-dock {
	position: absolute;
	left: 0; right: 0;
	bottom: calc(120rpx + env(safe-area-inset-bottom));
	z-index: 40;
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: center;
	padding: 0 24rpx;
}
.dock-btn {
	position: relative;
	border-radius: 50%;
	transition: transform 0.12s ease;
	background: #FFFFFF;
	border: 2rpx solid #2A2A30;
	display: flex; align-items: center; justify-content: center;
	margin: 0 10rpx;
	box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.35);
}
.dock-btn:active { transform: scale(0.88); }
.dock-btn text { font-weight: 700; line-height: 1; }
.dock-badge {
	position: absolute; top: -6rpx; right: -6rpx;
	min-width: 32rpx; height: 32rpx; padding: 0 6rpx;
	border-radius: 999rpx; background: #FF6B9A;
	display: flex; align-items: center; justify-content: center;
}
.dock-badge text { color: #fff; font-size: 18rpx; font-weight: 800; }
.dock-btn.rewind { width: 88rpx; height: 88rpx; }
.dock-btn.rewind text { color: #F5C451; font-size: 40rpx; }
.dock-btn.nope {
	width: 120rpx; height: 120rpx; border-color: #FD5068;
	flex-direction: column;
}
.dock-btn.nope text { color: #FD5068; font-size: 56rpx; }
.dock-btn.super {
	width: 96rpx; height: 96rpx; border-color: #FFC629;
	flex-direction: column; margin: 0 28rpx;
	background: #FFF9E6;
}
.dock-btn.super text { color: #E6A800; font-size: 36rpx; }
.dock-btn.like {
	width: 120rpx; height: 120rpx; border-color: #FF6B9A; background:#FF6B9A;
	border: 3rpx solid #fff; box-shadow: 0 8rpx 20rpx rgba(255,107,154,0.35);
	flex-direction: column;
}
.dock-btn.like text { color: #fff; font-size: 48rpx; }
.dock-label {
	display:block; font-size: 18rpx !important; font-weight: 600 !important;
	margin-top: 2rpx; color: inherit;
}
.dock-label.light { color: #fff !important; }
.dock-btn.boost { width: 88rpx; height: 88rpx; border-color: #A855F7; }
.dock-btn.boost text { color: #A855F7; font-size: 36rpx; }
.quota-col { display:flex; flex-direction:column; align-items:flex-end; margin-right: 8rpx; }
.likes-left.sub { font-size: 18rpx; opacity: 0.85; margin-top: 2rpx; }
.icon-btn.boost-ico { position: relative; }
.boost-glyph { color:#A855F7; font-size: 28rpx; }
.dock-badge.top {
	position: absolute; top: -4rpx; right: -4rpx;
	min-width: 28rpx; height: 28rpx; padding: 0 4rpx;
	border-radius: 999rpx; background: #FF6B9A;
	display: flex; align-items: center; justify-content: center;
}
.dock-badge.top text { color:#fff; font-size:16rpx; }
.empty-actions { display:flex; flex-direction:row; justify-content:center; margin-top: 8rpx; }
.empty-actions > view + view { margin-left: 16rpx; }
.reload.vip-cta { background: linear-gradient(90deg, #FF6B9A, #FF8FB3); }
.empty { padding-top: 280rpx; text-align: center; color: #999; }
.empty-title { display:block; color:#333; font-size:34rpx; margin-bottom:12rpx; }
.empty-sub { display:block; color:#888; font-size:24rpx; padding:0 40rpx; margin-bottom:24rpx; }
.reload {
	margin: 24rpx auto 0; width: 240rpx;
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3);
	border-radius: 999rpx; padding: 18rpx;
	text-align: center;
}
.reload text { color: #fff; }
.reload.explore-cta {
	background: #fff;
	border: 1px solid #FF6B9A;
}
.reload.explore-cta text { color: #FF6B9A; font-weight: 700; }
.explore-scroll {
	height: 100vh;
	padding: calc(env(safe-area-inset-top) + 140rpx) 24rpx 160rpx;
	box-sizing: border-box;
}
.explore-title {
	display: block; color: #222; font-size: 36rpx; font-weight: 800; margin: 8rpx 0 4rpx;
}
.explore-sub { display: block; color: #888; font-size: 22rpx; margin-bottom: 16rpx; }
.explore-filters {
	display: flex; flex-direction: row; margin-bottom: 18rpx; 
}
.explore-filters .ef + .ef { margin-left: 10rpx; }
.ef {
	padding: 10rpx 22rpx; border-radius: 999rpx;
	background: #fff; border: 1px solid rgba(255,107,154,0.25);
}
.ef text { color: #666; font-size: 22rpx; }
.ef.on { background: #FF6B9A; border-color: #FF6B9A; }
.ef.on text { color: #fff; font-weight: 700; }
.explore-grid {
	display: flex; flex-direction: row; flex-wrap: wrap;
}
.ex-card {
	width: 48%; margin-right: 4%; margin-bottom: 16rpx;
	height: 380rpx; border-radius: 24rpx; overflow: hidden; position: relative;
	background: #FFE8F0;
}
.ex-card.tall { height: 480rpx; }
.ex-card:nth-child(2n) { margin-right: 0; }
.ex-img { width: 100%; height: 100%; }
.ex-fade {
	position: absolute; left: 0; right: 0; bottom: 0; height: 42%;
	background: linear-gradient(to top, rgba(0,0,0,0.75), transparent);
}
.ex-online {
	position: absolute; left: 14rpx; top: 14rpx; z-index: 3;
	width: 16rpx; height: 16rpx; border-radius: 50%;
	background: #22C55E; border: 3rpx solid #fff;
}
.ex-verified {
	position: absolute; right: 14rpx; top: 14rpx; z-index: 3;
	width: 36rpx; height: 36rpx; border-radius: 50%; background: #FF6B9A;
	display: flex; align-items: center; justify-content: center;
}
.ex-verified text { color: #fff; font-size: 20rpx; font-weight: 800; }
.ex-meta { position: absolute; left: 16rpx; right: 80rpx; bottom: 20rpx; z-index: 2; }
.ex-name { display:block; color: #fff; font-size: 28rpx; font-weight: 700; }
.ex-city { display:block; color: rgba(255,255,255,0.85); font-size: 20rpx; margin-top: 4rpx; }
.ex-like {
	position: absolute; right: 16rpx; bottom: 16rpx; z-index: 3;
	width: 64rpx; height: 64rpx; border-radius: 50%; background: #FF6B9A;
	display: flex; align-items: center; justify-content: center;
	box-shadow: 0 6rpx 16rpx rgba(255,107,154,0.45);
}
.ex-like text { color: #fff; font-size: 32rpx; }
.explore-empty { padding-top: 80rpx; }
</style>
