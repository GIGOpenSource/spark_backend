<template>
	<view class="page">
		<text class="title display-font">Chats</text>
		<input class="search" v-model="keyword" placeholder="Search matches & messages" placeholder-class="ph" />
		<text class="section" v-if="filteredMatches.length">New matches</text>
		<scroll-view scroll-x class="matches" v-if="filteredMatches.length">
			<view class="match" v-for="m in filteredMatches" :key="m.match_id" @click="openMatch(m)">
				<ExpireRing
					v-if="matchTimer(m)"
					:expire-at="m.expire_at"
					:now-ms="nowTick"
					:size="110"
					:thickness="7"
				>
					<image :src="m.user.avatar_url" class="m-avatar" mode="aspectFill" />
					<view class="online" v-if="m.user.is_online" />
				</ExpireRing>
				<view v-else class="m-avatar-wrap">
					<image :src="m.user.avatar_url" class="m-avatar" mode="aspectFill" />
					<view class="online" v-if="m.user.is_online" />
				</view>
				<text class="m-name">{{ m.user.nickname }}</text>
				<text class="m-timer" v-if="matchTimer(m)">{{ matchTimer(m) }}</text>
			</view>
		</scroll-view>
		<text class="section" v-if="filteredConversations.length">Messages</text>
		<view v-for="c in filteredConversations" :key="c.id" class="row" @click="openChat(c)">
			<view class="avatar-wrap">
				<ExpireRing
					v-if="c.waiting_for_opener && c.expire_at"
					:expire-at="c.expire_at"
					:now-ms="nowTick"
					:size="96"
					:thickness="6"
				>
					<image :src="c.user.avatar_url" class="avatar-inner" :class="{ blur: c.blur_peer }" mode="aspectFill" />
				</ExpireRing>
				<template v-else>
					<image :src="c.user.avatar_url" class="avatar" :class="{ blur: c.blur_peer }" mode="aspectFill" />
					<view class="online" v-if="c.user.is_online && !c.blur_peer" />
				</template>
			</view>
			<view class="info">
				<text class="name">{{ c.user.nickname }}</text>
				<text class="preview">{{ previewText(c) }}</text>
			</view>
			<view class="row-right">
				<text class="your-turn" v-if="c.your_turn && !c.waiting_for_opener">Your move</text>
				<view v-if="c.unread" class="badge"><text>{{ c.unread > 99 ? '99+' : c.unread }}</text></view>
			</view>
		</view>
		<view v-if="loading" class="empty">
			<text class="empty-title">Loading…</text>
		</view>
		<view v-else-if="!filteredConversations.length && !filteredMatches.length" class="empty">
			<text class="empty-title">{{ keyword ? 'No results' : 'Make the first move' }}</text>
			<text class="empty-sub" v-if="!keyword">Matches show up here — start chatting within 24h</text>
			<view class="empty-btn" v-if="!keyword" @click="goDiscover"><text>People</text></view>
		</view>
		<SparkTabBar />
	</view>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { onShow, onHide } from '@dcloudio/uni-app'
import { apiConversations } from '@/api/chat.js'
import { apiMatches } from '@/api/likes.js'
import { trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { formatExpireCountdown } from '@/utils/productProfile.js'
import { isZhUi } from '@/config/i18n.js'
import ExpireRing from '@/components/ExpireRing/ExpireRing.vue'

const conversations = ref([])
const matches = ref([])
const keyword = ref('')
const loading = ref(false)
const nowTick = ref(Date.now())
let tickTimer = null
let lastLoadAt = 0
const LOAD_THROTTLE_MS = 30000

const zh = computed(() => isZhUi())

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
	if (!m || m.opened_at || m.messaging_mode !== 'women_first') return ''
	const exp = m.expire_at
	if (!exp) return ''
	return formatExpireCountdown(exp, nowTick.value)
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
		uni.showToast({ title: zh.value ? '加载失败' : 'Failed to load chats', icon: 'none' })
	}
	loading.value = false
}

function previewText(c) {
	if (c.waiting_for_opener) {
		const left = c.expire_at ? formatExpireCountdown(c.expire_at, nowTick.value) : ''
		if (zh.value) return left ? `等她先开口 · ${left}` : '等她先开口…'
		return left ? `Waiting for her · ${left}` : 'Waiting for her to move first…'
	}
	const prefix = c.is_prematch ? ((c.blur_peer ? (zh.value ? '有人打招呼' : 'Someone said hi') : (zh.value ? '打招呼' : 'Say Hi')) + ' · ') : ''
	const t = c.last_message || (zh.value ? '打个招呼' : 'Say hi')
	if (t === '[image]' || t === '[photo]' || t === '[图片]') return prefix + (zh.value ? '[图片]' : '[Photo]')
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
.page { min-height:100vh; background: var(--bg, #FFFFFF); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 160rpx; }
.title { display:block; color:#111; font-size:44rpx; font-weight:800; margin-bottom:16rpx; font-family: 'Montserrat', sans-serif; }
.section {
	display:block; color:#888; font-size:22rpx; letter-spacing:1rpx;
	text-transform:uppercase; margin: 8rpx 4rpx 14rpx;
}
.search {
	background:#F5F5F5; border-radius:999rpx; padding:18rpx 28rpx; color:#111; margin-bottom:20rpx; font-size:26rpx;
}
.ph { color:#666; }
.matches { white-space: nowrap; margin-bottom: 24rpx; }
.match { display:inline-block; width:140rpx; margin-right:16rpx; text-align:center; }
.m-avatar-wrap { position:relative; width:110rpx; height:110rpx; margin:0 auto; }
.m-avatar { width:100%; height:100%; border-radius:50%; }
.m-name { display:block; color:#111; font-size:22rpx; margin-top:8rpx; overflow:hidden; }
.m-timer { display:block; color:#B8860B; font-size:18rpx; margin-top:2rpx; font-weight:700; }
.row {
	display:flex; flex-direction:row; align-items:center;
	padding:20rpx 0; border-bottom:1px solid rgba(0,0,0,0.06);
}
.avatar-wrap { position:relative; margin-right:20rpx; width:96rpx; height:96rpx; }
.avatar { width:96rpx; height:96rpx; border-radius:50%; }
.avatar-inner { width:100%; height:100%; border-radius:50%; }
.avatar.blur, .avatar-inner.blur { filter: blur(10px); }
.online {
	position:absolute; right:2rpx; bottom:2rpx; width:18rpx; height:18rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #fff; z-index:2;
}
.info { flex:1; overflow:hidden; }
.name { color:#111; font-size:30rpx; display:block; font-weight:700; }
.preview {
	color:#888; font-size:24rpx; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:460rpx;
}
.row-right { display:flex; flex-direction:column; align-items:flex-end; margin-left: 12rpx; }
.your-turn {
	color:#B8860B; font-size:20rpx; font-weight:800; margin-bottom: 8rpx;
}
.badge {
	min-width:36rpx; height:36rpx; border-radius:18rpx; background:#FFC629;
	display:flex; align-items:center; justify-content:center; padding:0 10rpx;
}
.badge text { color:#111; font-size:20rpx; }
.empty { padding-top:100rpx; text-align:center; }
.empty-title { display:block; color:#111; font-size:32rpx; margin-bottom:12rpx; }
.empty-sub { display:block; color:#777; font-size:24rpx; margin-bottom:28rpx; }
.empty-btn {
	display:inline-block; background:#FFC629; border-radius:999rpx; padding:18rpx 40rpx;
}
.empty-btn text { color:#111; font-weight:600; }
</style>
