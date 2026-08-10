<template>
	<view class="discover-page">
		<view class="top-bar">
			<view class="logo-wrap">
				<image class="bee-logo" src="/static/icons/bee-sm.png" mode="aspectFit" />
				<text class="logo display-font">{{ APP_NAME_DISPLAY }}</text>
			</view>
			<view class="top-actions">
				<text class="likes-left" v-if="dailyLeft !== null">{{ dailyLeft }}</text>
				<view class="icon-btn" @click="openPassport"><view class="ico pin" /></view>
				<view class="icon-btn" @click="openFilter"><view class="ico sliders" /></view>
			</view>
		</view>

		<view class="mode-bar">
			<view
				v-for="m in DATING_MODES"
				:key="m.id"
				class="mode"
				:class="{ on: datingMode === m.id }"
				@click="switchMode(m.id)"
			>
				<text>{{ m.label }}</text>
			</view>
		</view>

		<view class="boost-banner" v-if="boostActive">
			<text>Spotlight · {{ boostLeft || 'live' }} left</text>
		</view>
		<view class="boost-banner passport" v-if="passportCity">
			<text>Traveling in {{ passportCity }}</text>
		</view>

		<!-- Best Bees / For You -->
		<view class="bees-section" v-if="bestBees.length && !loading">
			<view class="bees-head">
				<text class="bees-title display-font">Best Bees</text>
				<text class="bees-sub">For You · top picks today</text>
			</view>
			<scroll-view scroll-x class="bees-row">
				<view
					v-for="u in bestBees"
					:key="'bb'+u.id"
					class="bee-card"
					@click="openBestBee(u)"
				>
					<image :src="beePhoto(u)" class="bee-img" mode="aspectFill" />
					<text class="bee-name">{{ u.nickname }}</text>
				</view>
			</scroll-view>
		</view>

		<!-- Vertical full-profile stack -->
		<scroll-view
			v-if="current"
			scroll-y
			class="stack"
			:scroll-top="stackScroll"
			@scrolltolower="maybePrefetch"
		>
			<view class="profile-stack" @touchstart="onTouchStart" @touchmove="onTouchMove" @touchend="onTouchEnd">
				<view class="hero">
					<swiper class="hero-swiper" :current="photoIndex" @change="onSwiper">
						<swiper-item v-for="(p, i) in photos" :key="i">
							<image class="hero-img" :src="p.url || p" mode="aspectFill" />
						</swiper-item>
					</swiper>
					<view class="photo-progress" v-if="photos.length > 1">
						<view v-for="(p, i) in photos" :key="i" class="prog-seg" :class="{ on: i === photoIndex }" />
					</view>
					<view class="hero-fade" />
					<view class="hero-info">
						<view class="name-row">
							<text class="name display-font">{{ current.nickname }}</text>
							<text class="age">{{ current.age }}</text>
							<view v-if="current.is_verified" class="verified"><text>✓</text></view>
							<view v-if="current.is_online" class="online-dot" />
						</view>
						<view class="pill-row">
							<view class="pill" v-if="current.job"><text>{{ current.job }}</text></view>
							<view class="pill" v-if="current.city"><text>📍 {{ current.city }}</text></view>
						</view>
					</view>
					<view class="card-compliment" @click.stop="openCompliment('photo')">
						<image class="cc-ico" src="/static/icons/dock-compliment.png" mode="aspectFit" />
						<text class="cc-label">Compliment</text>
					</view>
				</view>

				<view class="body">
					<view class="section" v-if="current.bio">
						<text class="section-title">About</text>
						<text class="section-body" @click="openCompliment('bio')">{{ current.bio }}</text>
					</view>

					<view class="section" v-if="promptEntries.length">
						<text class="section-title">Prompts</text>
						<view
							v-for="(pr, i) in promptEntries"
							:key="'pr'+i"
							class="prompt-card"
							@click="openCompliment('prompt', i)"
						>
							<text class="prompt-q">{{ pr.q }}</text>
							<text class="prompt-a">{{ pr.a }}</text>
							<text class="prompt-cta">Compliment ›</text>
						</view>
					</view>

					<view class="section" v-if="openingMoves.length">
						<text class="section-title">Opening Moves</text>
						<view class="om" v-for="(m, i) in openingMoves" :key="'om'+i"><text>{{ m }}</text></view>
					</view>

					<view class="section" v-if="voicePrompt.url">
						<text class="section-title">Voice prompt</text>
						<text class="prompt-q">{{ voicePrompt.q }}</text>
						<Waveform :seed="voicePrompt.url" :playing="playingVoice" label="Play" @toggle="toggleVoice" />
						<text class="prompt-cta" @click="openCompliment('voice')">Compliment voice ›</text>
					</view>

					<view class="section" v-if="videoPrompt.url">
						<text class="section-title">Video prompt</text>
						<text class="prompt-q">{{ videoPrompt.q }}</text>
						<video class="prompt-video" :src="videoPrompt.url" controls />
						<text class="prompt-cta" @click="openCompliment('video')">Compliment video ›</text>
					</view>

					<view class="section" v-if="badgeList.length">
						<text class="section-title">Badges</text>
						<view class="pill-row">
							<view class="pill badge" v-for="b in badgeList" :key="b.id"><text>{{ b.label }}</text></view>
						</view>
					</view>

					<view class="section" v-if="(current.interests || []).length">
						<text class="section-title">Interests</text>
						<view class="pill-row">
							<view class="pill" v-for="(t, i) in current.interests" :key="i"><text>{{ t }}</text></view>
						</view>
					</view>

					<view class="section" v-if="current.looking_for">
						<text class="section-title">Looking for</text>
						<text class="section-body">{{ current.looking_for }}</text>
					</view>

					<view class="inline-photo" v-if="photos[1]">
						<image :src="photos[1].url || photos[1]" mode="aspectFill" class="inline-img" />
					</view>
					<view class="inline-photo" v-if="photos[2]">
						<image :src="photos[2].url || photos[2]" mode="aspectFill" class="inline-img" />
					</view>

					<view class="bottom-space" />
				</view>
			</view>
		</scroll-view>

		<view v-else-if="loading" class="empty">
			<text class="empty-title">Finding people near you…</text>
		</view>
		<view v-else class="empty">
			<text class="empty-title">{{ reviewMode ? 'Review mode' : "There's no one new around you" }}</text>
			<text class="empty-sub" v-if="reviewMode">Feed is empty while the app is under store review.</text>
			<text class="empty-sub" v-else>Try Passport, switch modes, or widen your filters</text>
			<view class="reload" v-if="!reviewMode" @click="loadFeed(true)"><text>Refresh</text></view>
		</view>

		<view class="action-dock" v-if="current">
			<view class="dock-btn rewind" @click="doRewind">
				<image src="/static/icons/dock-rewind.png" class="dock-ico" mode="aspectFit" />
				<view class="dock-badge" v-if="inv.rewind > 0"><text>{{ inv.rewind > 9 ? '9+' : inv.rewind }}</text></view>
			</view>
			<view class="dock-btn nope" @click="doAction('pass')">
				<image src="/static/icons/dock-nope.png" class="dock-ico" mode="aspectFit" />
			</view>
			<view class="dock-btn super" @click="openCompliment('photo')">
				<image src="/static/icons/dock-compliment.png" class="dock-ico" mode="aspectFit" />
				<view class="dock-badge" v-if="inv.super_like > 0"><text>{{ inv.super_like > 9 ? '9+' : inv.super_like }}</text></view>
			</view>
			<view class="dock-btn like" @click="doAction('like')">
				<image src="/static/icons/dock-like.png" class="dock-ico dark" mode="aspectFit" />
			</view>
			<view class="dock-btn boost" @click="doBoost">
				<image src="/static/icons/dock-boost.png" class="dock-ico" mode="aspectFit" />
				<view class="dock-badge" v-if="inv.boost > 0"><text>{{ inv.boost > 9 ? '9+' : inv.boost }}</text></view>
			</view>
		</view>

		<VipSheet v-if="showVip" v-model:show="showVip" :reason="vipReason" @purchased="onPurchased" />
		<FilterSheet v-model:show="showFilter" @saved="reloadFeed" />
		<PassportSheet v-model:show="showPassport" @saved="reloadFeed" />
		<ComplimentSheet
			v-if="showCompliment"
			v-model:show="showCompliment"
			:user="current"
			:photo-url="currentPhoto"
			:initial-kind="complimentKind"
			:initial-prompt-index="complimentPromptIndex"
			@sent="onComplimentSent"
			@need-shop="onComplimentNeedShop"
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
		<SparkTabBar />
	</view>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { onShow } from '@dcloudio/uni-app'
