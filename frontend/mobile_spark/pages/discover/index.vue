<template>
	<view class="discover-page">
		<view class="top-bar">
			<view class="logo-wrap">
				<view class="flame" />
				<text class="logo">{{ APP_NAME_DISPLAY }}</text>
			</view>
			<view class="top-actions">
				<text class="likes-left" v-if="dailyLeft !== null">♥ {{ dailyLeft }}</text>
				<view class="icon-btn" @click="openPassport"><view class="ico pin" /></view>
				<view class="icon-btn" @click="openFilter"><view class="ico sliders" /></view>
			</view>
		</view>

		<view class="mode-tabs">
			<view class="mode-tab" :class="{ on: feedMode === 'recommend' }" @click="setFeedMode('recommend')"><text>For You</text></view>
			<view class="mode-tab" :class="{ on: feedMode === 'top_picks' }" @click="setFeedMode('top_picks')"><text>Top Picks</text></view>
			<view class="mode-tab" :class="{ on: feedMode === 'explore' }" @click="setFeedMode('explore')"><text>Explore</text></view>
		</view>

		<view class="boost-banner" v-if="boostActive && feedMode === 'recommend'" @click="openBoostReport">
			<text>Boost is live{{ boostCountdown ? ` · ${boostCountdown}` : '' }} — tap for report</text>
		</view>
		<view class="boost-banner passport" v-if="passportCity && feedMode === 'recommend'">
			<text>Browsing in {{ passportCity }}</text>
		</view>

		<!-- Top Picks: daily curated grid (Tinder-style) -->
		<scroll-view v-if="feedMode === 'top_picks'" scroll-y class="picks-scroll">
			<view class="picks-head">
				<view>
					<text class="picks-title">Today’s Top Picks</text>
					<text class="picks-sub">{{ picksSubCopy }}{{ topPicksCountdown ? ` · ${topPicksCountdown}` : '' }}</text>
				</view>
				<view class="picks-refresh" @click="refreshTopPicks"><text>↻</text></view>
			</view>
			<view class="picks-grid">
				<view
					v-for="item in list"
					:key="item.id"
					class="pick-card"
					@click="openPick(item)"
				>
					<image class="pick-img" :src="pickPhoto(item)" mode="aspectFill" />
					<view class="pick-fade" />
					<view class="pick-meta">
						<text class="pick-name">{{ item.nickname }}{{ item.age ? `, ${item.age}` : '' }}</text>
						<view class="pick-tags" v-if="item.interests && item.interests.length">
							<text class="pick-tag">{{ item.interests[0] }}</text>
						</view>
					</view>
					<view class="pick-like" @click.stop="likePick(item)"><text>♥</text></view>
				</view>
			</view>
			<view v-if="loading" class="empty picks-empty"><text class="empty-title">Loading Top Picks…</text></view>
			<view v-else-if="!list.length" class="empty picks-empty">
				<text class="empty-title">No Top Picks yet</text>
				<text class="empty-sub">See more curated profiles with Gold · refreshes daily</text>
				<view class="reload gold-cta" @click="openGoldSheet"><text>Get Gold</text></view>
			</view>
		</scroll-view>

		<!-- Explore: browse grid (does not consume daily recommend quota) -->
		<scroll-view v-else-if="feedMode === 'explore'" scroll-y class="explore-scroll" @scrolltolower="maybePrefetch">
			<text class="explore-title">Explore</text>
			<text class="explore-sub">Browse by intent · doesn't use your daily picks</text>
			<view class="explore-filters">
				<view class="ef" :class="{ on: exploreCategory === 'dating' }" @click="setExploreCategory('dating')"><text>Dating</text></view>
				<view class="ef" :class="{ on: exploreCategory === 'bff' }" @click="setExploreCategory('bff')"><text>BFF</text></view>
				<view class="ef" :class="{ on: exploreCategory === 'interests' }" @click="setExploreCategory('interests')"><text>Interests</text></view>
				<view class="ef" :class="{ on: exploreCategory === 'bizz' }" @click="setExploreCategory('bizz')"><text>Bizz</text></view>
			</view>
			<view class="explore-filters secondary">
				<view class="ef" :class="{ on: exploreSort === 'near' }" @click="exploreSort = 'near'"><text>Nearby</text></view>
				<view class="ef" :class="{ on: exploreSort === 'new' }" @click="exploreSort = 'new'"><text>Newest</text></view>
				<view class="ef" :class="{ on: exploreSort === 'online' }" @click="exploreSort = 'online'"><text>Online</text></view>
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
			<view v-if="loading" class="empty explore-empty"><text class="empty-title">Loading…</text></view>
			<view v-else-if="!exploreList.length" class="empty explore-empty">
				<text class="empty-title">Nothing to explore right now</text>
				<view class="reload" @click="loadFeed(true)"><text>Refresh</text></view>
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
				<view class="stamp like-stamp" :style="{ opacity: likeOpacity }"><text>LIKE</text></view>
				<view class="stamp nope-stamp" :style="{ opacity: nopeOpacity }"><text>NOPE</text></view>
				<view class="stamp super-stamp" :style="{ opacity: superOpacity }"><text>SUPER</text></view>
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
			<text class="empty-title">Finding people near you…</text>
		</view>
		<view v-else class="empty">
			<text class="empty-title">{{ reviewMode ? 'Review mode' : "There's no one new around you" }}</text>
			<text class="empty-sub" v-if="reviewMode">Feed is empty while the app is under store review.</text>
			<view class="reload" v-if="!reviewMode" @click="loadFeed(true)"><text>Refresh</text></view>
		</view>

		<view class="action-dock" v-if="current && feedMode === 'recommend'">
			<view class="dock-btn rewind" :class="{ pop: stockPop === 'rewind' }" @click="doRewind">
				<text>↺</text>
				<view class="dock-badge" v-if="inv.rewind > 0"><text>{{ inv.rewind > 9 ? '9+' : inv.rewind }}</text></view>
			</view>
			<view class="dock-btn nope" @click="flyOut('pass')"><text>×</text></view>
			<view class="dock-btn super" :class="{ pop: stockPop === 'super_like' }" @click="openCompliment">
				<text>★</text>
				<view class="dock-badge" v-if="inv.super_like > 0"><text>{{ inv.super_like > 9 ? '9+' : inv.super_like }}</text></view>
			</view>
			<view class="dock-btn like" @click="flyOut('like')"><text>♥</text></view>
			<view class="dock-btn boost" :class="{ pop: stockPop === 'boost' }" @click="doBoost">
				<text>⚡</text>
				<view class="dock-badge" v-if="inv.boost > 0"><text>{{ inv.boost > 9 ? '9+' : inv.boost }}</text></view>
			</view>
		</view>
		</template>

		<VipSheet v-if="showVip" v-model:show="showVip" :reason="vipReason" @purchased="onPurchased" />
		<FilterSheet v-model:show="showFilter" @saved="reloadFeed" />
		<PassportSheet v-model:show="showPassport" @saved="reloadFeed" />
		<ComplimentSheet
			v-if="showCompliment"
			v-model:show="showCompliment"
			:user="current"
			@sent="onComplimentSent"
			@need-shop="onNeedSuperShop"
		/>
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
import { onShow } from '@dcloudio/uni-app'
import { apiFeed, apiSwipe, apiRewind } from '@/api/recommend.js'
import { apiBoost, apiEntitlements } from '@/api/vip.js'
import { apiHeartbeat } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { APP_NAME_DISPLAY, PACKAGE_NAME } from '@/config/config.js'
import { superLikeLabel, boostLabel, isComplimentEnabled } from '@/utils/productProfile.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import FilterSheet from '@/components/FilterSheet/FilterSheet.vue'
import PassportSheet from '@/components/PassportSheet/PassportSheet.vue'
import MatchModal from '@/components/MatchModal/MatchModal.vue'
import ComplimentSheet from '@/components/ComplimentSheet/ComplimentSheet.vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'

