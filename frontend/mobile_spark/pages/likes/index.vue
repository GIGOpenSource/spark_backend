<template>
	<view class="page">
		<view class="header">
			<text class="title spark-serif">Likes</text>
		</view>

		<view class="tabs">
			<view class="tab" :class="{ on: tab === 'received' }" @click="tab = 'received'">
				<text>Likes You</text>
				<text class="tab-count" v-if="count">{{ count }}</text>
			</view>
			<view class="tab" :class="{ on: tab === 'sent' }" @click="switchSent">
				<text>Sent</text>
			</view>
		</view>

		<template v-if="tab === 'received'">
			<view v-if="!unlocked" class="gold-banner" @click="openVip('need_gold')">
				<text class="banner-title">See who likes you with {{ goldName }}</text>
				<text class="banner-sub">{{ count || list.length }} likes waiting</text>
			</view>

			<view class="chips">
				<view class="chip" :class="{ on: sortMode === 'all' }" @click="setSort('all')"><text>All</text></view>
				<view class="chip" :class="{ on: sortMode === 'nearby' }" @click="setSort('nearby')"><text>Nearby</text></view>
				<view class="chip" :class="{ on: sortMode === 'common' }" @click="setSort('common')"><text>Common</text></view>
				<view class="chip" :class="{ on: sortMode === 'new' }" @click="setSort('new')"><text>New</text></view>
				<view class="chip" :class="{ on: sortMode === 'super' }" @click="setSort('super')"><text>Super</text></view>
				<view class="chip batch" v-if="unlocked && filteredList.length" @click="batchLike"><text>Like all</text></view>
			</view>
			<text class="quota-hint" v-if="canSayHi">Say Hi available with Platinum</text>
			<text class="quota-hint locked" v-else @click="openVip('need_platinum')">Say Hi · unlock with Platinum</text>

			<view class="grid">
				<view v-for="item in filteredList" :key="item.id || item.swipe_id" class="card" @click="open(item)">
					<image :src="item.avatar_url" class="img" mode="aspectFill" :class="{ blur: item.blur || !unlocked }" />
					<view class="lock-overlay" v-if="item.blur || !unlocked">
						<text class="lock-icon">🔒</text>
						<text class="lock-text">Tap to unlock</text>
					</view>
					<view class="online" v-if="item.is_online" />
					<view class="sl-badge" v-if="item.action === 'super_like'"><text>★</text></view>
					<template v-if="unlocked && !item.blur">
						<view class="footer">
							<text class="name">{{ displayName(item) }}</text>
							<view class="footer-actions" @click.stop>
								<view class="mini pass" @click="act(item, 'pass')"><text>×</text></view>
								<view class="mini like" @click="act(item, 'like')"><text>♥</text></view>
								<view class="hi" @click="onSayHiTap(item)"><text>{{ sayHiLabel }}</text></view>
							</view>
						</view>
					</template>
					<view v-else class="footer locked">
						<text class="name">Liked you</text>
					</view>
				</view>
			</view>
			<view v-if="loading" class="empty"><text class="empty-title">Loading…</text></view>
			<view v-else-if="!filteredList.length" class="empty">
				<text class="empty-title">No likes yet</text>
				<text class="empty-sub">Keep swiping to get more likes</text>
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
			<view v-if="sentLoading" class="empty"><text class="empty-title">Loading…</text></view>
			<view v-else-if="!sentList.length" class="empty"><text class="empty-title">No likes sent yet</text></view>
		</template>

		<VipSheet v-if="showVip" v-model:show="showVip" :reason="vipReason" @purchased="reloadCurrent" />
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
		<SparkTabBar :current="1" />
	</view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiLikesReceived, apiLikesSent, apiSayHi, apiLikesUnlock } from '@/api/likes.js'
import { apiSwipe } from '@/api/recommend.js'
import { track, trackClick } from '@/utils/analytics.js'
import { apiEntitlements } from '@/api/vip.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import MatchModal from '@/components/MatchModal/MatchModal.vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { tierDisplayName } from '@/utils/productProfile.js'

const TIER_RANK = { none: 0, plus: 1, gold: 2, platinum: 3 }

const tab = ref('received')
const list = ref([])
const sentList = ref([])
const unlocked = ref(false)
const count = ref(0)
const showVip = ref(false)
const vipReason = ref('need_gold')
const loading = ref(false)
const sentLoading = ref(false)
const sortMode = ref('all')
const canSayHi = ref(false)
const showMatch = ref(false)
const matchedUser = ref(null)
const matchedConversationId = ref(null)
const matchMeta = ref({ iAmOpener: null, expireAt: '', messagingMode: '' })
const goldName = tierDisplayName('gold')

const sayHiLabel = computed(() => (canSayHi.value ? 'Say Hi' : 'Say Hi 🔒'))

const filteredList = computed(() => list.value || [])

function setSort(mode) {
	sortMode.value = mode
	loadReceived()
}

function tierRank(t) {
	return TIER_RANK[t || 'none'] ?? 0
}

