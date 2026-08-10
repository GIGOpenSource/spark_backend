<template>
	<view class="page">
		<view class="header">
			<text class="title display-font">{{ $t('likes.title') }}</text>
		</view>

		<view class="tabs">
			<view class="tab" :class="{ on: tab === 'received' }" @click="tab = 'received'; loadReceived()">
				<text>{{ $t('likes.received') }}</text>
				<text class="tab-count" v-if="count">{{ count }}</text>
			</view>
			<view class="tab" :class="{ on: tab === 'sent' }" @click="switchSent">
				<text>{{ $t('likes.sent') }}</text>
			</view>
		</view>

		<template v-if="tab === 'received'">
			<view v-if="!unlocked" class="gold-banner" @click="openVip('need_gold')">
				<text class="banner-title">开通{{ goldName }}，看看谁喜欢了你</text>
				<text class="banner-sub">{{ count || list.length }} 人喜欢了你</text>
			</view>

			<view class="qa-hint" v-if="qaGate">
				<text>配对后需「女问男答」再开聊 · 这里只负责互喜欢</text>
			</view>

			<view class="grid">
				<view v-for="item in list" :key="item.id || item.swipe_id" class="card" @click="open(item)">
					<image :src="item.avatar_url" class="img" mode="aspectFill" :class="{ blur: item.blur || !unlocked }" />
					<view class="lock-overlay" v-if="item.blur || !unlocked">
						<text class="lock-icon">🔒</text>
						<text class="lock-text">点击解锁</text>
					</view>
					<view class="online" v-if="item.is_online" />
					<view class="sl-badge" v-if="item.action === 'super_like'"><text>★</text></view>
					<template v-if="unlocked && !item.blur">
						<view class="footer">
							<text class="name">{{ displayName(item) }}</text>
							<text class="qa-foot" v-if="qaGate">配对后问答开聊</text>
							<view class="footer-actions" @click.stop>
								<view class="mini pass" @click="act(item, 'pass')"><text>×</text></view>
								<view class="mini like" @click="act(item, 'like')"><text>♥</text></view>
							</view>
						</view>
					</template>
					<view v-else class="footer locked">
						<text class="name">喜欢了你</text>
					</view>
				</view>
			</view>
			<view v-if="loading" class="empty"><text>{{ $t('common.loading') }}</text></view>
			<view v-else-if="!list.length" class="empty"><text>{{ $t('likes.emptyReceived') }}</text></view>
		</template>

		<template v-else>
			<view class="grid">
				<view v-for="item in sentList" :key="item.swipe_id || item.id" class="card" @click="openSent(item)">
					<image :src="item.avatar_url" class="img" mode="aspectFill" />
					<view class="online" v-if="item.is_online" />
					<view class="sl-badge" v-if="item.action === 'super_like'"><text>★</text></view>
					<view class="footer">
						<text class="name">{{ item.nickname }} {{ item.age || '' }}</text>
						<text class="qa-foot">{{ sentStatus(item) }}</text>
						<view class="footer-actions" @click.stop>
							<view class="sent-cta" :class="{ outline: !item.is_matched }" @click="onSentAction(item)">
								<text>{{ sentLabel(item) }}</text>
							</view>
						</view>
					</view>
				</view>
			</view>
			<view v-if="sentLoading" class="empty"><text>{{ $t('common.loading') }}</text></view>
			<view v-else-if="!sentList.length" class="empty"><text>{{ $t('likes.emptySent') }}</text></view>
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
import { ref } from 'vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { onShow } from '@dcloudio/uni-app'
import { apiLikesReceived, apiLikesSent } from '@/api/likes.js'
import { apiSwipe } from '@/api/recommend.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { trackClick } from '@/utils/analytics.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import MatchModal from '@/components/MatchModal/MatchModal.vue'
import { tierDisplayName, isQaGate } from '@/utils/productProfile.js'

const tab = ref('received')
const list = ref([])
const sentList = ref([])
const unlocked = ref(false)
const count = ref(0)
const showVip = ref(false)
const vipReason = ref('need_gold')
const loading = ref(false)
const sentLoading = ref(false)
const showMatch = ref(false)
const matchedUser = ref(null)
const matchedConversationId = ref(null)
const matchMeta = ref({ matchId: null, iAmOpener: null, expireAt: '', messagingMode: '' })
const goldName = tierDisplayName('gold')
const qaGate = isQaGate()

