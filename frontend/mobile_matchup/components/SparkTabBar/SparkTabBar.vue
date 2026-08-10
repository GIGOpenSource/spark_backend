<template>
	<view class="tabbar" :style="{ paddingBottom: safeBottom + 'px' }">
		<view
			v-for="(item, index) in tabs"
			:key="item.path"
			class="tab"
			:class="{ on: current === index }"
			@click="switchTab(item, index)"
		>
			<view class="ico-wrap">
				<image
					class="ico"
					:src="current === index ? item.activeIcon : item.icon"
					mode="aspectFit"
				/>
				<view v-if="badgeText(index)" class="badge">
					<text>{{ badgeText(index) }}</text>
				</view>
			</view>
			<text class="label">{{ item.text }}</text>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { trackClick } from '@/utils/analytics.js'
import { getStoredTabBadges } from '@/utils/tabBadges.js'

const props = defineProps({
	current: { type: Number, default: 0 },
})

const badges = ref({ likes: 0, chat: 0 })
const safeBottom = ref(0)

const tabs = computed(() => [
	{
		path: '/pages/discover/index',
		text: '发现',
		icon: '/static/tab/discover.png',
		activeIcon: '/static/tab/discover-active.png',
	},
	{
		path: '/pages/likes/index',
		text: '喜欢',
		icon: '/static/tab/likes.png',
		activeIcon: '/static/tab/likes-active.png',
	},
	{
		path: '/pages/chat/index',
		text: '消息',
		icon: '/static/tab/chat.png',
		activeIcon: '/static/tab/chat-active.png',
	},
	{
		path: '/pages/me/index',
		text: '我',
		icon: '/static/tab/me.png',
		activeIcon: '/static/tab/me-active.png',
	},
])

function readBadges() {
	badges.value = getStoredTabBadges()
}

function badgeText(index) {
	if (index === 1 && badges.value.likes > 0) {
		return badges.value.likes > 99 ? '99+' : String(badges.value.likes)
	}
	if (index === 2 && badges.value.chat > 0) {
		return badges.value.chat > 99 ? '99+' : String(badges.value.chat)
	}
	return ''
}

function switchTab(item, index) {
	if (index === props.current) return
	const btnKeys = ['tab_discover', 'tab_likes', 'tab_chat', 'tab_me']
	trackClick(btnKeys[index] || `tab_${index}`)
	uni.switchTab({ url: item.path })
}

function hideNativeTabBar() {
	try {
		uni.hideTabBar({ animation: false })
	} catch (e) {}
}

onMounted(() => {
	hideNativeTabBar()
	try {
		const sys = uni.getSystemInfoSync() || {}
		safeBottom.value = sys.safeAreaInsets?.bottom || 0
	} catch (e) {
		safeBottom.value = 0
	}
	readBadges()
	uni.$on && uni.$on('tab_badges_updated', readBadges)
})

onShow(() => {
	hideNativeTabBar()
	readBadges()
})

onUnmounted(() => {
	uni.$off && uni.$off('tab_badges_updated', readBadges)
})
</script>

<style scoped>
.tabbar {
	position: fixed;
	left: 0; right: 0; bottom: 0;
	z-index: 999;
	display: flex; flex-direction: row;
	background: var(--card, #FFFFFF);
	border-top: 1px solid rgba(255,107,154,0.12);
	padding-top: 10rpx;
}
.tab {
	flex: 1;
	display: flex; flex-direction: column; align-items: center;
	padding: 6rpx 0 10rpx;
}
.ico-wrap { position: relative; width: 48rpx; height: 48rpx; margin-bottom: 4rpx; }
.ico { width: 48rpx; height: 48rpx; }
.badge {
	position: absolute; top: -10rpx; right: -18rpx;
	min-width: 28rpx; height: 28rpx; padding: 0 8rpx;
	border-radius: 999rpx; background: #FF4458;
	display: flex; align-items: center; justify-content: center;
}
.badge text { color: #fff; font-size: 18rpx; font-weight: 700; line-height: 1; }
.label { color: #B0A0A8; font-size: 20rpx; }
.tab.on .label { color: #FF6B9A; font-weight: 600; }
</style>
