<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="hangup">‹</text>
			<text class="title">视频通话</text>
		</view>

		<view class="stage">
			<view class="remote">
				<text class="label">对方画面</text>
				<text class="hint">{{ remoteHint }}</text>
			</view>
			<view class="local">
				<text class="label">我</text>
			</view>
		</view>

		<view class="status-row">
			<text class="status">{{ statusText }}</text>
		</view>

		<view class="actions">
			<view class="hang" @click="hangup"><text>挂断</text></view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiCallToken, apiCallHangup } from '@/api/chat.js'

const cid = ref(null)
const statusText = ref('连接中…')
const remoteHint = ref('等待对方加入')
const callMeta = ref({})
let joined = false

onLoad((q) => {
	cid.value = q.cid || q.id || null
})

onMounted(async () => {
	if (!cid.value) {
		statusText.value = '缺少会话'
		return
	}
	try {
		const res = await apiCallToken(cid.value)
		const data = res.results || {}
		callMeta.value = data
		if (!data.ok && data.error) {
			statusText.value = data.error === 'agora_not_configured'
				? '视频通话未配置（Agora）'
				: (data.error || '获取 Token 失败')
			remoteHint.value = '可稍后在设置中配置后重试'
			return
		}
		statusText.value = '已获取通话凭证'
		await tryJoin(data)
	} catch (e) {
		statusText.value = (e && e.message) || '无法开始通话'
	}
})

onUnmounted(() => {
	tryLeave()
})

async function tryJoin(data) {
	try {
		if (typeof uni !== 'undefined' && typeof uni.$sparkAgoraJoin === 'function') {
			await uni.$sparkAgoraJoin({
				appId: data.app_id,
				token: data.token,
				channel: data.channel,
				uid: data.uid,
			})
			joined = true
			statusText.value = '通话中'
			remoteHint.value = '已连接 Agora'
			return
		}
	} catch (e) {
		statusText.value = 'Agora 加入失败'
		return
	}
	// #ifdef H5
	statusText.value = 'H5 需挂载 uni.$sparkAgoraJoin'
	remoteHint.value = '原生 / Web SDK 桥接后可显示画面'
	// #endif
	// #ifndef H5
	statusText.value = '请集成 Agora 原生插件'
	// #endif
}

function tryLeave() {
	try {
		if (joined && typeof uni !== 'undefined' && typeof uni.$sparkAgoraLeave === 'function') {
			uni.$sparkAgoraLeave()
		}
	} catch (e) {}
	joined = false
}

async function hangup() {
	tryLeave()
	if (cid.value) {
		try { await apiCallHangup(cid.value) } catch (e) {}
	}
	uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/chat/index' }) })
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: #120E10;
	padding: calc(env(safe-area-inset-top) + 16rpx) 24rpx calc(env(safe-area-inset-bottom) + 40rpx);
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
}
.header { display: flex; flex-direction: row; align-items: center; margin-bottom: 24rpx; }
.back { color: #fff; font-size: 48rpx; width: 60rpx; }
.title { color: #fff; font-size: 34rpx; font-weight: 700; }
.stage {
	flex: 1;
	position: relative;
	border-radius: 28rpx;
	overflow: hidden;
	background: #1C1518;
	min-height: 60vh;
}
.remote {
	width: 100%; height: 100%;
	display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.label { color: rgba(255,255,255,0.7); font-size: 26rpx; margin-bottom: 12rpx; }
.hint { color: rgba(255,255,255,0.45); font-size: 24rpx; }
.local {
	position: absolute; right: 24rpx; bottom: 24rpx;
	width: 200rpx; height: 280rpx; border-radius: 20rpx;
	background: #2A2024; border: 2rpx solid rgba(255,107,154,0.45);
	display: flex; align-items: center; justify-content: center;
}
.local .label { margin: 0; color: #FF6B9A; }
.status-row { padding: 28rpx 8rpx; text-align: center; }
.status { color: rgba(255,255,255,0.8); font-size: 26rpx; }
.actions { display: flex; justify-content: center; }
.hang {
	background: #FF4458; border-radius: 999rpx; padding: 28rpx 80rpx;
}
.hang text { color: #fff; font-weight: 700; font-size: 30rpx; }
</style>