async function loadEntitlements() {
	try {
		const res = await apiEntitlements()
		const tier = (res.results && res.results.vip_tier) || 'none'
		canSayHi.value = tierRank(tier) >= tierRank('platinum')
	} catch (e) {
		const u = uni.getStorageSync('userInfo') || {}
		canSayHi.value = tierRank(u.vip_tier) >= tierRank('platinum')
	}
}

async function loadReceived() {
	loading.value = true
	try {
		const res = await apiLikesReceived(sortMode.value === 'online' ? 'all' : sortMode.value)
		list.value = (res.results && res.results.list) || []
		unlocked.value = !!(res.results && res.results.unlocked)
		count.value = (res.results && res.results.count) || list.value.length
		refreshTabBadges()
	} catch (e) {
		uni.showToast({ title: 'Failed to load likes', icon: 'none' })
	}
	loading.value = false
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
	loadEntitlements()
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
	if (item.blur || (!unlocked.value && !item._unlocked)) {
		if (item.swipe_id && !String(item.id).startsWith('funnel')) {
			uni.showActionSheet({
				itemList: ['Unlock this like', 'Get Gold'],
				success: async (r) => {
					if (r.tapIndex === 0) {
						try {
							await apiLikesUnlock(item.swipe_id)
							uni.showToast({ title: 'Unlocked', icon: 'none' })
							loadReceived()
						} catch (e) {
							openVip(e && e.message === 'need_likes_unlock' ? 'need_likes_unlock' : 'need_gold')
						}
					} else {
						openVip('need_gold')
					}
				},
			})
			return
		}
		openVip('need_gold')
		return
	}
	uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${item.id}` })
}

function openSent(item) {
	uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${item.id}` })
}

function sentStatus(item) {
	if (item.status === 'matched') return 'Matched · tap to chat'
	if (item.status === 'expired') return 'Like expired · like again'
	return item.job || 'Waiting for them'
}

