<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">{{ $t('me.verify') }}</text>
		</view>

		<view class="hero">
			<view class="badge" :class="statusClass"><text>{{ statusLabel }}</text></view>
			<text class="lead">通过认证后资料页会显示粉色勾，更容易被信任</text>
		</view>

		<view class="card">
			<text class="sec">认证说明</text>
			<text class="body">按提示完成自拍比对。审核通过后不可伪造头像。</text>
		</view>

		<view class="btn" :class="{ busy: busy }" @click="start">
			<text>{{ busy ? '启动中…' : (status === 'approved' ? '已通过认证' : '开始认证') }}</text>
		</view>

		<view class="sandbox" v-if="showSandbox">
			<text class="sec">沙箱调试</text>
			<view class="row">
				<view class="mini ok" @click="decide(true)"><text>模拟通过</text></view>
				<view class="mini no" @click="decide(false)"><text>模拟拒绝</text></view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiVerifyStart, apiVerifyStatus, apiVerifySandboxDecide } from '@/api/verify.js'

const status = ref('none')
const busy = ref(false)
const showSandbox = ref(false)

const statusLabel = computed(() => {
	const map = {
		none: '未认证',
		pending: '审核中',
		approved: '已认证',
		rejected: '未通过',
	}
	return map[status.value] || status.value || '未认证'
})

const statusClass = computed(() => {
	if (status.value === 'approved') return 'ok'
	if (status.value === 'pending') return 'wait'
	if (status.value === 'rejected') return 'bad'
	return ''
})

onMounted(load)

async function load() {
	try {
		const res = await apiVerifyStatus()
		const data = res.results || {}
		status.value = data.status || data.verify_status || 'none'
		showSandbox.value = !!data.sandbox || !!data.can_sandbox
		const boot = uni.getStorageSync('bootstrap') || {}
		if (boot.features && boot.features.persona_configured === false) {
			showSandbox.value = true
		}
	} catch (e) {}
}

function openHosted(url) {
	if (!url) return
	// #ifdef H5
	if (typeof window !== 'undefined') {
		window.open(url, '_blank')
		return
	}
	// #endif
	// #ifdef APP-PLUS
	try {
		if (typeof plus !== 'undefined' && plus.runtime && plus.runtime.openURL) {
			plus.runtime.openURL(url)
			return
		}
	} catch (e) {}
	// #endif
	uni.navigateTo({
		url: `/pagesA/me/legal?url=${encodeURIComponent(url)}`,
		fail: () => {
			uni.setClipboardData({ data: url })
			uni.showToast({ title: '认证链接已复制', icon: 'none' })
		},
	})
}

async function start() {
	if (busy.value || status.value === 'approved') return
	busy.value = true
	try {
		const res = await apiVerifyStart()
		const data = res.results || {}
		const hosted = data.hosted_url || data.url || data.inquiry_url || ''
		if (hosted) {
			openHosted(hosted)
			uni.showToast({ title: '请在打开的页面完成认证', icon: 'none' })
		} else if (data.inquiry_id || data.session_token) {
			uni.showToast({ title: '已创建认证会话', icon: 'none' })
		}
		status.value = data.status || 'pending'
		const boot = uni.getStorageSync('bootstrap') || {}
		if (boot.features && boot.features.persona_configured === false) {
			showSandbox.value = true
		}
		await load()
	} catch (e) {
		const boot = uni.getStorageSync('bootstrap') || {}
		if (boot.features && boot.features.persona_configured === false) {
			showSandbox.value = true
			uni.showToast({ title: 'Persona 未配置，可使用沙箱', icon: 'none' })
		} else {
			uni.showToast({ title: (e && e.message) || '启动失败', icon: 'none' })
		}
	}
	busy.value = false
}

async function decide(ok) {
	try {
		await apiVerifySandboxDecide({ approve: !!ok })
		await load()
		uni.showToast({ title: ok ? '已模拟通过' : '已模拟拒绝', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
	}
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background: var(--bg, #FFF7FA); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#222; font-size:48rpx; width:60rpx; }
.title { color:#222; font-size:40rpx; font-weight:700; }
.hero { margin-bottom: 28rpx; }
.badge {
	display:inline-flex; padding:10rpx 22rpx; border-radius:999rpx;
	background:#FFE0EA; margin-bottom:16rpx;
}
.badge text { color:#FF6B9A; font-size:24rpx; font-weight:700; }
.badge.ok { background: rgba(34,197,94,0.15); }
.badge.ok text { color:#16A34A; }
.badge.wait { background: rgba(255,198,41,0.25); }
.badge.wait text { color:#B8860B; }
.badge.bad { background: rgba(255,68,88,0.12); }
.badge.bad text { color:#FF4458; }
.lead { display:block; color:#666; font-size:26rpx; line-height:1.5; }
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:24rpx;
	border: 1px solid rgba(255,107,154,0.12);
}
.sec { display:block; color:#999; font-size:22rpx; margin-bottom:10rpx; }
.body { display:block; color:#333; font-size:26rpx; line-height:1.5; }
.btn {
	background: linear-gradient(90deg,#FF6B9A,#FF8FB3); border-radius:999rpx;
	padding:28rpx; text-align:center;
}
.btn.busy { opacity:0.7; }
.btn text { color:#fff; font-weight:700; }
.sandbox { margin-top: 40rpx; }
.row { display:flex; flex-direction:row; }
.mini {
	flex:1; border-radius:999rpx; padding:20rpx; text-align:center; margin-right:12rpx;
	background:#fff; border:1px solid rgba(255,107,154,0.2);
}
.mini.no { margin-right:0; }
.mini text { color:#333; font-size:24rpx; }
.mini.ok text { color:#16A34A; }
.mini.no text { color:#FF4458; }
</style>
