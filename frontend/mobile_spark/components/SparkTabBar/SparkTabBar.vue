<template>
	<view class="tabbar" :style="barStyle">
		<view
			v-for="(tab, i) in tabs"
			:key="tab.path"
			class="tab"
			:class="{ on: props.current === i }"
			hover-class="tab-hover"
			@click.stop="switchTo(i)"
		>
			<view class="ico-wrap">
				<image class="ico" :src="props.current === i ? tab.activeIcon : tab.icon" mode="aspectFit" />
				<view class="badge" v-if="badgeFor(i)">
					<text>{{ badgeFor(i) }}</text>
				</view>
			</view>
			<text class="label">{{ tab.label }}</text>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStoredTabBadges } from '@/utils/tabBadges.js'
import { trackClick } from '@/utils/analytics.js'

const props = defineProps({
	current: { type: Number, default: 0 },
	badges: { type: Object, default: null },
})

const tabs = [
	{
		path: '/pages/discover/index',
		label: 'Discover',
		icon: '/static/tab/discover.png',
		activeIcon: '/static/tab/discover-active.png',
	},
	{
		path: '/pages/likes/index',
		label: 'Likes',
		icon: '/static/tab/likes.png',
		activeIcon: '/static/tab/likes-active.png',
	},
	{
		path: '/pages/chat/index',
		label: 'Chat',
		icon: '/static/tab/chat.png',
		activeIcon: '/static/tab/chat-active.png',
	},
	{
		path: '/pages/me/index',
		label: 'Me',
		icon: '/static/tab/me.png',
		activeIcon: '/static/tab/me-active.png',
	},
]

const stored = ref(getStoredTabBadges())

const barStyle = computed(() => ({
	background: 'var(--bg, #FFFFFF)',
	color: 'var(--text, #111111)',
}))

function badgeFor(i) {
	const src = props.badges || stored.value || {}
	let n = 0
	if (i === 1) n = Number(src.likes) || 0
	if (i === 2) n = Number(src.chat) || 0
	if (!n) return ''
	return n > 99 ? '99+' : String(n)
}

function currentRoute() {
	try {
		const pages = getCurrentPages()
		const page = pages && pages[pages.length - 1]
		return (page && page.route) || ''
	} catch (e) {
		return ''
	}
}

function switchTo(i) {
	if (i === props.current) return
	const target = tabs[i]
	if (!target) return
	const route = currentRoute()
	if (route && target.path.replace(/^\//, '') === route) return
	const btnKeys = ['tab_discover', 'tab_likes', 'tab_chat', 'tab_me']
	trackClick(btnKeys[i] || `tab_${i}`)
	uni.switchTab({
		url: target.path,
		fail: () => {},
	})
}

function hideNativeTabBar() {
	try {
		uni.hideTabBar({ animation: false, fail: () => {} })
	} catch (e) {}
}

function onBadgeEvent(payload) {
	if (payload && typeof payload === 'object') {
		stored.value = {
			likes: Number(payload.likes) || 0,
			chat: Number(payload.chat) || 0,
		}
	} else {
		stored.value = getStoredTabBadges()
	}
}

onMounted(() => {
	hideNativeTabBar()
	stored.value = getStoredTabBadges()
	uni.$on && uni.$on('tab_badges_updated', onBadgeEvent)
})
onShow(() => {
	hideNativeTabBar()
	stored.value = getStoredTabBadges()
})
onUnmounted(() => {
	uni.$off && uni.$off('tab_badges_updated', onBadgeEvent)
})
</script>

<style scoped>
.tabbar {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	z-index: 10050;
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: space-around;
	padding: 10rpx 8rpx calc(10rpx + env(safe-area-inset-bottom));
	border-top: 1px solid rgba(0,0,0,0.06);
	background: #FFFFFF;
	box-shadow: 0 -4rpx 20rpx rgba(0,0,0,0.04);
	/* Keep above native uni-tabbar while it finishes hiding */
	pointer-events: auto;
}
.tab {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 6rpx 0;
}
.tab-hover { opacity: 0.7; }
.ico-wrap { position: relative; width: 48rpx; height: 48rpx; }
.ico { width: 48rpx; height: 48rpx; pointer-events: none; }
.label {
	margin-top: 4rpx;
	font-size: 20rpx;
	color: #999;
}
.tab.on .label { color: #FF4458; font-weight: 600; }
.badge {
	position: absolute;
	top: -8rpx;
	right: -18rpx;
	min-width: 28rpx;
	height: 28rpx;
	padding: 0 8rpx;
	border-radius: 999rpx;
	background: #FF4458;
	display: flex;
	align-items: center;
	justify-content: center;
}
.badge text { color: #fff; font-size: 18rpx; font-weight: 700; line-height: 1; }
</style>
