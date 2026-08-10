<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Legal & data</text>
		</view>

		<text class="section">Policies</text>
		<view class="card" @click="openPolicy('tos')"><text>Terms of Service</text><text class="val">›</text></view>
		<view class="card" @click="openPolicy('privacy')"><text>Privacy Policy</text><text class="val">›</text></view>
		<view class="card" @click="openGuidelines"><text>Community Guidelines</text><text class="val">›</text></view>

		<text class="section">Age</text>
		<view class="note">
			<text>Spark is for adults 18+. By using the app you confirm you meet the age requirement in your region.</text>
		</view>

		<text class="section">Your data</text>
		<view class="card" @click="exportData">
			<text>Export my data</text>
			<text class="val">{{ exporting ? '…' : '›' }}</text>
		</view>
		<view class="card danger" @click="deleteAccount">
			<text>Delete account</text>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiBootstrap, apiDeleteAccount, apiExportData } from '@/api/auth.js'
import { APP_ID, PACKAGE_NAME, SITE_DOMAIN } from '@/config/config.js'

const exporting = ref(false)
const policy = ref({
	tos_url: `https://${SITE_DOMAIN}/tos`,
	privacy_url: `https://${SITE_DOMAIN}/privacy`,
	guidelines_url: `https://${SITE_DOMAIN}/community`,
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
		guidelines_url: boot.community_guidelines_url || boot.guidelines_url || policy.value.guidelines_url,
	}
})

function openUrl(url) {
	// #ifdef H5
	window.open(url, '_blank')
	// #endif
	// #ifndef H5
	uni.setClipboardData({ data: url })
	uni.showToast({ title: 'Link copied', icon: 'none' })
	// #endif
}

function openPolicy(kind) {
	openUrl(kind === 'privacy' ? policy.value.privacy_url : policy.value.tos_url)
}
function openGuidelines() {
	openUrl(policy.value.guidelines_url)
}

async function exportData() {
	if (exporting.value) return
	exporting.value = true
	try {
		const res = await apiExportData()
		const data = res.results || {}
		const text = JSON.stringify(data, null, 2)
		uni.setClipboardData({
			data: text.slice(0, 50000),
			success: () => uni.showToast({ title: 'Export copied to clipboard', icon: 'none' }),
		})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Export failed', icon: 'none' })
	}
	exporting.value = false
}

function deleteAccount() {
	uni.showModal({
		title: 'Delete account?',
		content: 'This permanently deactivates your account. Type confirmation on the next step.',
		confirmColor: '#FF4B55',
		success: (m) => {
			if (!m.confirm) return
			uni.showModal({
				title: 'Confirm',
				editable: true,
				placeholderText: 'Type DELETE',
				success: async (m2) => {
					if (!m2.confirm) return
					const typed = String(m2.content || '').trim().toUpperCase()
					if (typed !== 'DELETE') {
						uni.showToast({ title: 'Type DELETE to confirm', icon: 'none' })
						return
					}
					try {
						await apiDeleteAccount({ confirm: 'delete' })
						uni.removeStorageSync('token')
						uni.removeStorageSync('userInfo')
						uni.reLaunch({ url: '/pages/auth/welcome' })
					} catch (e) {
						uni.showToast({ title: (e && e.message) || 'Delete failed', icon: 'none' })
					}
				}
			})
		}
	})
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFFFFF; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { display:block; color:#111; font-size:40rpx; font-weight:700; }
.section {
	display:block; color:#666; font-size:22rpx; letter-spacing:1rpx;
	text-transform:uppercase; margin: 28rpx 8rpx 12rpx;
}
.card {
	background:#FFFFFF; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(0,0,0,0.06);
}
.card text { color:#111; font-size:28rpx; }
.card.danger { margin-top: 8rpx; }
.card.danger text { color:#FF4B55; }
.val { color:#999; }
.note {
	background:#FFF5F7; border-radius:16rpx; padding:24rpx;
	border: 1px solid rgba(253,38,122,0.15);
}
.note text { color:#444; font-size:26rpx; line-height:1.5; }
</style>
