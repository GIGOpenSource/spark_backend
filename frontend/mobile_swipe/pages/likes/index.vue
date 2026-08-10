<template>
	<view class="page">
		<view class="header">
			<text class="title">Beeline</text>
		</view>

		<view class="tabs">
			<view class="tab" :class="{ on: tab === 'received' }" @click="tab = 'received'">
				<text>Beeline</text>
				<text class="tab-count" v-if="count">{{ count }}</text>
			</view>
			<view class="tab" :class="{ on: tab === 'sent' }" @click="switchSent">
				<text>Sent</text>
			</view>
		</view>

		<template v-if="tab === 'received'">
			<view v-if="!unlocked" class="gold-banner" :class="{ 'unlock-pulse': unlocking }" @click="openVip('need_gold')">
				<text class="banner-title">See who liked you with {{ goldName }}</text>
				<text class="banner-sub">{{ count || list.length }} likes waiting · Compliments highlighted</text>
			</view>

			<view class="chips">
				<view class="chip" :class="{ on: sortMode === 'all' }" @click="sortMode = 'all'"><text>All</text></view>
				<view class="chip" :class="{ on: sortMode === 'online' }" @click="sortMode = 'online'"><text>Recently active</text></view>
				<view class="chip" :class="{ on: sortMode === 'compliment' }" @click="sortMode = 'compliment'"><text>Compliments</text></view>
				<view class="chip" :class="{ on: sortMode === 'verified' }" @click="sortMode = 'verified'"><text>Verified</text></view>
				<view class="chip" :class="{ on: sortMode === 'nearby' }" @click="sortMode = 'nearby'"><text>Nearby</text></view>
				<view class="chip" @click="showFilter = true"><text>More</text></view>
			</view>

			<view class="grid">
				<view
					v-for="item in filteredList"
					:key="item.id || item.swipe_id"
					class="card"
					:class="{ highlight: !!item.compliment_message, 'unlock-in': unlocking && unlocked, complimented: !!item.compliment_message }"
					@click="open(item)"
				>
					<image :src="item.avatar_url" class="img" mode="aspectFill" :class="{ blur: item.blur || !unlocked }" />
					<view class="lock-overlay" v-if="item.blur || !unlocked">
						<text class="lock-icon">🔒</text>
						<text class="lock-text">Tap to unlock</text>
					</view>
					<view class="online" v-if="item.is_online" />
					<view class="sl-badge" v-if="item.action === 'super_like'"><text>★</text></view>
					<view class="compliment" v-if="item.compliment_message">
						<text>{{ item.compliment_message }}</text>
					</view>
					<template v-if="unlocked && !item.blur">
						<view class="footer">
							<text class="name">{{ displayName(item) }}</text>
							<view class="footer-actions" @click.stop>
								<view class="mini pass" @click="act(item, 'pass')"><text>×</text></view>
								<view class="mini like" @click="act(item, 'like')"><text>♥</text></view>
								<view class="hi" @click="openCompliment(item)"><text>Compliment</text></view>
							</view>
						</view>
					</template>
					<view v-else class="footer locked">
						<text class="name">Liked you</text>
					</view>
				</view>
			</view>
			<view v-if="loading" class="empty"><text>Loading Beeline…</text></view>
			<view v-else-if="!filteredList.length" class="empty">
				<text class="empty-title">Your Beeline is quiet</text>
				<text class="empty-sub">Keep browsing People — likes show up here</text>
			</view>
		</template>

		<template v-else>
			<view v-for="item in sentList" :key="item.swipe_id || item.id" class="sent-row">
				<view class="avatar-wrap" @click="openSent(item)">
					<image :src="item.avatar_url" class="avatar" mode="aspectFill" />
					<view class="online" v-if="item.is_online" />
				</view>
				<view class="info" @click="openSent(item)">
					<text class="s-name">{{ item.nickname }} {{ item.age }}</text>
					<text class="s-job">{{ sentStatus(item) }}</text>
				</view>
				<view
					class="hi-btn"
					:class="{ outline: !item.is_matched, muted: !item.is_matched && item.status !== 'expired' }"
					@click="onSentAction(item)"
				>
					<text>{{ sentLabel(item) }}</text>
				</view>
			</view>
			<view v-if="sentLoading" class="empty"><text>Loading…</text></view>
			<view v-else-if="!sentList.length" class="empty"><text>No likes sent yet</text></view>
		</template>

		<VipSheet v-if="showVip" v-model:show="showVip" :reason="vipReason" @purchased="onVipPurchased" />
		<FilterSheet v-model:show="showFilter" @saved="loadReceived" />
		<ComplimentSheet
			v-if="showCompliment"
			v-model:show="showCompliment"
			:user="complimentUser"
			:photo-url="complimentPhoto"
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
import { ref, computed } from 'vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { onShow } from '@dcloudio/uni-app'
import { apiLikesReceived, apiLikesSent } from '@/api/likes.js'
import { apiSwipe } from '@/api/recommend.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { trackClick } from '@/utils/analytics.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import MatchModal from '@/components/MatchModal/MatchModal.vue'
import ComplimentSheet from '@/components/ComplimentSheet/ComplimentSheet.vue'
import FilterSheet from '@/components/FilterSheet/FilterSheet.vue'
import { tierDisplayName } from '@/utils/productProfile.js'