const list = ref([])
const photoIndex = ref(0)
const showVip = ref(false)
const showFilter = ref(false)
const showPassport = ref(false)
const showMatch = ref(false)
const showCompliment = ref(false)
const vipReason = ref('')
const matchedUser = ref(null)
const matchedConversationId = ref(null)
const inv = ref({ super_like: 0, boost: 0, rewind: 0 })
const matchMeta = ref({ matchId: null, iAmOpener: null, expireAt: '', messagingMode: '' })
const reviewMode = ref(false)
const boostActive = ref(false)
const boostEndAt = ref('')
const boostCountdown = ref('')
const topPicksRefreshAt = ref('')
const topPicksCountdown = ref('')
const passportCity = ref('')
const dailyLeft = ref(null)
const feedMode = ref('recommend')
const exploreSort = ref('near')
const exploreCategory = ref('dating')
const loading = ref(false)
let countdownTimer = null
const stockPop = ref('')
let stockPopTimer = null
let feedLock = false
let swipeBusy = false
const FEED_SOFT_CAP = 60
const FEED_LOW_WATER = 4

const picksSubCopy = computed(() => {
	if (dailyLeft.value !== null) return `Curated for you · ${dailyLeft.value} likes left today`
	return 'Curated for you · refresh daily'
})

function pulseStock(kind) {
	stockPop.value = kind
	if (stockPopTimer) clearTimeout(stockPopTimer)
	stockPopTimer = setTimeout(() => { stockPop.value = '' }, 420)
}