import { apiFeed, apiSwipe, apiRewind } from '@/api/recommend.js'
import { apiBoost, apiEntitlements } from '@/api/vip.js'
import { apiHeartbeat } from '@/api/auth.js'
import { apiProfileUpdate } from '@/api/profile.js'
import { track, trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { APP_NAME_DISPLAY, PACKAGE_NAME } from '@/config/config.js'
import {
	isComplimentEnabled, DATING_MODES, getDatingMode, setDatingMode,
	formatBoostCountdown, resolveBadges,
} from '@/utils/productProfile.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import FilterSheet from '@/components/FilterSheet/FilterSheet.vue'
import PassportSheet from '@/components/PassportSheet/PassportSheet.vue'
import ComplimentSheet from '@/components/ComplimentSheet/ComplimentSheet.vue'
import MatchModal from '@/components/MatchModal/MatchModal.vue'
import Waveform from '@/components/Waveform/Waveform.vue'

const list = ref([])
const bestBees = ref([])
const photoIndex = ref(0)
const showVip = ref(false)
const showFilter = ref(false)
const showPassport = ref(false)
const showCompliment = ref(false)
const showMatch = ref(false)
const inv = ref({ super_like: 0, boost: 0, rewind: 0 })
const vipReason = ref('')
const matchedUser = ref(null)
const matchedConversationId = ref(null)
const matchMeta = ref({ matchId: null, iAmOpener: null, expireAt: '', messagingMode: '' })
const reviewMode = ref(false)
const boostActive = ref(false)
const boostEndAt = ref('')
const boostLeft = ref('')
const passportCity = ref('')
const dailyLeft = ref(null)
const loading = ref(false)
const datingMode = ref(getDatingMode())
const complimentKind = ref('photo')
const complimentPromptIndex = ref(0)
const stackScroll = ref(0)
const playingVoice = ref(false)
const flying = ref(false)
let feedLock = false
let swipeBusy = false
let boostTimer = null
let voiceCtx = null
const FEED_SOFT_CAP = 60
const FEED_LOW_WATER = 4

let startX = 0
let startY = 0
let moved = false
const dx = ref(0)

const current = computed(() => list.value[0] || null)
const photos = computed(() => {
	const c = current.value
	if (!c) return []
	const listP = c.photos || []
	if (listP.length) return listP
	if (c.avatar_url) return [{ url: c.avatar_url }]
	return []
})
const currentPhoto = computed(() => {
	if (!photos.value.length) return current.value?.avatar_url || ''
	const p = photos.value[Math.min(photoIndex.value, photos.value.length - 1)]
	return p.url || p
})

const promptEntries = computed(() => {
	const life = (current.value && current.value.lifestyle) || {}
	const arr = Array.isArray(life.prompts) ? life.prompts : []
	const filled = arr.filter((p) => p && p.q && p.a)
	if (filled.length) return filled
	if (life.prompt && life.prompt.q && life.prompt.a) return [life.prompt]
	return []
})
const openingMoves = computed(() => {
	const listM = (current.value && current.value.lifestyle && current.value.lifestyle.opening_moves) || []
	return Array.isArray(listM) ? listM.filter(Boolean) : []
})
const voicePrompt = computed(() => ((current.value && current.value.lifestyle && current.value.lifestyle.voice_prompt) || {}))
const videoPrompt = computed(() => ((current.value && current.value.lifestyle && current.value.lifestyle.video_prompt) || {}))
const badgeList = computed(() => resolveBadges(current.value))

function beePhoto(u) {
	if (u.photos && u.photos.length) return u.photos[0].url
	return u.avatar_url || ''
}

function onSwiper(e) {
	photoIndex.value = e.detail.current
}

function onTouchStart(e) {
	if (flying.value || swipeBusy) return
	const t = e.touches[0]
	startX = t.clientX
	startY = t.clientY
	moved = false
	dx.value = 0
}
function onTouchMove(e) {
	if (flying.value || swipeBusy) return
	const t = e.touches[0]
	dx.value = t.clientX - startX
	const dy = t.clientY - startY
	if (Math.abs(dx.value) > 24 && Math.abs(dx.value) > Math.abs(dy)) moved = true
}
function onTouchEnd() {
	if (flying.value || swipeBusy) { dx.value = 0; return }
	if (!moved) { dx.value = 0; return }
	if (dx.value > 120) doAction('like')
	else if (dx.value < -120) doAction('pass')
	dx.value = 0
	moved = false
}

async function switchMode(id) {
	if (datingMode.value === id) return
	datingMode.value = setDatingMode(id)
	try {
		const me = uni.getStorageSync('userInfo') || {}
		const life = { ...(me.lifestyle || {}), dating_mode: id }
		await apiProfileUpdate({ lifestyle: life }).catch(() => {})
		me.lifestyle = life
		uni.setStorageSync('userInfo', me)
	} catch (e) {}
	await loadFeed(true)
	await loadBestBees()
}

async function loadFeed(reset = true) {
	const token = uni.getStorageSync('token')
	if (!token) {
		uni.reLaunch({ url: '/pages/auth/welcome' })
		return
	}
	if (flying.value || swipeBusy || feedLock) return
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
			mode: 'recommend',
			dating_mode: datingMode.value,
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
			stackScroll.value = 0
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
		passportCity.value = data.passport_city || ''
		dailyLeft.value = data.daily_like_left
		tickBoost()
		const boot = uni.getStorageSync('bootstrap') || {}
		if (boot.review_mode) reviewMode.value = true
		loading.value = false
		feedLock = false
	} catch (e) {
		loading.value = false
		feedLock = false
		if (!list.value.length) {
			uni.showToast({ title: 'Failed to load feed', icon: 'none' })
		}
	}
}