const tab = ref('received')
const list = ref([])
const sentList = ref([])
const unlocked = ref(false)
const unlocking = ref(false)
const count = ref(0)
const showVip = ref(false)
const showFilter = ref(false)
const vipReason = ref('need_gold')
const loading = ref(false)
const sentLoading = ref(false)
const sortMode = ref('all')
const showMatch = ref(false)
const showCompliment = ref(false)
const complimentUser = ref(null)
const complimentPhoto = ref('')
const matchedUser = ref(null)
const matchedConversationId = ref(null)
const matchMeta = ref({ matchId: null, iAmOpener: null, expireAt: '', messagingMode: '' })
const goldName = tierDisplayName('gold')
let wasLocked = true

const filteredList = computed(() => {
	const rows = list.value || []
	if (sortMode.value === 'online') return rows.filter((x) => x.is_online)
	if (sortMode.value === 'compliment') return rows.filter((x) => !!x.compliment_message)
	if (sortMode.value === 'verified') return rows.filter((x) => !!x.is_verified)
	if (sortMode.value === 'nearby') {
		return rows.slice().sort((a, b) => {
			const da = Number(a.distance_km != null ? a.distance_km : 9999)
			const db = Number(b.distance_km != null ? b.distance_km : 9999)
			return da - db
		})
	}
	// Compliments float to top by default
	return rows.slice().sort((a, b) => Number(!!b.compliment_message) - Number(!!a.compliment_message))
})

async function loadReceived() {
	loading.value = true
	try {
		const res = await apiLikesReceived()
		list.value = (res.results && res.results.list) || []
		const nextUnlocked = !!(res.results && res.results.unlocked)
		if (wasLocked && nextUnlocked) {
			unlocking.value = true
			try { uni.vibrateShort({ type: 'medium' }) } catch (e) {}
			setTimeout(() => { unlocking.value = false }, 900)
		}
		wasLocked = !nextUnlocked
		unlocked.value = nextUnlocked
		count.value = (res.results && res.results.count) || list.value.length
		refreshTabBadges()
	} catch (e) {
		uni.showToast({ title: 'Failed to load Beeline', icon: 'none' })
	}
	loading.value = false
}

function onVipPurchased() {
	reloadCurrent()
}

async function loadSent() {
	sentLoading.value = true
	try {
		const res = await apiLikesSent()
		sentList.value = (res.results && res.results.list) || []
	} catch (e) {
		sentList.value = []
		uni.showToast({ title: 'Failed to load', icon: 'none' })
	}
	sentLoading.value = false
}

function reloadCurrent() {
	if (tab.value === 'sent') loadSent()
	else loadReceived()
}

function switchSent() {
	tab.value = 'sent'
	loadSent()
}

function displayName(item) {
	if (item.blur || !unlocked.value) return 'Liked you'
	return `${item.nickname || ''} ${item.age || ''}`.trim()
}

function openVip(reason) {
	trackClick('open_vip')
	vipReason.value = reason
	showVip.value = true
}

function open(item) {
	if (item.blur || !unlocked.value || String(item.id).startsWith('funnel')) {
		openVip('need_gold')
		return
	}
	uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${item.id}` })
}

function openSent(item) {
	uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${item.id}` })
}

function sentStatus(item) {
	if (item.status === 'matched') return "It's a Match · tap to chat"
	if (item.status === 'expired') return 'Expired · like again'
	if (item.action === 'super_like') return 'Compliment sent · waiting'
	return 'Waiting for them'
}

function sentLabel(item) {
	if (item.is_matched) return 'Message'
	if (item.status === 'expired') return 'Like again'
	return 'Waiting'
}

