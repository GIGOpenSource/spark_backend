<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Photo verify</text>
		</view>

		<view class="hero">
			<view class="badge" :class="{ on: isVerified }"><text>{{ isVerified ? 'Verified' : 'Not verified' }}</text></view>
			<text class="sub">Confirm you’re a real person. Selfie checks use Persona when configured.</text>
		</view>

		<view class="card">
			<text class="label">Status</text>
			<text class="val">{{ statusLabel }}</text>
		</view>
		<view class="card" v-if="inquiryId">
			<text class="label">Inquiry</text>
			<text class="val mono">{{ inquiryId }}</text>
		</view>

		<view class="btn" :class="{ busy: busy }" @click="start" v-if="!isVerified">
			<text>{{ busy ? 'Starting…' : (inquiryId ? 'Refresh / continue' : 'Start verification') }}</text>
		</view>

		<view class="btn ghost" v-if="hostedUrl && !isVerified" @click="openHosted">
			<text>Open verification</text>
		</view>

		<template v-if="showSandbox && !isVerified && inquiryId">
			<text class="section">Sandbox (no Persona keys)</text>
			<view class="row">
				<view class="btn ghost" @click="decide(true)"><text>Approve</text></view>
				<view class="btn ghost danger" @click="decide(false)"><text>Decline</text></view>
			</view>
		</template>
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiVerifyStart, apiVerifyStatus, apiVerifySandboxDecide } from '@/api/verify.js'

const isVerified = ref(false)
const status = ref('')
const inquiryId = ref('')
const personaConfigured = ref(true)
const hostedUrl = ref('')
const busy = ref(false)

const showSandbox = computed(() => !personaConfigured.value)
const statusLabel = computed(() => {
	if (isVerified.value) return 'approved'
	return status.value || '—'
})

onMounted(load)

async function load() {
	try {
		const res = await apiVerifyStatus()
		const d = res.results || {}
		isVerified.value = !!d.is_verified
		status.value = d.status || ''
		inquiryId.value = d.inquiry_id || ''
		hostedUrl.value = d.hosted_url || ''
		if (typeof d.persona_configured === 'boolean') personaConfigured.value = d.persona_configured
	} catch (e) {}
}

function openHostedUrl(url) {
	if (!url) return
	// #ifdef H5
	window.open(url, '_blank')
	// #endif
	// #ifdef APP-PLUS
	try {
		plus.runtime.openURL(url)
		return
	} catch (e) {}
	// #endif
	// #ifndef H5
	uni.navigateTo({
		url: `/pagesA/me/legal?url=${encodeURIComponent(url)}`,
		fail: () => {
			uni.setClipboardData({ data: url })
			uni.showToast({ title: 'Link copied', icon: 'none' })
		}
	})
	// #endif
}

function openHosted() {
	openHostedUrl(hostedUrl.value)
}

async function start() {
	if (busy.value) return
	busy.value = true
	try {
		const res = await apiVerifyStart()
		const d = res.results || {}
		isVerified.value = !!d.is_verified
		status.value = d.status || status.value
		inquiryId.value = d.inquiry_id || inquiryId.value
		hostedUrl.value = d.hosted_url || hostedUrl.value
		if (typeof d.persona_configured === 'boolean') personaConfigured.value = d.persona_configured
		if (d.hosted_url && personaConfigured.value) {
			openHostedUrl(d.hosted_url)
		} else if (d.mock) {
			uni.showToast({ title: 'Sandbox inquiry created', icon: 'none' })
		} else if (!isVerified.value) {
			uni.showToast({ title: 'Inquiry started', icon: 'none' })
		}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Start failed', icon: 'none' })
	}
	busy.value = false
}

async function decide(approve) {
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
.page { min-height:100vh; background: var(--bg, #FFFFFF); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { display:block; color:#111; font-size:40rpx; font-weight:700; }
.hero { margin-bottom: 28rpx; padding: 8rpx; }
.badge {
	display:inline-flex; padding:10rpx 20rpx; border-radius:999rpx;
	background:#F3F0F7; margin-bottom:16rpx;
}
.badge text { color:#666; font-size:24rpx; font-weight:600; }
.badge.on { background: rgba(34,197,94,0.15); }
.badge.on text { color:#16A34A; }
.sub { display:block; color:#666; font-size:26rpx; line-height:1.45; }
.card {
	background:#FFFFFF; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(0,0,0,0.06);
}
.label { color:#666; font-size:24rpx; }
.val { color:#111; font-size:26rpx; max-width: 60%; text-align:right; }
.mono { font-size:22rpx; word-break: break-all; }
.btn {
	margin-top: 12rpx;
	background: linear-gradient(90deg, #FD267A, #FF4458); border-radius:999rpx;
	padding: 28rpx; text-align:center;
}
.btn text { color:#fff; font-weight:700; }
.btn.busy { opacity: 0.7; }
.btn.ghost {
	flex:1; background:#fff; border:1px solid rgba(0,0,0,0.12); margin-right:12rpx;
}
.btn.ghost text { color:#111; }
.btn.ghost.danger { margin-right:0; border-color: rgba(255,75,85,0.4); }
.btn.ghost.danger text { color:#FF4B55; }
.section {
	display:block; color:#666; font-size:22rpx; letter-spacing:1rpx;
	text-transform:uppercase; margin: 32rpx 8rpx 12rpx;
}
.row { display:flex; flex-direction:row; }
</style>