function refreshTopPicks() {
	loadFeed(true)
	uni.showToast({ title: 'Refreshing Top Picks', icon: 'none' })
}

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

const INFO_TYPES = ['basic', 'bio', 'looking', 'interest', 'prompt', 'lifestyle']
const infoPills = computed(() => {
	const c = current.value
	if (!c) return []
	const t = INFO_TYPES[Math.min(photoIndex.value, INFO_TYPES.length - 1)]
	let pills = []
	if (t === 'basic') {
		const dist = c.distance_km != null ? `${c.distance_km} km away` : (c.city ? `📍 ${c.city}` : '')
		pills = [
			c.priority ? '★ Priority' : '',
			c.job,
			dist,
			c.is_traveling ? '✈ Traveling' : '',
		]
	} else if (t === 'bio') {
		pills = [c.bio ? c.bio.slice(0, 28) : '', c.distance_km != null ? `${c.distance_km} km` : (c.city ? `📍 ${c.city}` : ''), '']
	} else if (t === 'looking') {
		pills = [c.looking_for, c.relationship, c.looking_for_intent || '']
	} else if (t === 'interest') {
		const ints = c.interests || []
		pills = [ints[0], ints[1], ints[2]]
	} else if (t === 'prompt') {
		const life = c.lifestyle || {}
		const list = Array.isArray(life.prompts) ? life.prompts : []
		const pr = list[0] || life.prompt || null
		pills = pr && pr.q ? [`💬 ${pr.q}`, pr.a ? String(pr.a).slice(0, 36) : ''] : []
	} else {
		pills = [c.mbti, c.zodiac, c.pronouns || c.relationship]
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
	if (flying.value || feedLock) return
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
			category: feedMode.value === 'explore' ? exploreCategory.value : undefined,
		})
		const data = res.results || {}
		const incoming = data.list || []
		// F-08: stack cards keep first photo only; current card restores full list on focus via detail
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
		boostEndAt.value = data.boost_end_at || ''
		topPicksRefreshAt.value = data.next_refresh_at || ''
		passportCity.value = data.passport_city || ''
		dailyLeft.value = data.daily_like_left
		tickCountdowns()
		const boot = uni.getStorageSync('bootstrap') || {}
		if (boot.review_mode) reviewMode.value = true
		loading.value = false
		feedLock = false
	} catch (e) {
		loading.value = false
		feedLock = false
		const msg = (e && e.message) || ''
		if (feedMode.value === 'top_picks' && (msg === 'need_gold' || (e && e.results && e.results.need_vip))) {
			openGoldSheet()
		} else if (!list.value.length) {
			uni.showToast({ title: 'Failed to load feed', icon: 'none' })
		}
	}
}

