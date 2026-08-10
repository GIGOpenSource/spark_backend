<template>
	<view class="tabbar">
		<view
			v-for="(item, i) in tabs"
			:key="item.path"
			class="tab"
			:class="{ on: current === i }"
			@click="switchTab(i)"
		>
			<image class="ico" :src="current === i ? item.activeIcon : item.icon" mode="aspectFit" />
			<text class="label">{{ item.text }}</text>
			<view v-if="badge(i)" class="badge"><text>{{ badge(i) }}</text></view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { trackClick } from '@/utils/analytics.js'
import { getStoredTabBadges } from '@/utils/tabBadges.js'

const tabs = [
	{
		path: '/pages/discover/index',
		text: 'People',
		icon: '/static/tab/discover.png',
		activeIcon: '/static/tab/discover-active.png',
	},
	{
		path: '/pages/likes/index',
		text: 'Beeline',
		icon: '/static/tab/likes.png',
		activeIcon: '/static/tab/likes-active.png',
	},
	{
		path: '/pages/chat/index',
		text: 'Chats',
		icon: '/static/tab/chat.png',
		activeIcon: '/static/tab/chat-active.png',
	},
	{
		path: '/pages/me/index',
		text: 'Profile',
		icon: '/static/tab/me.png',
		activeIcon: '/static/tab/me-active.png',
	},
]

const current = ref(0)
const badges = ref({ likes: 0, chat: 0 })

function resolveIndex() {
	try {
		const pages = getCurrentPages()
		const page = pages && pages[pages.length - 1]
		const route = page && (page.route || '')
		const idx = tabs.findIndex((t) => route && t.path.replace(/^\//, '') === route)
		if (idx >= 0) current.value = idx
	} catch (e) {}
}

function loadBadges() {
	badges.value = getStoredTabBadges()
}

function badge(i) {
	if (i === 1 && badges.value.likes > 0) {
		return badges.value.likes > 99 ? '99+' : String(badges.value.likes)
	}
	if (i === 2 && badges.value.chat > 0) {
		return badges.value.chat > 99 ? '99+' : String(badges.value.chat)
	}
	return ''
}

function switchTab(i) {
	if (current.value === i) return
	const btnKeys = ['tab_discover', 'tab_likes', 'tab_chat', 'tab_me']
	trackClick(btnKeys[i] || `tab_${i}`)
	current.value = i
	uni.switchTab({ url: tabs[i].path })
}

function onBadgeEvent() {
	loadBadges()
}

function hideNativeTabBar() {
	try {
		uni.hideTabBar({ animation: false })
	} catch (e) {}
}

onMounted(() => {
	hideNativeTabBar()
	resolveIndex()
	loadBadges()
	uni.$on && uni.$on('tab_badges_updated', onBadgeEvent)
})

onShow(() => {
	hideNativeTabBar()
	resolveIndex()
	loadBadges()
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
	z-index: 999;
	display: flex;
	flex-direction: row;
	background: var(--bg, #FFFFFF);
	border-top: 1px solid rgba(0, 0, 0, 0.06);
	padding-bottom: env(safe-area-inset-bottom);
	height: calc(100rpx + env(safe-area-inset-bottom));
	box-sizing: content-box;
}
.tab {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	position: relative;
	padding-top: 10rpx;
}
.ico { width: 48rpx; height: 48rpx; }
.label {
	margin-top: 4rpx;
	font-size: 20rpx;
	color: #9B9B9B;
}
.tab.on .label { color: #111; font-weight: 700; }
.badge {
	position: absolute;
	top: 6rpx;
	right: 28%;
	min-width: 28rpx;
	height: 28rpx;
	padding: 0 8rpx;
	border-radius: 999rpx;
	background: #E74C3C;
	display: flex;
	align-items: center;
	justify-content: center;
}
.badge text { color: #fff; font-size: 18rpx; font-weight: 700; line-height: 1; }
</style>