async function loadBestBees() {
	try {
		const res = await apiFeed({
			limit: 8,
			mode: 'best_bees',
			dating_mode: datingMode.value,
			package_name: PACKAGE_NAME,
			app_version: '1.0.0',
			platform: 'h5',
		})
		bestBees.value = ((res.results && res.results.list) || []).slice(0, 8)
	} catch (e) {
		bestBees.value = []
	}
}

function tickBoost() {
	if (!boostEndAt.value) {
		boostLeft.value = ''
		return
	}
	boostLeft.value = formatBoostCountdown(boostEndAt.value)
	if (!boostLeft.value || boostLeft.value === '0:00') {
		boostActive.value = false
		boostLeft.value = ''
	}
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

function openCompliment(kind = 'photo', promptIdx = 0) {
	if (!current.value) return
	trackClick('swipe_super')
	if (!isComplimentEnabled()) {
		doAction('super_like', { skipClick: true })
		return
	}
	complimentKind.value = kind
	complimentPromptIndex.value = promptIdx
	showCompliment.value = true
}

function onComplimentNeedShop() {
	vipReason.value = 'need_super_like'
	showVip.value = true
}

function onComplimentSent(data) {
	const target = current.value
	if (!target) return
	track('swipe', { action: 'compliment', target_id: target.id, matched: !!(data && data.matched) })
	if (data && data.matched && data.match) {
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
	} else {
		uni.showToast({ title: 'Compliment sent', icon: 'none' })
	}
	advanceCard()
}

async function doAction(action, opts = {}) {
	if (!current.value || flying.value || swipeBusy) return
	if (!opts.skipClick) {
		const btnMap = { like: 'swipe_like', pass: 'swipe_pass', super_like: 'swipe_super' }
		if (btnMap[action]) trackClick(btnMap[action])
	}
	flying.value = true
	swipeBusy = true
	const target = current.value
	try {
		const res = await apiSwipe({ target_id: target.id, action, feed_mode: 'recommend' })
		const data = res.results || {}
		track('swipe', { action, target_id: target.id, matched: !!data.matched })
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
		if (typeof data.daily_like_left === 'number') dailyLeft.value = data.daily_like_left
		advanceCard()
	} catch (e) {
		if (!handleVipError(e)) {
			uni.showToast({ title: (e && e.message) || 'Action failed', icon: 'none' })
		}
	} finally {
		flying.value = false
		swipeBusy = false
		dx.value = 0
	}
}

function advanceCard() {
	list.value = list.value.slice(1)
	photoIndex.value = 0
	stackScroll.value = 1
	setTimeout(() => { stackScroll.value = 0 }, 16)
	if (!list.value.length) loadFeed(true)
	else maybePrefetch()
}

async function doRewind() {
	trackClick('swipe_rewind')
	try {
		await apiRewind()
		await loadFeed(true)
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
		const res = await apiBoost()
		boostActive.value = true
		boostEndAt.value = (res.results && res.results.end_at) || ''
		tickBoost()
		uni.showToast({ title: 'Spotlight on', icon: 'none' })
		loadInventory()
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

function openBestBee(u) {
	const payload = encodeURIComponent(JSON.stringify(u))
	uni.navigateTo({
		url: `/pagesA/profile/detail?user_id=${u.id}&funnel=${payload}`
	})
}

function toggleVoice() {
	const url = voicePrompt.value.url
	if (!url) return
	try {
		if (voiceCtx) {
			voiceCtx.stop()
			voiceCtx.destroy()
			voiceCtx = null
			playingVoice.value = false
			return
		}
		voiceCtx = uni.createInnerAudioContext()
		voiceCtx.src = url
		voiceCtx.onEnded(() => { playingVoice.value = false })
		voiceCtx.play()
		playingVoice.value = true
	} catch (e) {}
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
	loadBestBees()
}

function reloadFeed() {
	loadFeed(true)
	loadBestBees()
}

onMounted(() => {
	loadFeed(true)
	loadBestBees()
	loadInventory()
	apiHeartbeat().catch(() => {})
	import('@/utils/maps.js').then((m) => m.reportLocation({ updateCity: false })).catch(() => {})
	boostTimer = setInterval(tickBoost, 1000)
})
onShow(() => {
	apiHeartbeat().catch(() => {})
	refreshTabBadges()
	loadInventory()
	datingMode.value = getDatingMode()
})
onUnmounted(() => {
	if (boostTimer) clearInterval(boostTimer)
	try { if (voiceCtx) voiceCtx.destroy() } catch (e) {}
})
</script>

<style scoped>
.discover-page {
	min-height: 100vh;
	background: #FAFAFA;
	padding-bottom: calc(200rpx + env(safe-area-inset-bottom));
	box-sizing: border-box;
}
.top-bar {
	display: flex; flex-direction: row; align-items: center; justify-content: space-between;
	padding: calc(env(safe-area-inset-top) + 8rpx) 28rpx 8rpx;
}
.logo-wrap { display: flex; flex-direction: row; align-items: center; }
.bee-logo { width: 40rpx; height: 40rpx; margin-right: 10rpx; }
.logo {
	font-size: 40rpx; font-weight: 800; letter-spacing: 1rpx; color: #111;
	font-family: 'Montserrat', sans-serif;
}
.top-actions { display: flex; flex-direction: row; align-items: center; }
.likes-left {
	color: #B8860B; font-size: 24rpx; font-weight: 700; margin-right: 8rpx;
	min-width: 40rpx; text-align: right;
}
.icon-btn {
	width: 64rpx; height: 64rpx; border-radius: 50%;
	display: flex; align-items: center; justify-content: center; margin-left: 8rpx;
}
.ico.pin {
	width: 22rpx; height: 22rpx; border: 2rpx solid #111;
	border-radius: 50% 50% 50% 0; transform: rotate(-45deg);
}
.ico.sliders {
	width: 30rpx; height: 22rpx;
	background:
		linear-gradient(#111,#111) 0 4rpx/100% 3rpx no-repeat,
		linear-gradient(#111,#111) 0 18rpx/100% 3rpx no-repeat,
		radial-gradient(circle,#111 45%,transparent 46%) 8rpx 0/12rpx 12rpx no-repeat,
		radial-gradient(circle,#111 45%,transparent 46%) 18rpx 12rpx/12rpx 12rpx no-repeat;
}
.mode-bar {
	display:flex; flex-direction:row; padding: 0 24rpx 12rpx;
}
.mode {
	flex:1; text-align:center; padding: 16rpx 0; margin-right: 10rpx;
	border-radius: 999rpx; background: #F3F3F3;
}
.mode:last-child { margin-right: 0; }
.mode.on { background: #FFC629; }
.mode text { color:#111; font-size:26rpx; font-weight:800; font-family: 'Montserrat', sans-serif; }
.boost-banner {
	margin: 0 24rpx 12rpx;
	background: rgba(255,198,41,0.2);
	border: 1px solid rgba(255,198,41,0.45);
	border-radius: 16rpx; padding: 14rpx 18rpx;
}
.boost-banner.passport {
	background: rgba(110,168,254,0.14);
	border-color: rgba(110,168,254,0.4);
}
.boost-banner text { color:#8A6D00; font-size:24rpx; font-weight:600; }
.boost-banner.passport text { color:#2563EB; }
.bees-section { padding: 8rpx 0 16rpx; }
.bees-head { padding: 0 28rpx 12rpx; }
.bees-title { display:block; color:#111; font-size:32rpx; font-weight:800; font-family: 'Montserrat', sans-serif; }
.bees-sub { display:block; color:#888; font-size:22rpx; margin-top:4rpx; }
.bees-row { white-space: nowrap; padding-left: 24rpx; }
.bee-card {
	display:inline-block; width: 160rpx; margin-right: 14rpx; vertical-align: top;
}
.bee-img {
	width: 160rpx; height: 200rpx; border-radius: 20rpx; background:#eee;
	border: 3rpx solid #FFC629;
}
.bee-name {
	display:block; text-align:center; color:#111; font-size:22rpx; font-weight:700; margin-top:8rpx;
	overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.stack {
	height: calc(100vh - 280rpx - env(safe-area-inset-top));
}
.profile-stack {
	margin: 0 20rpx; background:#fff; border-radius: 28rpx; overflow:hidden;
	box-shadow: 0 8rpx 28rpx rgba(0,0,0,0.08);
}
.hero { position: relative; height: 760rpx; }
.hero-swiper, .hero-img { width:100%; height:100%; }
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
.hero-fade {
	position:absolute; left:0; right:0; bottom:0; height: 40%;
	background: linear-gradient(to top, rgba(0,0,0,0.55), transparent); pointer-events:none;
}
.hero-info { position:absolute; left:28rpx; right:28rpx; bottom:36rpx; z-index:3; }
.name-row { display:flex; flex-direction:row; align-items:flex-end; margin-bottom:12rpx; }
.name { font-size:52rpx; color:#fff; font-weight:800; margin-right:12rpx; font-family: 'Montserrat', sans-serif; }
.age { font-size:42rpx; color:#fff; font-weight:500; margin-right:12rpx; }
.verified {
	width:34rpx; height:34rpx; border-radius:50%; background:#1DA1F2;
	display:flex; align-items:center; justify-content:center; margin-bottom:8rpx;
}
.verified text { color:#fff; font-size:18rpx; font-weight:800; }
.online-dot {
	width:16rpx; height:16rpx; border-radius:50%; background:#22C55E; margin-left:10rpx; margin-bottom:12rpx;
}
.pill-row { display:flex; flex-direction:row; flex-wrap:wrap; }
.pill {
	background: rgba(255,255,255,0.18); border-radius:999rpx; padding:10rpx 18rpx;
	margin-right:10rpx; margin-bottom:8rpx;
}
.pill text { color:#fff; font-size:22rpx; }
.body .pill { background:#FFF8E1; }
.body .pill text { color:#111; }
.body .pill.badge { background:#FFC629; }
.card-compliment {
	position:absolute; right:24rpx; bottom:200rpx; z-index:6;
	display:flex; flex-direction:row; align-items:center;
	background: rgba(255,255,255,0.95); border-radius:999rpx; padding:14rpx 22rpx;
	border: 1px solid rgba(255,198,41,0.55);
}
.cc-ico { width: 28rpx; height: 28rpx; margin-right: 8rpx; }
.cc-label { color:#111; font-size:24rpx; font-weight:800; }
.body { padding: 28rpx 28rpx 40rpx; }
.section { margin-bottom: 28rpx; }
.section-title {
	display:block; color:#111; font-size:30rpx; font-weight:800; margin-bottom:12rpx;
	font-family: 'Montserrat', sans-serif;
}
.section-body { display:block; color:#333; font-size:28rpx; line-height:1.45; }
.prompt-card {
	background:#FFFDF6; border-radius:20rpx; padding:22rpx; margin-bottom:14rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.prompt-q { display:block; color:#8A6D00; font-size:22rpx; font-weight:700; margin-bottom:8rpx; }
.prompt-a { display:block; color:#111; font-size:28rpx; line-height:1.4; }
.prompt-cta { display:block; color:#B8860B; font-size:22rpx; font-weight:800; margin-top:12rpx; }
.om {
	background:#F7F7F7; border-radius:16rpx; padding:18rpx 20rpx; margin-bottom:10rpx;
}
.om text { color:#333; font-size:26rpx; }
.prompt-video { width:100%; height:360rpx; border-radius:16rpx; margin-top:12rpx; background:#111; }
.inline-photo { margin-bottom: 20rpx; border-radius: 20rpx; overflow:hidden; height: 520rpx; }
.inline-img { width:100%; height:100%; }
.bottom-space { height: 40rpx; }
.action-dock {
	position: fixed; left: 0; right: 0;
	bottom: calc(120rpx + env(safe-area-inset-bottom));
	z-index: 40; display: flex; flex-direction: row; align-items: center; justify-content: center;
	padding: 0 24rpx;
}
.dock-btn {
	position: relative; border-radius: 50%; background: #FFFFFF;
	border: 2rpx solid #E5E5E5; display: flex; align-items: center; justify-content: center;
	margin: 0 10rpx; box-shadow: 0 8rpx 24rpx rgba(0,0,0,0.12);
}
.dock-btn:active { transform: scale(0.88); }
.dock-ico { width: 40rpx; height: 40rpx; }
.dock-ico.dark { width: 44rpx; height: 44rpx; }
.dock-badge {
	position: absolute; top: -6rpx; right: -6rpx;
	min-width: 32rpx; height: 32rpx; padding: 0 6rpx;
	border-radius: 999rpx; background: #FFC629;
	display: flex; align-items: center; justify-content: center;
}
.dock-badge text { color: #111; font-size: 18rpx; font-weight: 800; }
.dock-btn.rewind, .dock-btn.super, .dock-btn.boost { width: 88rpx; height: 88rpx; }
.dock-btn.nope, .dock-btn.like { width: 112rpx; height: 112rpx; }
.dock-btn.like { border-color: #FFC629; background:#FFC629; }
.empty { padding-top: 200rpx; text-align: center; color: #999; }
.empty-title { display:block; color:#111; font-size:34rpx; margin-bottom:12rpx; font-weight:700; }
.empty-sub { display:block; color:#777; font-size:24rpx; padding:0 40rpx; margin-bottom:24rpx; }
.reload {
	margin: 24rpx auto 0; width: 240rpx;
	background: #FFC629; border-radius: 999rpx; padding: 18rpx; text-align:center;
}
.reload text { color: #111; font-weight:700; }
</style>
