<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Legal & data</text>
		</view>

		<view class="card" @click="openPolicy('tos')"><text>Terms of Service</text><text class="val">›</text></view>
		<view class="card" @click="openPolicy('privacy')"><text>Privacy Policy</text><text class="val">›</text></view>
		<view class="card" @click="openPolicy('guidelines')"><text>Community Guidelines</text><text class="val">›</text></view>

		<text class="section">Your data</text>
		<view class="card" @click="exportData">
			<text>Export my data</text>
			<text class="val">{{ exporting ? '…' : '›' }}</text>
		</view>
		<view class="card danger" @click="deleteAccount"><text>Delete account</text></view>
		<text class="note">You must be 18+ to use this app. Deleting your account is permanent.</text>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiDeleteAccount, apiExportData, apiBootstrap } from '@/api/auth.js'
import { APP_ID, PACKAGE_NAME, SITE_DOMAIN } from '@/config/config.js'

const exporting = ref(false)
const policy = ref({
	tos_url: `https://${SITE_DOMAIN}/tos`,
	privacy_url: `https://${SITE_DOMAIN}/privacy`,
	community_guidelines_url: `https://${SITE_DOMAIN}/guidelines`,
})

onMounted(async () => {
	let boot = uni.getStorageSync('bootstrap') || {}
	if (!boot.tos_url) {
		try {
			const res = await apiBootstrap({ app_id: APP_ID, platform: 'h5', package_name: PACKAGE_NAME, app_version: '1.0.0' })
			boot = res.results || {}
			uni.setStorageSync('bootstrap', boot)
		} catch (e) {}
	}
	policy.value = {
		tos_url: boot.tos_url || policy.value.tos_url,
		privacy_url: boot.privacy_url || policy.value.privacy_url,
		community_guidelines_url: boot.community_guidelines_url || policy.value.community_guidelines_url,
	}
})

function openPolicy(kind) {
	const map = {
		tos: policy.value.tos_url,
		privacy: policy.value.privacy_url,
		guidelines: policy.value.community_guidelines_url,
	}
	const url = map[kind]
	// #ifdef H5
	window.open(url, '_blank')
	// #endif
	// #ifndef H5
	uni.setClipboardData({ data: url })
	uni.showToast({ title: 'Link copied', icon: 'none' })
	// #endif
}

async function exportData() {
	if (exporting.value) return
	exporting.value = true
	try {
		const res = await apiExportData()
		const raw = JSON.stringify(res.results || {}, null, 2)
		uni.setClipboardData({ data: raw.slice(0, 4000) })
		uni.showToast({ title: 'Export copied (snapshot)', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Export failed', icon: 'none' })
	}
	exporting.value = false
}

function deleteAccount() {
	uni.showModal({
		title: 'Delete account?',
		content: 'This cannot be undone. Type confirm in the next step.',
		success: async (m) => {
			if (!m.confirm) return
			try {
				await apiDeleteAccount({ confirm: 'delete' })
				uni.removeStorageSync('token')
				uni.removeStorageSync('userInfo')
				uni.reLaunch({ url: '/pages/auth/welcome' })
			} catch (e) {
				uni.showToast({ title: (e && e.message) || 'Delete failed', icon: 'none' })
			}
		},
	})
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
.section {
	display:block; color:#888; font-size:22rpx; letter-spacing:1rpx;
	text-transform:uppercase; margin: 28rpx 8rpx 12rpx;
}
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(255,198,41,0.25);
}
.card text { color:#111; font-size:28rpx; }
.val { color:#999; }
.card.danger text { color:#C0392B; }
.note { display:block; color:#888; font-size:22rpx; margin-top:16rpx; line-height:1.45; }
</style>