function formatRemain(iso) {
	if (!iso) return ''
	const end = new Date(iso).getTime()
	const ms = end - Date.now()
	if (ms <= 0) return '0:00'
	const m = Math.floor(ms / 60000)
	const s = Math.floor((ms % 60000) / 1000)
	if (m >= 60) {
		const h = Math.floor(m / 60)
		return `${h}h ${m % 60}m`
	}
	return `${m}:${String(s).padStart(2, '0')}`
}

function tickCountdowns() {
	boostCountdown.value = boostActive.value ? formatRemain(boostEndAt.value) : ''
	topPicksCountdown.value = feedMode.value === 'top_picks' ? formatRemain(topPicksRefreshAt.value) : ''
}

function setExploreCategory(cat) {
	exploreCategory.value = cat
	if (feedMode.value === 'explore') loadFeed(true)
}

async function openBoostReport() {
	try {
		const { apiBoostReport } = await import('@/api/vip.js')
		const res = await apiBoostReport()
		const s = (res.results && res.results.session) || {}
		uni.showModal({
			title: 'Boost report',
			content: `Impressions ${s.impressions || 0} · Likes ${s.likes || 0} · Matches ${s.matches || 0}`,
			showCancel: false,
		})
	} catch (e) {
		uni.showToast({ title: 'No boost report yet', icon: 'none' })
	}
}

function setFeedMode(mode) {
	if (feedMode.value === mode) return
	feedMode.value = mode
	loadFeed(true)
}

function pickPhoto(item) {
	if (!item) return ''
	if (item.photos && item.photos.length) return item.photos[0].url
	return item.avatar_url || ''
}

function openPick(item) {
	if (!item) return
	const payload = encodeURIComponent(JSON.stringify(item))
	uni.navigateTo({
		url: `/pagesA/profile/detail?user_id=${item.id}&funnel=${payload}`
	})
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
			uni.showToast({ title: 'Liked', icon: 'none' })
		}
		if (typeof data.daily_like_left === 'number') dailyLeft.value = data.daily_like_left
	} catch (e) {
		if (!handleVipError(e)) {
			uni.showToast({ title: (e && e.message) || 'Like failed', icon: 'none' })
		}
	}
}

function openCompliment() {
	if (!current.value || flying.value) return
	trackClick('swipe_super')
	// Super Like ≠ Compliment — only open ComplimentSheet when product enables it.
	if (!isComplimentEnabled()) {
		flyOut('super_like')
		return
	}
	showCompliment.value = true
}
function onComplimentSent() {
	pulseStock('super_like')
	if (inv.value.super_like > 0) inv.value.super_like -= 1
	list.value = list.value.slice(1)
	photoIndex.value = 0
	if (list.value.length < FEED_LOW_WATER) loadFeed(false)
}
function onNeedSuperShop() {
	vipReason.value = 'need_super_like'
	showVip.value = true
}

function openGoldSheet() {
	vipReason.value = 'need_gold'
	showVip.value = true
}

async function likePick(item) {
	if (!item) return
	try {
		const res = await apiSwipe({ target_id: item.id, action: 'like', feed_mode: 'top_picks' })
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
			uni.showToast({ title: 'Liked', icon: 'none' })
		}
		if (typeof data.daily_like_left === 'number') dailyLeft.value = data.daily_like_left
	} catch (e) {
		if (!handleVipError(e)) {
			uni.showToast({ title: (e && e.message) || 'Like failed', icon: 'none' })
		}
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
				expireAt: data.match.expire_at || data.match.expire_at,
				messagingMode: data.match.messaging_mode,
			}
			showMatch.value = true
			track('match', { target_id: target.id, conversation_id: matchedConversationId.value })
		}
		list.value = list.value.slice(1)
		photoIndex.value = 0
		if (action === 'super_like' && inv.value.super_like > 0) {
			inv.value.super_like -= 1
			pulseStock('super_like')
		}
		if (typeof data.daily_like_left === 'number') dailyLeft.value = data.daily_like_left
		if (!list.value.length) loadFeed(true)
		else maybePrefetch()
	} catch (e) {
		dx.value = 0
		dy.value = 0
		flying.value = false
		if (!handleVipError(e)) {
			uni.showToast({ title: (e && e.message) || 'Swipe failed', icon: 'none' })
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
		if (inv.value.rewind > 0) inv.value.rewind -= 1
		pulseStock('rewind')
		uni.showToast({ title: 'Rewound', icon: 'none' })
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
		if (inv.value.boost > 0) inv.value.boost -= 1
		pulseStock('boost')
		uni.showToast({ title: boostLabel() + ' on', icon: 'none' })
	} catch (e) {
		handleVipError(e) || ((vipReason.value = 'need_boost'), (showVip.value = true))
	}
}

