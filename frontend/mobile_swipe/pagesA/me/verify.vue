<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Photo verification</text>
		</view>
		<view class="hero">
			<view class="badge" :class="{ on: isVerified }">{{ isVerified ? 'Verified' : 'Not verified' }}</view>
			<text class="sub">Confirm you’re real with a quick selfie check. Verified profiles get a blue check.</text>
		</view>
		<view class="card" v-if="status">
			<text>Status</text>
			<text class="val">{{ status }}</text>
		</view>
		<view class="btn" :class="{ busy: loading }" @click="start">
			<text>{{ loading ? 'Starting…' : (isVerified ? 'Already verified' : 'Start verification') }}</text>
		</view>
		<view v-if="!personaReady && inquiryId && !isVerified" class="btn ghost" @click="sandbox(true)">
			<text>Sandbox: approve</text>
		</view>
		<view v-if="!personaReady && inquiryId && !isVerified" class="btn ghost" @click="sandbox(false)">
			<text>Sandbox: decline</text>
		</view>
		<text class="note" v-if="!personaReady">Persona keys not linked — sandbox decide is available.</text>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiVerifyStart, apiVerifyStatus, apiVerifySandboxDecide } from '@/api/verify.js'

const isVerified = ref(false)
const status = ref('')
const inquiryId = ref('')
const personaReady = ref(false)
const loading = ref(false)

async function refresh() {
	try {
		const res = await apiVerifyStatus()
		const d = res.results || {}
		isVerified.value = !!d.is_verified
		status.value = d.status || (d.is_verified ? 'approved' : '')
		inquiryId.value = d.inquiry_id || ''
		personaReady.value = !!d.persona_configured
	} catch (e) {}
}

onMounted(refresh)

async function start() {
	if (isVerified.value || loading.value) return
	loading.value = true
	try {
		const res = await apiVerifyStart()
		const d = res.results || {}
		isVerified.value = !!d.is_verified
		status.value = d.status || ''
		inquiryId.value = d.inquiry_id || ''
		personaReady.value = !!d.persona_configured
		const hosted = d.hosted_url || d.inquiry_url || ''
		if (hosted) {
			openHosted(hosted)
		} else {
			uni.showToast({
				title: d.mock ? 'Inquiry created (sandbox)' : 'Verification started',
				icon: 'none',
			})
		}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Start failed', icon: 'none' })
	}
	loading.value = false
}

function openHosted(url) {
	if (!url) return
	// #ifdef H5
	window.open(url, '_blank')
	return
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
			uni.showToast({ title: 'Verification link copied', icon: 'none' })
		},
	})
}

async function sandbox(approve) {
	try {
		const res = await apiVerifySandboxDecide({ approve, inquiry_id: inquiryId.value })
		const d = res.results || {}
		isVerified.value = !!d.is_verified
		status.value = d.status || ''
		uni.showToast({ title: approve ? 'Verified' : 'Declined', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Decide failed', icon: 'none' })
	}
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFFDF6; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { color:#111; font-size:40rpx; font-weight:800; }
.hero { margin-bottom: 28rpx; }
.badge {
	display:inline-block; padding: 10rpx 20rpx; border-radius:999rpx;
	background:#eee; color:#666; font-size:24rpx; font-weight:700; margin-bottom:16rpx;
}
.badge.on { background:#FFC629; color:#111; }
.sub { display:block; color:#666; font-size:26rpx; line-height:1.45; }
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between;
	border: 1px solid rgba(255,198,41,0.25);
}
.card text { color:#111; font-size:28rpx; }
.val { color:#999; }
.btn {
	background:#FFC629; border-radius:999rpx; padding:28rpx; text-align:center; margin-bottom:16rpx;
}
.btn.busy { opacity:0.7; }
.btn text { color:#111; font-weight:800; }
.btn.ghost { background:#fff; border:1px solid rgba(255,198,41,0.5); }
.note { display:block; color:#888; font-size:22rpx; margin-top:12rpx; }
</style>