async function onSentAction(item) {
	if (item.is_matched && item.conversation_id) {
		uni.navigateTo({ url: `/pagesA/chat/room?id=${item.conversation_id}` })
		return
	}
	if (item.is_matched) {
		uni.switchTab({ url: '/pages/chat/index' })
		return
	}
	if (item.status === 'expired') {
		try {
			await apiSwipe({ target_id: item.id, action: 'like' })
			uni.showToast({ title: 'Liked again', icon: 'none' })
			await loadSent()
		} catch (e) {
			if (e && (e.message === 'daily_like_limit' || (e.results && e.results.need_vip))) {
				openVip(e.message || 'need_vip')
			} else {
				uni.showToast({ title: (e && e.message) || 'Like failed', icon: 'none' })
			}
		}
		return
	}
	uni.showToast({ title: 'Waiting for them to like you back', icon: 'none' })
}

async function act(item, action) {
	if (action === 'like') trackClick('like_back')
	try {
		const res = await apiSwipe({ target_id: item.id, action })
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
		} else if (action === 'like') {
			uni.showToast({ title: 'Liked', icon: 'none' })
		}
	} catch (e) {
		const msg = (e && e.message) || ''
		if (/need_|daily_like|limit/.test(msg) || (e && e.results && e.results.need_vip)) {
			openVip(msg || 'need_vip')
		} else {
			uni.showToast({ title: msg || 'Action failed', icon: 'none' })
		}
	}
}

function openCompliment(item) {
	complimentUser.value = item
	complimentPhoto.value = item.avatar_url || (item.compliment_photo || '')
	showCompliment.value = true
}

function onComplimentNeedShop() {
	openVip('need_super_like')
}

function onComplimentSent(data) {
	if (complimentUser.value) {
		list.value = list.value.filter((x) => x.id !== complimentUser.value.id)
	}
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
	} else {
		uni.showToast({ title: 'Compliment sent', icon: 'none' })
	}
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

onShow(() => {
	if (tab.value === 'sent') loadSent()
	else loadReceived()
})
</script>

