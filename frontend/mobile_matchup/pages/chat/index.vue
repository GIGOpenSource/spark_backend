<template>
	<view class="page">
		<text class="title">{{ $t('chat.title') }}</text>
		<input class="search" v-model="keyword" :placeholder="$t('chat.search')" placeholder-class="ph" />
		<text class="section" v-if="filteredMatches.length">{{ $t('chat.newMatches') }}</text>
		<scroll-view scroll-x class="matches" v-if="filteredMatches.length">
			<view class="match" v-for="m in filteredMatches" :key="m.match_id" @click="openMatch(m)">
				<ExpiryRing
					:progress="matchProgress(m)"
					:size="122"
					:stroke="6"
				>
					<view class="m-avatar-inner">
						<image :src="m.user.avatar_url" class="m-avatar" mode="aspectFill" />
						<view class="online" v-if="m.user.is_online" />
						<view class="qa-dot" v-if="m.qa_gate_pending" />
					</view>
				</ExpiryRing>
				<text class="m-name">{{ m.user.nickname }}</text>
				<text class="m-timer" v-if="matchTimer(m)">{{ matchTimer(m) }}</text>
			</view>
		</scroll-view>
		<text class="section" v-if="filteredConversations.length">{{ $t('chat.conversations') }}</text>
		<view v-for="c in filteredConversations" :key="c.id" class="row" @click="openChat(c)">
			<ExpiryRing
				v-if="showConvRing(c)"
				:progress="convProgress(c)"
				:size="108"
				:stroke="5"
			>
				<view class="avatar-inner">
					<image :src="c.user.avatar_url" class="avatar" :class="{ blur: c.blur_peer }" mode="aspectFill" />
					<view class="online" v-if="c.user.is_online && !c.blur_peer" />
					<view class="qa-dot" v-if="c.qa_gate_pending" />
				</view>
			</ExpiryRing>
			<view v-else class="avatar-wrap">
				<image :src="c.user.avatar_url" class="avatar" :class="{ blur: c.blur_peer }" mode="aspectFill" />
				<view class="online" v-if="c.user.is_online && !c.blur_peer" />
				<view class="qa-dot" v-if="c.qa_gate_pending" />
			</view>
			<view class="info">
				<text class="name">{{ c.user.nickname }}</text>
				<text class="preview">{{ previewText(c) }}</text>
			</view>
			<view class="row-right">
				<text class="your-turn" v-if="c.your_turn && !c.waiting_for_opener && !c.qa_gate_pending">{{ $t('chat.yourTurn') }}</text>
				<text class="your-turn qa" v-else-if="c.qa_gate_pending">{{ $t('chat.qaPending') }}</text>
				<view v-if="c.unread" class="badge"><text>{{ c.unread > 99 ? '99+' : c.unread }}</text></view>
			</view>
		</view>
		<view v-if="loading" class="empty">
			<text class="empty-title">{{ $t('common.loading') }}</text>
		</view>
		<view v-else-if="!filteredConversations.length && !filteredMatches.length" class="empty">
			<text class="empty-title">{{ keyword ? '没有结果' : $t('chat.empty') }}</text>
			<text class="empty-sub" v-if="!keyword">{{ $t('chat.emptySub') }}</text>
			<view class="empty-btn" v-if="!keyword" @click="goDiscover"><text>{{ $t('chat.goDiscover') }}</text></view>
		</view>
		<SparkTabBar :current="2" />
	</view>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { onShow, onHide } from '@dcloudio/uni-app'
import { apiConversations } from '@/api/chat.js'
import { apiMatches } from '@/api/likes.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { trackClick } from '@/utils/analytics.js'
import { formatExpireCountdown, expireProgress, matchOpenHours } from '@/utils/productProfile.js'
import ExpiryRing from '@/components/ExpiryRing/ExpiryRing.vue'

const conversations = ref([])
const matches = ref([])
const keyword = ref('')
const loading = ref(false)
const nowTick = ref(Date.now())
let tickTimer = null
let lastLoadAt = 0
const LOAD_THROTTLE_MS = 30000

