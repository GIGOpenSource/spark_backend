<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">法律与数据</text>
		</view>

		<text class="section">协议</text>
		<view class="card" @click="openPolicy('tos')"><text>用户协议</text><text class="val">›</text></view>
		<view class="card" @click="openPolicy('privacy')"><text>隐私政策</text><text class="val">›</text></view>
		<view class="card" @click="openGuidelines"><text>社区准则</text><text class="val">›</text></view>

		<text class="section">年龄</text>
		<view class="note">
			<text>本应用仅面向 18 岁及以上用户。使用即表示你符合所在地区的年龄要求。</text>
		</view>

		<text class="section">你的数据</text>
		<view class="card" @click="exportData">
			<text>导出我的数据</text>
			<text class="val">{{ exporting ? '…' : '›' }}</text>
		</view>
		<view class="card danger" @click="deleteAccount">
			<text>删除账号</text>
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
			const res = await apiBootstrap({
				app_id: APP_ID, platform: 'h5', package_name: PACKAGE_NAME, app_version: '1.0.0',
			})
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
	uni.showToast({ title: '链接已复制', icon: 'none' })
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
			success: () => uni.showToast({ title: '导出内容已复制', icon: 'none' }),
		})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '导出失败', icon: 'none' })
	}
	exporting.value = false
}

function deleteAccount() {
	uni.showModal({
		title: '删除账号？',
		content: '账号将被永久停用，此操作不可恢复。',
		confirmColor: '#FF6B9A',
		success: (m) => {
			if (!m.confirm) return
			uni.showModal({
				title: '确认删除',
				editable: true,
				placeholderText: '输入 DELETE',
				success: async (m2) => {
					if (!m2.confirm) return
					const typed = String(m2.content || '').trim().toUpperCase()
					if (typed !== 'DELETE') {
						uni.showToast({ title: '请输入 DELETE 确认', icon: 'none' })
						return
					}
					try {
						await apiDeleteAccount({ confirm: 'delete' })
						uni.removeStorageSync('token')
						uni.removeStorageSync('userInfo')
						uni.reLaunch({ url: '/pages/auth/welcome' })
					} catch (e) {
						uni.showToast({ title: (e && e.message) || '删除失败', icon: 'none' })
					}
				},
			})
		},
	})
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFF7FA; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#222; font-size:48rpx; width:60rpx; }
.title { display:block; color:#222; font-size:40rpx; font-weight:700; }
.section {
	display:block; color:#999; font-size:22rpx; margin: 28rpx 8rpx 12rpx;
}
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(255,107,154,0.12);
}
.card text { color:#222; font-size:28rpx; }
.card.danger text { color:#FF6B9A; }
.val { color:#999; }
.note {
	background:#FFF0F5; border-radius:16rpx; padding:24rpx;
	border: 1px solid rgba(255,107,154,0.18);
}
.note text { color:#444; font-size:26rpx; line-height:1.5; }
</style>