function sentLabel(item) {
	if (item.is_matched) return 'Message'
	if (item.status === 'expired') return 'Like again'
	return canSayHi.value ? 'Say Hi' : 'Say Hi 🔒'
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

async function batchLike() {
	const rows = filteredList.value.filter((x) => unlocked.value && !x.blur && x.id && !String(x.id).startsWith('funnel'))
	if (!rows.length) {
		uni.showToast({ title: 'Nothing to like', icon: 'none' })
		return
	}
	uni.showModal({
		title: 'Like all?',
		content: `Send likes to ${rows.length} people in this list.`,
		success: async (m) => {
			if (!m.confirm) return
			let ok = 0
			for (const item of rows.slice(0, 20)) {
				try {
					await apiSwipe({ target_id: item.id, action: 'like' })
					list.value = list.value.filter((x) => x.id !== item.id)
					ok += 1
				} catch (e) {
					if (e && /need_|daily_like|limit/.test(e.message || '')) {
						openVip(e.message || 'need_vip')
						break
					}
				}
			}
			uni.showToast({ title: ok ? `Liked ${ok}` : 'Batch failed', icon: 'none' })
		}
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

function promptSayHi(item) {
	if (!canSayHi.value) {
		openVip('need_platinum')
		return
	}
	uni.showModal({
		title: 'Say Hi',
		content: '',
		editable: true,
		placeholderText: 'Write a short message…',
		confirmText: 'Send',
		cancelText: 'Cancel',
		success: (res) => {
			if (res.confirm) {
				const msg = (res.content || '').trim() || 'Hi!'
				sendSayHi(item, msg)
			}
		},
	})
}

function onSayHiTap(item) {
	trackClick('say_hi')
	promptSayHi(item)
}

async function sendSayHi(item, message) {
	try {
		const res = await apiSayHi({ target_id: item.id, message })
		const data = res.results || {}
		track('say_hi', { target_id: item.id, conversation_id: data.conversation_id || null })
		if (data.conversation_id) {
			uni.navigateTo({ url: `/pagesA/chat/room?id=${data.conversation_id}` })
		} else {
			uni.showToast({ title: 'Sent', icon: 'none' })
		}
	} catch (e) {
		if (e && (e.message === 'need_platinum' || (e.results && e.results.need_vip))) {
			openVip('need_platinum')
		} else {
			uni.showToast({ title: (e && e.message) || 'Say Hi failed', icon: 'none' })
		}
	}
}

async function onSentAction(item) {
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
	if (item.is_matched && item.conversation_id) {
		uni.navigateTo({ url: `/pagesA/chat/room?id=${item.conversation_id}` })
		return
	}
	if (item.is_matched) {
		promptSayHi(item)
		return
	}
	promptSayHi(item)
}

onShow(() => {
	loadEntitlements()
	if (tab.value === 'sent') loadSent()
	else loadReceived()
})
</script>

<style scoped>
.page { min-height:100vh; background:#FFFFFF; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 180rpx; }
.header { margin-bottom:12rpx; }
.title { display:block; color:#111; font-size:44rpx; font-weight:700; }
.spark-serif { font-family: inherit; }
.tabs {
	display:flex; flex-direction:row; background:#fff; border-radius:999rpx; padding:6rpx;
	margin-bottom:20rpx; border: 1px solid rgba(201,162,39,0.35);
}
.tab {
	flex:1; display:flex; flex-direction:row; align-items:center; justify-content:center;
	padding:16rpx 8rpx; border-radius:999rpx;
}
.tab.on { background: linear-gradient(90deg, #F5D76E, #C9A227); }
.tab text { color:#666; font-size:26rpx; font-weight:600; }
.tab.on text { color:#1A1A1A; font-weight:700; }
.tab-count {
	margin-left:8rpx; background:rgba(26,26,26,0.12); border-radius:999rpx;
	padding:2rpx 10rpx; font-size:20rpx !important;
}
.gold-banner {
	background: linear-gradient(135deg, #FFF6D6 0%, #FFE08A 55%, #F5D76E 100%);
	border: 1px solid rgba(201,162,39,0.45);
	border-radius: 24rpx;
	padding: 28rpx;
	margin-bottom: 20rpx;
}
.banner-title { display:block; color:#1A1A1A; font-size:30rpx; font-weight:700; margin-bottom:8rpx; }
.banner-sub { display:block; color:#8A6A00; font-size:24rpx; }
.chips { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom: 18rpx; }
.chip {
	background:#F3F0F7; border-radius:999rpx; padding:10rpx 20rpx; margin-right:10rpx; margin-bottom:8rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.chip.on { background:#1A1A1A; border-color:#1A1A1A; }
.chip text { color:#444; font-size:22rpx; }
.chip.on text { color:#fff; font-weight:600; }
.chip.batch { background: rgba(253,38,122,0.12); border-color: rgba(253,38,122,0.25); }
.chip.batch text { color:#FD267A; font-weight:600; }
.quota-hint {
	display:block; color:#666; font-size:22rpx; margin: -4rpx 4rpx 16rpx;
}
.quota-hint.locked { color:#FD267A; }
.grid { display:flex; flex-direction:row; flex-wrap:wrap; }
.card {
	width: 48%;
	margin-right: 4%;
	margin-bottom: 20rpx;
	border-radius: 24rpx;
	overflow: hidden;
	background: #FFFFFF;
	position: relative;
	box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.08);
}
.card:nth-child(2n) { margin-right: 0; }
.img { width:100%; height:420rpx; }
.img.blur { filter: blur(18px); transform: scale(1.1); }
.lock-overlay {
	position:absolute; left:0; right:0; top:0; bottom:0;
	background: rgba(255,255,255,0.55);
	display:flex; flex-direction:column; align-items:center; justify-content:center;
	z-index:2;
}
.lock-icon { font-size:36rpx; margin-bottom:8rpx; }
.lock-text { color:#111; font-size:22rpx; }
.online {
	position:absolute; left:16rpx; top:16rpx; width:18rpx; height:18rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #FFFFFF; z-index:3;
}
.sl-badge {
	position:absolute; right:16rpx; top:16rpx; z-index:3;
	width:44rpx; height:44rpx; border-radius:50%; background:#1DA1F2;
	display:flex; align-items:center; justify-content:center;
}
.sl-badge text { color:#fff; font-size:24rpx; }
.footer {
	position:absolute; left:0; right:0; bottom:0; z-index:3;
	padding: 16rpx;
	background: linear-gradient(to top, rgba(0,0,0,0.75), transparent);
}
.footer.locked {
	padding-bottom: 20rpx;
	background: linear-gradient(to top, rgba(0,0,0,0.88), rgba(0,0,0,0.35));
}
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
	background: linear-gradient(90deg, #1A1A1A, #333); border-radius:999rpx; padding:10rpx 18rpx;
	border: 1px solid rgba(245,215,110,0.7);
}
.hi text { color:#F5D76E; font-size:20rpx; font-weight:700; }
.sent-row {
	display:flex; flex-direction:row; align-items:center;
	background:#fff; border-radius:20rpx; padding:16rpx; margin-bottom:14rpx;
	border: 1px solid rgba(201,162,39,0.25);
}
.avatar-wrap { position:relative; width:96rpx; height:96rpx; margin-right:16rpx; }
.avatar { width:96rpx; height:96rpx; border-radius:50%; }
.info { flex:1; min-width:0; }
.s-name { display:block; color:#111; font-size:28rpx; font-weight:700; margin-bottom:6rpx; }
.s-job { display:block; color:#666; font-size:22rpx; }
.hi-btn {
	background: linear-gradient(90deg, #FF4B55, #FF6B75); border-radius:999rpx; padding:12rpx 20rpx;
}
.hi-btn text { color:#fff; font-size:22rpx; font-weight:600; }
.hi-btn.outline { background:#fff; border: 1px solid #FF4B55; }
.hi-btn.outline text { color:#FF4B55; }
.hi-btn.muted { opacity: 0.55; }
.empty { padding-top:80rpx; text-align:center; }
.empty-title { display:block; color:#111; font-size:32rpx; margin-bottom:12rpx; }
.empty-sub { display:block; color:#666; font-size:24rpx; }
</style>