const filteredConversations = computed(() => {
	const k = keyword.value.trim().toLowerCase()
	if (!k) return conversations.value
	return conversations.value.filter((c) => {
		const name = (c.user && c.user.nickname) || ''
		const msg = c.last_message || ''
		return name.toLowerCase().includes(k) || msg.toLowerCase().includes(k)
	})
})

const filteredMatches = computed(() => {
	const k = keyword.value.trim().toLowerCase()
	if (!k) return matches.value
	return matches.value.filter((m) => ((m.user && m.user.nickname) || '').toLowerCase().includes(k))
})

function matchTimer(m) {
	if (!m || m.opened_at) return ''
	if (m.messaging_mode !== 'women_first' && m.messaging_mode !== 'qa_gate') return ''
	if (m.messaging_mode === 'qa_gate' && m.qa && m.qa.status === 'approved') return ''
	const exp = m.expire_at
	if (!exp) return ''
	return formatExpireCountdown(exp, nowTick.value)
}

function matchProgress(m) {
	if (!matchTimer(m)) return 0
	return expireProgress(m.expire_at, nowTick.value, matchOpenHours() || 48)
}

function showConvRing(c) {
	if (!c || !c.expire_at) return false
	if (c.opened_at) return false
	const qaPending = !!(c.qa_gate_pending || (c.qa && c.qa.status && c.qa.status !== 'approved' && c.qa.status !== 'expired'))
	return qaPending || (c.messaging_mode === 'qa_gate' && !c.opened_at)
}

function convProgress(c) {
	if (!showConvRing(c)) return 0
	return expireProgress(c.expire_at, nowTick.value, matchOpenHours() || 48)
}

async function load(force = false) {
	const now = Date.now()
	if (!force && lastLoadAt && now - lastLoadAt < LOAD_THROTTLE_MS && conversations.value.length) {
		return
	}
	loading.value = true
	try {
		const [c, m] = await Promise.all([apiConversations(), apiMatches()])
		conversations.value = (c.results && c.results.list) || []
		matches.value = (m.results && m.results.list) || []
		lastLoadAt = Date.now()
		refreshTabBadges()
	} catch (e) {
		uni.showToast({ title: '加载失败', icon: 'none' })
	}
	loading.value = false
}

function previewText(c) {
	if (c.messaging_mode === 'qa_gate' && c.qa && c.qa.status && c.qa.status !== 'approved') {
		if (c.qa.status === 'expired') return '缘分已到期'
		const left = c.expire_at ? formatExpireCountdown(c.expire_at, nowTick.value) : ''
		const st = c.qa.status
		let tip = '问答进行中'
		if (st === 'need_question') tip = c.qa.can_ask ? '请出题' : '等她出题'
		else if (st === 'need_answer') tip = c.qa.can_answer ? '请回答' : '等他回答'
		else if (st === 'need_review') tip = c.qa.can_review ? '请审阅' : '等她审阅'
		return left ? `${tip} · ${left}` : tip
	}
	// qa_gate: skip women_first waiting copy
	if (c.messaging_mode === 'qa_gate') {
		const t = c.last_message || '打个招呼'
		if (t === '[image]' || t === '[photo]' || t === '[图片]') return '[图片]'
		if (t === '[voice]' || t === '[语音]') return '[语音]'
		return t
	}
	if (c.waiting_for_opener) {
		const left = c.expire_at ? formatExpireCountdown(c.expire_at, nowTick.value) : ''
		return left ? `等待开聊 · ${left}` : '等待开聊…'
	}
	const prefix = c.is_prematch ? ((c.blur_peer ? '有人打招呼' : '打招呼') + ' · ') : ''
	const t = c.last_message || '打个招呼'
	if (t === '[image]' || t === '[photo]' || t === '[图片]') return prefix + '[图片]'
	if (t === '[voice]' || t === '[语音]') return prefix + '[语音]'
	return prefix + t
}