async function loadReceived() {
	loading.value = true
	try {
		const res = await apiLikesReceived()
		list.value = (res.results && res.results.list) || []
		unlocked.value = !!(res.results && res.results.unlocked)
		count.value = (res.results && res.results.count) || list.value.length
		refreshTabBadges()
	} catch (e) {
		uni.showToast({ title: '加载失败', icon: 'none' })
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
		uni.showToast({ title: '加载失败', icon: 'none' })
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
	if (item.blur || !unlocked.value) return '喜欢了你'
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
	if (item.status === 'matched') return '已配对 · 去问答开聊'
	if (item.status === 'expired') return '已过期 · 可再次喜欢'
	return '等待对方喜欢你'
}

function sentLabel(item) {
	if (item.is_matched) return '去开聊'
	if (item.status === 'expired') return '再次喜欢'
	return '等待中'
}

async function onSentAction(item) {
	if (item.is_matched && item.conversation_id) {
		const focus = matchMeta.value.messagingMode === 'qa_gate' || qaGate ? '&focus=qa' : ''
		uni.navigateTo({ url: `/pagesA/chat/room?id=${item.conversation_id}${focus}` })
		return
	}
	if (item.is_matched) {
		uni.switchTab({ url: '/pages/chat/index' })
		return
	}
	if (item.status === 'expired') {
		try {
			await apiSwipe({ target_id: item.id, action: 'like' })
			uni.showToast({ title: '已再次喜欢', icon: 'none' })
			await loadSent()
		} catch (e) {
			if (e && (e.message === 'daily_like_limit' || (e.results && e.results.need_vip))) {
				openVip(e.message || 'need_vip')
			} else {
				uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
			}
		}
	}
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
			uni.showToast({ title: '已喜欢', icon: 'none' })
		}
	} catch (e) {
		const msg = (e && e.message) || ''
		if (/need_|daily_like|limit/.test(msg) || (e && e.results && e.results.need_vip)) {
			openVip(msg || 'need_vip')
		} else {
			uni.showToast({ title: msg || '操作失败', icon: 'none' })
		}
	}
}

function goChat(payload) {
	showMatch.value = false
	const id = matchedConversationId.value
	const focusQa = !!(payload && (payload.focusAsk || payload.focus === 'qa'))
		|| !!(matchMeta.value && matchMeta.value.iAmOpener && (matchMeta.value.messagingMode === 'qa_gate' || qaGate))
	if (id) {
		uni.navigateTo({ url: `/pagesA/chat/room?id=${id}${focusQa ? '&focus=qa' : ''}` })
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
.page { min-height:100vh; background:#FFF7FA; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 160rpx; }
.header { margin-bottom:12rpx; }
.title { display:block; color:#222; font-size:44rpx; font-weight:700; }
.display-font { font-family: inherit; }
.tabs {
	display:flex; flex-direction:row; background:#fff; border-radius:999rpx; padding:6rpx;
	margin-bottom:20rpx; border: 1px solid rgba(255,107,154,0.2);
}
.tab {
	flex:1; display:flex; flex-direction:row; align-items:center; justify-content:center;
	padding:16rpx 8rpx; border-radius:999rpx;
}
.tab.on { background: linear-gradient(90deg, #FF6B9A, #FF8FB3); }
.tab text { color:#666; font-size:26rpx; font-weight:600; }
.tab.on text { color:#fff; }
.tab-count {
	margin-left:8rpx; background:rgba(255,255,255,0.25); border-radius:999rpx;
	padding:2rpx 10rpx; font-size:20rpx !important;
}
.gold-banner {
	background: linear-gradient(135deg, #FFE0EA 0%, #FFF0F5 100%);
	border: 1px solid rgba(255,107,154,0.35);
	border-radius: 24rpx;
	padding: 28rpx;
	margin-bottom: 16rpx;
}
.banner-title { display:block; color:#222; font-size:30rpx; font-weight:700; margin-bottom:8rpx; }
.banner-sub { display:block; color:#FF6B9A; font-size:24rpx; }
.qa-hint {
	background:#FFF; border-radius:16rpx; padding:16rpx 20rpx; margin-bottom:16rpx;
	border: 1px dashed rgba(255,107,154,0.4);
}
.qa-hint text { color:#FF6B9A; font-size:22rpx; }
.grid { display:flex; flex-direction:row; flex-wrap:wrap; }
.card {
	width: 48%;
	margin-right: 4%;
	margin-bottom: 20rpx;
	border-radius: 24rpx;
	overflow: hidden;
	background: #FFE8F0;
	position: relative;
}
.card:nth-child(2n) { margin-right: 0; }
.img { width:100%; height:420rpx; }
.img.blur { filter: blur(18px); transform: scale(1.1); }
.lock-overlay {
	position:absolute; left:0; right:0; top:0; bottom:0;
	background: rgba(255,255,255,0.28);
	display:flex; flex-direction:column; align-items:center; justify-content:center;
	z-index:2;
}
.lock-icon { font-size:36rpx; margin-bottom:8rpx; }
.lock-text { color:#222; font-size:22rpx; font-weight:600; }
.online {
	position:absolute; left:16rpx; top:16rpx; width:18rpx; height:18rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #fff; z-index:3;
}
.sl-badge {
	position:absolute; right:16rpx; top:16rpx; z-index:3;
	width:44rpx; height:44rpx; border-radius:50%; background:#FF6B9A;
	display:flex; align-items:center; justify-content:center;
}
.sl-badge text { color:#fff; font-size:24rpx; }
.footer {
	position:absolute; left:0; right:0; bottom:0; z-index:3;
	padding: 16rpx;
	background: linear-gradient(to top, rgba(0,0,0,0.75), transparent);
}
.footer.locked { padding-bottom: 20rpx; }
.name { display:block; color:#fff; font-size:26rpx; margin-bottom:8rpx; }
.qa-foot { display:block; color:rgba(255,255,255,0.85); font-size:18rpx; margin-bottom:10rpx; }
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
.sent-cta {
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3); border-radius:999rpx; padding:10rpx 18rpx;
}
.sent-cta text { color:#fff; font-size:22rpx; font-weight:600; }
.sent-cta.outline { background:rgba(255,255,255,0.92); }
.sent-cta.outline text { color:#FF6B9A; }
.empty { padding-top:80rpx; text-align:center; color:#777; }
</style>
