<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title spark-serif">发出的喜欢</text>
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
				:class="{ outline: !item.is_matched, disabled: false }"
				@click="onAction(item)"
			>
				<text>{{ actionLabel(item) }}</text>
			</view>
		</view>
		<view v-if="!list.length" class="empty"><text>还没有发出的喜欢</text></view>
		<VipSheet v-model:show="showVip" reason="need_platinum" @purchased="load" />
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiLikesSent, apiSayHi } from '@/api/likes.js'
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
	if (item.status === 'matched') return 'Matched · tap to chat'
	if (item.status === 'expired') return 'Like expired · like again'
	return item.job || 'Waiting for them'
}

function actionLabel(item) {
	if (item.is_matched) return 'Message'
	if (item.status === 'expired') return 'Like again'
	return 'Say Hi 🔒'
}

function open(item) {
	uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${item.id}` })
}

async function onAction(item) {
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
	await sayHi(item)
}

async function sayHi(item) {
	if (item.is_matched && item.conversation_id) {
		uni.navigateTo({ url: `/pagesA/chat/room?id=${item.conversation_id}` })
		return
	}
	if (item.is_matched) {
		try {
			const res = await apiSayHi({ target_id: item.id, message: 'Hi!' })
			const cid = res.results && res.results.conversation_id
			if (cid) uni.navigateTo({ url: `/pagesA/chat/room?id=${cid}` })
		} catch (e) {
			if (e && (e.message === 'need_platinum' || (e.results && e.results.need_vip))) {
				showVip.value = true
			} else {
				uni.showToast({ title: (e && e.message) || 'Say Hi failed', icon: 'none' })
			}
		}
		return
	}
	try {
		const res = await apiSayHi({ target_id: item.id, message: 'Hi!' })
		uni.showToast({ title: 'Say Hi sent', icon: 'none' })
		if (res.results && res.results.conversation_id) {
			uni.navigateTo({ url: `/pagesA/chat/room?id=${res.results.conversation_id}` })
		}
	} catch (e) {
		if (e && (e.message === 'need_platinum' || (e.results && e.results.need_vip))) {
			showVip.value = true
		} else {
			uni.showToast({ title: (e && e.message) || 'Say Hi failed', icon: 'none' })
		}
	}
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
.title { color:#111; font-size:40rpx; font-weight:700; }
.spark-serif { font-family: 'Playfair Display', 'Times New Roman', serif; }
.row {
	display:flex; flex-direction:row; align-items:center;
	background:#FFFFFF; border-radius:20rpx; padding:16rpx; margin-bottom:16rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.avatar-wrap { position:relative; margin-right:20rpx; }
.avatar { width:96rpx; height:96rpx; border-radius:50%; }
.online {
	position:absolute; right:2rpx; bottom:2rpx; width:18rpx; height:18rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #FFFFFF;
}
.info { flex:1; }
.name { color:#111; font-size:30rpx; display:block; }
.job { color:#666; font-size:24rpx; }
.hi-btn {
	background:#FF6B9A; border-radius:999rpx; padding:14rpx 22rpx;
}
.hi-btn text { color:#fff; font-size:22rpx; font-weight:600; }
.hi-btn.outline {
	background: transparent;
	border: 1px solid rgba(255,107,154,0.7);
}
.hi-btn.outline text { color:#FF6B9A; }
.hi-btn.disabled { opacity: 0.45; border-color: #ccc; background: #F3F0F7; }
.hi-btn.disabled text { color:#999; }
.empty { padding-top:80rpx; text-align:center; color:#666; }
</style>