function openFilter() {
	trackClick('filter_open')
	showFilter.value = true
}

function openPassport() {
	trackClick('passport_open')
	showPassport.value = true
}

function openDetail() {
	if (!current.value || flying.value) return
	const payload = encodeURIComponent(JSON.stringify(current.value))
	uni.navigateTo({
		url: `/pagesA/profile/detail?user_id=${current.value.id}&funnel=${payload}&photo=${photoIndex.value}`
	})
}

function goChat() {
	showMatch.value = false
	const id = matchedConversationId.value
	if (id) {
		uni.navigateTo({ url: `/pagesA/chat/room?id=${id}` })
		return
	}
	uni.switchTab({ url: '/pages/chat/index' })
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
	if (countdownTimer) clearInterval(countdownTimer)
	countdownTimer = setInterval(tickCountdowns, 1000)
})
onShow(() => {
	apiHeartbeat().catch(() => {})
	refreshTabBadges()
	loadInventory()
	tickCountdowns()
})
</script>

<style scoped>
.discover-page {
	min-height: 100vh;
	background: #F8F8F8;
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
.flame {
	width: 36rpx; height: 44rpx; margin-right: 10rpx;
	background: linear-gradient(180deg, #FD267A 0%, #FF6036 100%);
	border-radius: 40% 40% 48% 48%;
	clip-path: polygon(50% 0%, 88% 42%, 70% 100%, 30% 100%, 12% 42%);
}
.logo {
	font-size: 40rpx;
	font-weight: 800;
	letter-spacing: 1rpx;
	color: #FF4458;
}
.top-actions { display: flex; flex-direction: row; align-items: center; }
.likes-left {
	color: #FF4458; font-size: 24rpx; font-weight: 700; margin-right: 8rpx;
	min-width: 40rpx; text-align: right;
}
.mode-tabs {
	position: absolute;
	left: 0; right: 0;
	top: calc(env(safe-area-inset-top) + 72rpx);
	z-index: 22;
	display: flex; flex-direction: row; justify-content: center; 
	padding: 0 24rpx 10rpx;
	pointer-events: none;
}
.mode-tabs .mode-tab + .mode-tab { margin-left: 12rpx; }
.mode-tabs .mode-tab { pointer-events: auto; }
.mode-tab {
	padding: 10rpx 28rpx 14rpx;
	border-radius: 0;
	background: transparent;
	border-bottom: 4rpx solid transparent;
}
.mode-tab text { color: #666; font-size: 26rpx; font-weight: 600; }
.mode-tab.on { background: transparent; border-bottom-color: #FF4458; }
.mode-tab.on text { color: #111; font-weight: 800; }
.icon-btn {
	width: 64rpx; height: 64rpx; border-radius: 50%;
	background: transparent; margin-left: 8rpx;
	display: flex; align-items: center; justify-content: center;
}
.ico.pin {
	width: 22rpx; height: 22rpx; border: 2rpx solid #999;
	border-radius: 50% 50% 50% 0; transform: rotate(-45deg);
}
.ico.sliders {
	width: 30rpx; height: 22rpx;
	background:
		linear-gradient(#999,#999) 0 4rpx/100% 3rpx no-repeat,
		linear-gradient(#999,#999) 0 18rpx/100% 3rpx no-repeat,
		radial-gradient(circle,#999 45%,transparent 46%) 8rpx 0/12rpx 12rpx no-repeat,
		radial-gradient(circle,#999 45%,transparent 46%) 18rpx 12rpx/12rpx 12rpx no-repeat;
}
.boost-banner {
	position: absolute;
	left: 24rpx; right: 24rpx;
	top: calc(env(safe-area-inset-top) + 128rpx);
	z-index: 21;
	background: rgba(255,68,88,0.16);
	border: 1px solid rgba(255,68,88,0.35);
	border-radius: 16rpx;
	padding: 14rpx 18rpx;
}
.boost-banner.passport {
	background: rgba(110,168,254,0.14);
	border-color: rgba(110,168,254,0.4);
}
.boost-banner text { color:#FF4458; font-size:24rpx; }
.boost-banner.passport text { color:#2563EB; }
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
	box-shadow: 0 12rpx 40rpx rgba(0,0,0,0.12);
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
.stamp text { font-size: 44rpx; font-weight: 900; letter-spacing: 2rpx; }
.like-stamp { left: 36rpx; border-color: #2dd36f; }
.like-stamp text { color: #2dd36f; }
.nope-stamp { right: 36rpx; border-color: #fd5068; transform: rotate(18deg); }
.nope-stamp text { color: #fd5068; }
.super-stamp {
	left: 50%; top: 160rpx; transform: translateX(-50%) rotate(-8deg);
	border-color: #1DA1F2;
}
.super-stamp text { color: #1DA1F2; font-size: 36rpx; }
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
	border: 2rpx solid rgba(0,0,0,0.08);
	display: flex; align-items: center; justify-content: center;
	margin: 0 10rpx;
	box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.1);
}
.dock-btn:active { transform: scale(0.88); }
.dock-btn.pop { animation: stockPop 0.42s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes stockPop {
	0% { transform: scale(1); }
	40% { transform: scale(1.18); }
	100% { transform: scale(1); }
}
.dock-btn text { font-weight: 700; line-height: 1; }
.dock-badge {
	position: absolute; top: -6rpx; right: -6rpx;
	min-width: 32rpx; height: 32rpx; padding: 0 6rpx;
	border-radius: 999rpx; background: #FF4458;
	display: flex; align-items: center; justify-content: center;
}
.dock-badge text { color: #fff; font-size: 18rpx; font-weight: 700; }
.dock-btn.rewind { width: 88rpx; height: 88rpx; }
.dock-btn.rewind text { color: #F5C451; font-size: 40rpx; }
.dock-btn.nope { width: 112rpx; height: 112rpx; border-color: #FD5068; }
.dock-btn.nope text { color: #FD5068; font-size: 64rpx; }
.dock-btn.super { width: 88rpx; height: 88rpx; border-color: #1DA1F2; }
.dock-btn.super text { color: #1DA1F2; font-size: 40rpx; }
.dock-btn.like { width: 112rpx; height: 112rpx; border-color: #2DD36F; }
.dock-btn.like text { color: #2DD36F; font-size: 52rpx; }
.dock-btn.boost { width: 88rpx; height: 88rpx; border-color: #A855F7; }
.dock-btn.boost text { color: #A855F7; font-size: 36rpx; }
.picks-scroll {
	height: 100vh;
	padding: calc(env(safe-area-inset-top) + 140rpx) 24rpx 40rpx;
	box-sizing: border-box;
}
.picks-head {
	display:flex; flex-direction:row; align-items:flex-start; justify-content:space-between;
	margin-bottom: 8rpx;
}
.picks-refresh {
	width:64rpx; height:64rpx; border-radius:50%; background:#fff;
	border:1px solid rgba(0,0,0,0.08);
	display:flex; align-items:center; justify-content:center;
}
.picks-refresh text { color:#FD267A; font-size:32rpx; }
.picks-title {
	display: block; color: #111; font-size: 36rpx; font-weight: 800; margin: 8rpx 0 4rpx;
}
.picks-sub { display: block; color: #666; font-size: 22rpx; margin-bottom: 20rpx; }
.pick-tags { margin-top: 6rpx; }
.pick-tag {
	display:inline-block; background: rgba(255,255,255,0.22); color:#fff;
	font-size:18rpx; padding:4rpx 12rpx; border-radius:999rpx;
}
.picks-grid {
	display: flex; flex-direction: row; flex-wrap: wrap;
}
.pick-card {
	width: 48%; margin-right: 4%; margin-bottom: 16rpx;
	height: 420rpx; border-radius: 24rpx; overflow: hidden; position: relative;
	background: #FFFFFF;
	box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.08);
}
.pick-card:nth-child(2n) { margin-right: 0; }
.pick-img { width: 100%; height: 100%; }
.pick-fade {
	position: absolute; left: 0; right: 0; bottom: 0; height: 40%;
	background: linear-gradient(to top, rgba(0,0,0,0.85), transparent);
}
.pick-meta { position: absolute; left: 16rpx; right: 80rpx; bottom: 20rpx; z-index: 2; }
.pick-name { color: #fff; font-size: 28rpx; font-weight: 700; }
.pick-like {
	position: absolute; right: 16rpx; bottom: 16rpx; z-index: 3;
	width: 64rpx; height: 64rpx; border-radius: 50%; background: #FF4458;
	display: flex; align-items: center; justify-content: center;
}
.pick-like text { color: #fff; font-size: 32rpx; }
.picks-empty { padding-top: 80rpx; }
.explore-scroll {
	height: 100vh;
	padding: calc(env(safe-area-inset-top) + 140rpx) 24rpx 40rpx;
	box-sizing: border-box;
}
.explore-title {
	display: block; color: #111; font-size: 36rpx; font-weight: 800; margin: 8rpx 0 4rpx;
}
.explore-sub { display: block; color: #666; font-size: 22rpx; margin-bottom: 16rpx; }
.explore-filters {
	display: flex; flex-direction: row; margin-bottom: 18rpx; 
}
.explore-filters .ef + .ef { margin-left: 10rpx; }
.ef {
	padding: 10rpx 22rpx; border-radius: 999rpx;
	background: #fff; border: 1px solid rgba(253,38,122,0.25);
	box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
}
.ef text { color: #666; font-size: 22rpx; }
.ef.on { background: #FF4458; border-color: #FF4458; }
.ef.on text { color: #fff; font-weight: 700; }
.explore-grid {
	display: flex; flex-direction: row; flex-wrap: wrap;
}
.ex-card {
	width: 48%; margin-right: 4%; margin-bottom: 16rpx;
	height: 380rpx; border-radius: 24rpx; overflow: hidden; position: relative;
	background: #FFFFFF;
	box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.08);
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
	width: 36rpx; height: 36rpx; border-radius: 50%; background: #1DA1F2;
	display: flex; align-items: center; justify-content: center;
}
.ex-verified text { color: #fff; font-size: 20rpx; font-weight: 800; }
.ex-meta { position: absolute; left: 16rpx; right: 80rpx; bottom: 20rpx; z-index: 2; }
.ex-name { display:block; color: #fff; font-size: 28rpx; font-weight: 700; }
.ex-city { display:block; color: rgba(255,255,255,0.85); font-size: 20rpx; margin-top: 4rpx; }
.ex-like {
	position: absolute; right: 16rpx; bottom: 16rpx; z-index: 3;
	width: 64rpx; height: 64rpx; border-radius: 50%; background: #FF4458;
	display: flex; align-items: center; justify-content: center;
	box-shadow: 0 6rpx 16rpx rgba(255,68,88,0.35);
}
.ex-like text { color: #fff; font-size: 32rpx; }
.explore-empty { padding-top: 80rpx; }
.empty { padding-top: 280rpx; text-align: center; color: #666; }
.empty-title { display:block; color:#111; font-size:34rpx; margin-bottom:12rpx; }
.empty-sub { display:block; color:#666; font-size:24rpx; padding:0 40rpx; margin-bottom:24rpx; }
.reload {
	margin: 24rpx auto 0; width: 240rpx;
	background: linear-gradient(90deg, #FD267A, #FF6036);
	border-radius: 999rpx; padding: 18rpx;
	text-align: center;
}
.reload text { color: #fff; }
.reload.gold-cta {
	background: linear-gradient(90deg, #F5C451, #E8A317);
	box-shadow: 0 6rpx 20rpx rgba(245,196,81,0.35);
}
.reload.gold-cta text { color: #111; font-weight: 800; }
</style>