function openChat(c) {
	trackClick('open_room')
	uni.navigateTo({ url: `/pagesA/chat/room?id=${c.id}` })
}
function openMatch(m) {
	trackClick('open_room')
	if (m.conversation_id) {
		uni.navigateTo({ url: `/pagesA/chat/room?id=${m.conversation_id}` })
	} else {
		uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${m.user.id}` })
	}
}
function goDiscover() {
	uni.switchTab({ url: '/pages/discover/index' })
}

onShow(() => {
	load()
	if (tickTimer) clearInterval(tickTimer)
	tickTimer = setInterval(() => { nowTick.value = Date.now() }, 1000)
})
onHide(() => {
	if (tickTimer) clearInterval(tickTimer)
	tickTimer = null
})
onUnmounted(() => {
	if (tickTimer) clearInterval(tickTimer)
})
</script>

<style scoped>
.page { min-height:100vh; background:#FFF7FA; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 160rpx; }
.title { display:block; color:#222; font-size:44rpx; font-weight:700; margin-bottom:16rpx; }
.section {
	display:block; color:#888; font-size:22rpx; letter-spacing:1rpx;
	margin: 8rpx 4rpx 14rpx;
}
.search {
	background:#FFFFFF; border-radius:999rpx; padding:18rpx 28rpx; color:#222; margin-bottom:20rpx; font-size:26rpx;
}
.ph { color:#666; }
.matches { white-space: nowrap; margin-bottom: 24rpx; }
.match { display:inline-flex; flex-direction:column; align-items:center; width:140rpx; margin-right:16rpx; text-align:center; }
.m-avatar-inner { position:relative; width:110rpx; height:110rpx; }
.m-avatar { width:110rpx; height:110rpx; border-radius:50%; }
.qa-dot {
	position:absolute; left:2rpx; top:2rpx; width:16rpx; height:16rpx;
	border-radius:50%; background:#FFC629; border:3rpx solid #FFF7FA; z-index:2;
}
.m-name { display:block; color:#222; font-size:22rpx; margin-top:8rpx; overflow:hidden; }
.m-timer { display:block; color:#FFC629; font-size:18rpx; margin-top:2rpx; }
.row {
	display:flex; flex-direction:row; align-items:center;
	padding:20rpx 0; border-bottom:1px solid rgba(255,107,154,0.12);
}
.avatar-wrap { position:relative; margin-right:20rpx; width:96rpx; height:96rpx; }
.avatar-inner { position:relative; width:96rpx; height:96rpx; }
.avatar { width:96rpx; height:96rpx; border-radius:50%; }
.avatar.blur { filter: blur(10px); }
.online {
	position:absolute; right:2rpx; bottom:2rpx; width:18rpx; height:18rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #FFF7FA;
}
.info { flex:1; overflow:hidden; margin-left: 12rpx; }
.name { color:#222; font-size:30rpx; display:block; }
.preview {
	color:#888; font-size:24rpx; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:420rpx;
}
.row-right { display:flex; flex-direction:column; align-items:flex-end; margin-left: 12rpx; }
.your-turn {
	color:#FF6B9A; font-size:20rpx; font-weight:800; margin-bottom: 8rpx;
}
.your-turn.qa { color:#C9A000; }
.badge {
	min-width:36rpx; height:36rpx; border-radius:18rpx; background:#FF6B9A;
	display:flex; align-items:center; justify-content:center; padding:0 10rpx;
}
.badge text { color:#fff; font-size:20rpx; }
.empty { padding-top:100rpx; text-align:center; }
.empty-title { display:block; color:#222; font-size:32rpx; margin-bottom:12rpx; }
.empty-sub { display:block; color:#777; font-size:24rpx; margin-bottom:28rpx; }
.empty-btn {
	display:inline-block; background:#FF6B9A; border-radius:999rpx; padding:18rpx 40rpx;
}
.empty-btn text { color:#fff; font-weight:600; }
</style>
