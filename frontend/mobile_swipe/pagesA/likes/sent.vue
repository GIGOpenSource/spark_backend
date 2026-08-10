<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Sent</text>
		</view>
		<view v-for="item in list" :key="item.swipe_id || item.id" class="row">
			<view class="avatar-wrap" @click="open(item)">
				<image :src="item.avatar_url" class="avatar" mode="aspectFill" />
				<view class="online" v-if="item.is_online" />
			</view>
			<view class="info" @click="open(item)">
				<text class="name">{{ item.nickname }} {{ item.age }}</text>
				<text class="job">{{ statusText(item) }}</text>
			</view>
			<view
				class="hi-btn"
				:class="{ outline: !item.is_matched, muted: !item.is_matched && item.status !== 'expired' }"
				@click="onAction(item)"
			>
				<text>{{ actionLabel(item) }}</text>
			</view>
		</view>
		<view v-if="!list.length" class="empty"><text>No likes sent yet</text></view>
		<VipSheet v-model:show="showVip" reason="need_vip" @purchased="load" />
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiLikesSent } from '@/api/likes.js'
import { apiSwipe } from '@/api/recommend.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'

const list = ref([])
const showVip = ref(false)

async function load() {
	try {
		const res = await apiLikesSent()
		list.value = (res.results && res.results.list) || []
	} catch (e) {
		list.value = []
		uni.showToast({ title: 'Failed to load', icon: 'none' })
	}
}

function statusText(item) {
	if (item.status === 'matched') return "It's a Match · tap to chat"
	if (item.status === 'expired') return 'Expired · like again'
	if (item.action === 'super_like') return 'Compliment sent · waiting'
	return 'Waiting for them'
}

function actionLabel(item) {
	if (item.is_matched) return 'Message'
	if (item.status === 'expired') return 'Like again'
	return 'Waiting'
}

function open(item) {
	uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${item.id}` })
}

async function onAction(item) {
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
			await load()
		} catch (e) {
			if (e && (e.message === 'daily_like_limit' || (e.results && e.results.need_vip))) {
				showVip.value = true
			} else {
				uni.showToast({ title: (e && e.message) || 'Like failed', icon: 'none' })
			}
		}
		return
	}
	uni.showToast({ title: 'Waiting for them to like you back', icon: 'none' })
}

function back() {
	uni.navigateBack()
}

onShow(load)
</script>

<style scoped>
.page { min-height:100vh; background:#FFFFFF; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { color:#111; font-size:40rpx; font-weight:800; }
.row {
	display:flex; flex-direction:row; align-items:center;
	background:#FFF8E1; border-radius:20rpx; padding:16rpx; margin-bottom:16rpx;
	border: 1px solid rgba(255,198,41,0.25);
}
.avatar-wrap { position:relative; margin-right:20rpx; }
.avatar { width:96rpx; height:96rpx; border-radius:50%; }
.online {
	position:absolute; right:2rpx; bottom:2rpx; width:18rpx; height:18rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #fff;
}
.info { flex:1; }
.name { color:#111; font-size:30rpx; display:block; font-weight:600; }
.job { color:#888; font-size:24rpx; }
.hi-btn {
	background:#FFC629; border-radius:999rpx; padding:14rpx 22rpx;
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
.empty { padding-top:80rpx; text-align:center; color:#888; }
</style>