<style scoped>
.page { min-height:100vh; background: var(--bg, #FFFFFF); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 160rpx; }
.header { margin-bottom:12rpx; }
.title { display:block; color:#111; font-size:44rpx; font-weight:800; }
.tabs {
	display:flex; flex-direction:row; background:#fff; border-radius:999rpx; padding:6rpx;
	margin-bottom:20rpx; border: 1px solid rgba(255,198,41,0.45);
}
.tab {
	flex:1; display:flex; flex-direction:row; align-items:center; justify-content:center;
	padding:16rpx 8rpx; border-radius:999rpx;
}
.tab.on { background:#FFC629; }
.tab text { color:#666; font-size:26rpx; font-weight:600; }
.tab.on text { color:#111; font-weight:700; }
.tab-count {
	margin-left:8rpx; background:rgba(17,17,17,0.12); border-radius:999rpx;
	padding:2rpx 10rpx; font-size:20rpx !important;
}
.gold-banner {
	background: #FFF8E1;
	border: 1px solid rgba(255,198,41,0.55);
	border-radius: 24rpx;
	padding: 28rpx;
	margin-bottom: 24rpx;
}
.gold-banner.unlock-pulse { animation: unlockPulse 0.7s ease; }
@keyframes unlockPulse {
	0% { transform: scale(0.98); box-shadow: 0 0 0 0 rgba(255,198,41,0.5); }
	50% { transform: scale(1.02); box-shadow: 0 0 0 16rpx rgba(255,198,41,0); }
	100% { transform: scale(1); }
}
.banner-title { display:block; color:#111; font-size:30rpx; font-weight:700; margin-bottom:8rpx; }
.banner-sub { display:block; color:#B8860B; font-size:24rpx; }
.chips { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom: 18rpx; }
.chip {
	background:#FFF8E1; border-radius:999rpx; padding:10rpx 20rpx; margin-right:10rpx; margin-bottom:8rpx;
	border: 1px solid rgba(255,198,41,0.4);
}
.chip.on { background:#FFC629; border-color:#FFC629; }
.chip text { color:#666; font-size:22rpx; }
.chip.on text { color:#111; font-weight:700; }
.grid { display:flex; flex-direction:row; flex-wrap:wrap; }
.card {
	width: 48%;
	margin-right: 4%;
	margin-bottom: 20rpx;
	border-radius: 24rpx;
	overflow: hidden;
	background: #F5F5F5;
	position: relative;
}
.card.highlight { box-shadow: 0 0 0 3rpx #FFC629; }
.card.complimented {
	animation: complimentGlow 1.2s ease-out;
}
@keyframes complimentGlow {
	0% { box-shadow: 0 0 0 0 rgba(255,198,41,0.9); transform: scale(0.98); }
	40% { box-shadow: 0 0 0 12rpx rgba(255,198,41,0.35); transform: scale(1.02); }
	100% { box-shadow: 0 0 0 3rpx #FFC629; transform: scale(1); }
}
.card.unlock-in { animation: cardReveal 0.65s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes cardReveal {
	0% { filter: blur(12px); transform: scale(1.04); }
	100% { filter: blur(0); transform: scale(1); }
}
.card:nth-child(2n) { margin-right: 0; }
.img { width:100%; height:420rpx; }
.img.blur { filter: blur(18px); transform: scale(1.1); }
.lock-overlay {
	position:absolute; left:0; right:0; top:0; bottom:0;
	background: rgba(255,255,255,0.25);
	display:flex; flex-direction:column; align-items:center; justify-content:center;
	z-index:2;
}
.lock-icon { font-size:36rpx; margin-bottom:8rpx; }
.lock-text { color:#111; font-size:22rpx; font-weight:600; }
.online {
	position:absolute; left:16rpx; top:16rpx; width:18rpx; height:18rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #fff; z-index:3;
}
.sl-badge {
	position:absolute; right:16rpx; top:16rpx; z-index:3;
	width:44rpx; height:44rpx; border-radius:50%; background:#1DA1F2;
	display:flex; align-items:center; justify-content:center;
}
.sl-badge text { color:#fff; font-size:24rpx; }
.compliment {
	position:absolute; left:12rpx; right:12rpx; bottom: 120rpx; z-index:3;
	background: #FFC629; border-radius: 12rpx; padding: 10rpx 14rpx;
	box-shadow: 0 6rpx 16rpx rgba(0,0,0,0.18);
}
.compliment text { color:#111; font-size:22rpx; line-height:1.3; font-weight:600; }
.footer {
	position:absolute; left:0; right:0; bottom:0; z-index:3;
	padding: 16rpx;
	background: linear-gradient(to top, rgba(0,0,0,0.75), transparent);
}
.footer.locked { padding-bottom: 20rpx; }
.name { display:block; color:#fff; font-size:26rpx; margin-bottom:12rpx; }
.footer-actions { display:flex; flex-direction:row; align-items:center; }
.mini {
	width:56rpx; height:56rpx; border-radius:50%;
	display:flex; align-items:center; justify-content:center; margin-right:10rpx;
}
.mini text { font-size:28rpx; }
.pass { background:rgba(255,255,255,0.9); }
.pass text { color:#111; }
.like { background:#2DD36F; }
.like text { color:#fff; }
.hi {
	margin-left: auto;
	background: #FFC629; border-radius:999rpx; padding:10rpx 18rpx;
}
.hi text { color:#111; font-size:20rpx; font-weight:700; }
.sent-row {
	display:flex; flex-direction:row; align-items:center;
	background:#FFF8E1; border-radius:20rpx; padding:16rpx; margin-bottom:14rpx;
	border: 1px solid rgba(255,198,41,0.25);
}
.avatar-wrap { position:relative; width:96rpx; height:96rpx; margin-right:16rpx; }
.avatar { width:96rpx; height:96rpx; border-radius:50%; }
.info { flex:1; min-width:0; }
.s-name { display:block; color:#111; font-size:28rpx; font-weight:700; margin-bottom:6rpx; }
.s-job { display:block; color:#888; font-size:22rpx; }
.hi-btn {
	background:#FFC629; border-radius:999rpx; padding:12rpx 20rpx;
}
.hi-btn text { color:#111; font-size:22rpx; font-weight:700; }
.hi-btn.outline {
	background: transparent;
	border: 1px solid rgba(255,198,41,0.8);
}
.hi-btn.outline text { color:#B8860B; }
.hi-btn.muted {
	background: #F0F0F0;
	border: none;
}
.hi-btn.muted text { color:#888; }
.empty { padding-top:80rpx; text-align:center; color:#777; }
.empty-title { display:block; color:#111; font-size:32rpx; font-weight:800; margin-bottom:8rpx; }
.empty-sub { display:block; color:#888; font-size:24rpx; }
</style>
