<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="hangup">‹</text>
			<text class="title">{{ $t('chat.videoCall') }}</text>
		</view>
		<view class="stage">
			<view class="remote">
				<image v-if="peerAvatar" :src="peerAvatar" class="peer-img" mode="aspectFill" />
				<view v-else class="peer-ph" />
				<text class="label">{{ peerName || 'Peer' }}</text>
				<text class="status">{{ statusText }}</text>
			</view>
			<view class="local">
				<image v-if="meAvatar" :src="meAvatar" class="me-img" mode="aspectFill" />
				<view v-else class="me-ph" />
				<text class="local-label">You</text>
			</view>
		</view>
		<text class="note" v-if="note">{{ note }}</text>
		<view class="actions">
			<view class="hang" @click="hangup"><text>{{ $t('chat.hangup') }}</text></view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiCallToken, apiCallHangup } from '@/api/chat.js'

const cid = ref(null)
const peerName = ref('')
const peerAvatar = ref('')
const meAvatar = ref((uni.getStorageSync('userInfo') || {}).avatar_url || '')
const statusText = ref('Connecting…')
const note = ref('')
const tokenData = ref(null)
let joined = false

onLoad((q) => {
	cid.value = q.cid || q.id
	peerName.value = q.name ? decodeURIComponent(q.name) : ''
	peerAvatar.value = q.avatar ? decodeURIComponent(q.avatar) : ''
})

onMounted(async () => {
	if (!cid.value) {
		statusText.value = 'Missing conversation'
		return
	}
	try {
		const res = await apiCallToken(cid.value)
		tokenData.value = res.results || {}
		statusText.value = 'Connected'
		const channel = tokenData.value.channel || `conv_${cid.value}`
		const token = tokenData.value.token || tokenData.value.rtc_token || ''
		const appId = tokenData.value.app_id || ''
		const uid = tokenData.value.uid || (uni.getStorageSync('userInfo') || {}).id
		// Hook for Agora Web / native SDK if registered by host app
		try {
			if (typeof uni !== 'undefined' && typeof uni.$sparkAgoraJoin === 'function') {
				await uni.$sparkAgoraJoin({ appId, channel, token, uid })
				joined = true
				note.value = ''
			} else {
				note.value = 'Agora SDK not linked — token ready. Register uni.$sparkAgoraJoin to join.'
			}
		} catch (e) {
			note.value = (e && e.message) || 'Failed to join RTC'
		}
	} catch (e) {
		statusText.value = (e && e.message) || 'Call failed'
		if (statusText.value.includes('agora_not_configured')) {
			note.value = 'Video calling is not configured on this server yet.'
		}
	}
})

onUnmounted(() => {
	cleanup()
})

async function cleanup() {
	try {
		if (typeof uni !== 'undefined' && typeof uni.$sparkAgoraLeave === 'function' && joined) {
			await uni.$sparkAgoraLeave()
		}
	} catch (e) {}
	if (cid.value) {
		try { await apiCallHangup(cid.value) } catch (e) {}
	}
}

async function hangup() {
	await cleanup()
	uni.navigateBack({ fail: () => uni.navigateBack() })
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: #111;
	color: #fff;
	display: flex;
	flex-direction: column;
}
.header {
	padding: calc(env(safe-area-inset-top) + 16rpx) 24rpx 16rpx;
	display: flex;
	flex-direction: row;
	align-items: center;
}
.back { color: #fff; font-size: 48rpx; width: 60rpx; }
.title { color: #fff; font-size: 32rpx; font-weight: 700; }
.stage { flex: 1; position: relative; margin: 16rpx 24rpx; }
.remote {
	width: 100%;
	height: 100%;
	border-radius: 28rpx;
	overflow: hidden;
	background: #1a1a1a;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}
.peer-img, .peer-ph {
	width: 200rpx; height: 200rpx; border-radius: 50%; margin-bottom: 24rpx;
}
.peer-ph { background: #333; }
.label { color: #fff; font-size: 36rpx; font-weight: 700; }
.status { color: #aaa; font-size: 24rpx; margin-top: 8rpx; }
.local {
	position: absolute;
	right: 24rpx;
	bottom: 24rpx;
	width: 200rpx;
	height: 280rpx;
	border-radius: 20rpx;
	overflow: hidden;
	background: #222;
	border: 2rpx solid rgba(255,198,41,0.6);
}
.me-img, .me-ph { width: 100%; height: 100%; }
.me-ph { background: #333; }
.local-label {
	position: absolute; left: 12rpx; bottom: 12rpx;
	color: #fff; font-size: 20rpx; background: rgba(0,0,0,0.45); padding: 4rpx 10rpx; border-radius: 8rpx;
}
.note {
	display: block;
	color: #FFC629;
	font-size: 22rpx;
	padding: 0 32rpx 16rpx;
	text-align: center;
}
.actions {
	padding: 24rpx 48rpx calc(env(safe-area-inset-bottom) + 40rpx);
}
.hang {
	background: #E74C3C;
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.hang text { color: #fff; font-weight: 800; font-size: 30rpx; }
</style>
