<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="hangup">‹</text>
			<text class="title">Video call</text>
		</view>

		<view class="stage">
			<view class="remote">
				<view class="placeholder">
					<text class="ph-label">Remote</text>
					<text class="ph-sub" v-if="status">{{ status }}</text>
					<text class="ph-sub" v-else>Waiting for peer…</text>
				</view>
			</view>
			<view class="local">
				<view class="placeholder small">
					<text class="ph-label">You</text>
				</view>
			</view>
		</view>

		<view class="meta" v-if="channel">
			<text class="meta-line">Channel: {{ channel }}</text>
			<text class="meta-line" v-if="mock">Agora mock — tokens work for wiring UI</text>
		</view>

		<!-- #ifdef H5 -->
		<view class="hint-box">
			<text>H5: hook Agora Web SDK via uni.$sparkAgoraJoin(tokenPayload)</text>
		</view>
		<!-- #endif -->

		<view class="actions">
			<view class="hang" @click="hangup"><text>Hang up</text></view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiCallToken, apiCallHangup } from '@/api/chat.js'

const cid = ref(null)
const status = ref('Connecting…')
const channel = ref('')
const token = ref('')
const appId = ref('')
const mock = ref(false)
let hungUp = false

onLoad((q) => {
	cid.value = q.cid || q.id
})

onMounted(async () => {
	if (!cid.value) {
		status.value = 'Missing conversation'
		return
	}
	try {
		const res = await apiCallToken(cid.value)
		const d = res.results || {}
		channel.value = d.channel || `conv_${cid.value}`
		token.value = d.token || d.rtc_token || ''
		appId.value = d.app_id || d.appId || ''
		mock.value = !!d.mock
		status.value = mock.value ? 'Connected (mock)' : 'Connected'
		const payload = {
			conversation_id: cid.value,
			channel: channel.value,
			token: token.value,
			app_id: appId.value,
			uid: d.uid || (uni.getStorageSync('userInfo') || {}).id,
			mock: mock.value,
		}
		// #ifdef H5
		try {
			if (typeof uni !== 'undefined' && typeof uni.$sparkAgoraJoin === 'function') {
				await uni.$sparkAgoraJoin(payload)
				status.value = 'Joined via Agora Web SDK'
			}
		} catch (e) {
			status.value = 'Token ready · SDK hook failed'
		}
		// #endif
	} catch (e) {
		status.value = (e && e.message) || 'Call failed'
		uni.showToast({ title: status.value, icon: 'none' })
	}
})

onUnmounted(() => {
	if (!hungUp) hangup(true)
})

async function hangup(silent) {
	if (hungUp) {
		if (!silent) uni.navigateBack()
		return
	}
	hungUp = true
	try {
		if (cid.value) await apiCallHangup(cid.value)
	} catch (e) {}
	// #ifdef H5
	try {
		if (typeof uni !== 'undefined' && typeof uni.$sparkAgoraLeave === 'function') {
			await uni.$sparkAgoraLeave()
		}
	} catch (e) {}
	// #endif
	if (!silent) {
		uni.navigateBack({ fail: () => {} })
	}
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: #0B0B0F;
	padding: calc(env(safe-area-inset-top) + 16rpx) 24rpx calc(env(safe-area-inset-bottom) + 40rpx);
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
}
.header {
	display: flex;
	flex-direction: row;
	align-items: center;
	margin-bottom: 24rpx;
}
.back { color: #fff; font-size: 48rpx; width: 60rpx; }
.title { color: #fff; font-size: 34rpx; font-weight: 700; }
.stage {
	flex: 1;
	position: relative;
	border-radius: 28rpx;
	overflow: hidden;
	background: #1A1A22;
	min-height: 60vh;
}
.remote { width: 100%; height: 100%; min-height: 60vh; }
.local {
	position: absolute;
	right: 24rpx;
	bottom: 24rpx;
	width: 220rpx;
	height: 300rpx;
	border-radius: 20rpx;
	overflow: hidden;
	border: 2rpx solid rgba(255,255,255,0.35);
	background: #2A2A35;
}
.placeholder {
	width: 100%;
	height: 100%;
	min-height: 60vh;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}
.placeholder.small { min-height: 0; }
.ph-label { color: #fff; font-size: 32rpx; font-weight: 700; }
.ph-sub { color: rgba(255,255,255,0.65); font-size: 24rpx; margin-top: 12rpx; }
.meta { margin-top: 20rpx; }
.meta-line { display: block; color: rgba(255,255,255,0.55); font-size: 22rpx; margin-bottom: 6rpx; }
.hint-box {
	margin-top: 16rpx;
	padding: 16rpx 20rpx;
	border-radius: 16rpx;
	background: rgba(255,68,88,0.15);
}
.hint-box text { color: #FF8A96; font-size: 22rpx; }
.actions { margin-top: 32rpx; }
.hang {
	background: #FF4458;
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.hang text { color: #fff; font-weight: 700; font-size: 30rpx; }
</style>
