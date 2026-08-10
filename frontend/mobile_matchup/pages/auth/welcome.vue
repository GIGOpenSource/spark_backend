<template>
	<view class="welcome">
		<view class="glow" />
		<view class="hero">
			<view class="heart-logo" />
			<text class="logo">{{ $t('brand.name') }}</text>
			<text class="tagline">{{ $t('brand.tagline') }}</text>
		</view>
		<view class="actions">
			<view class="btn primary" @click="phoneLogin"><text>{{ $t('auth.phone') }}</text></view>
			<view class="btn apple" @click="appleLogin"><text>{{ $t('auth.apple') }}</text></view>
			<view class="btn wechat" @click="wechatLogin"><text>{{ $t('auth.wechat') }}</text></view>
			<view class="secondary-links">
				<text class="sec-link" @click="goRegister">{{ $t('auth.emailRegister') }}</text>
				<text class="sec-dot">·</text>
				<text class="sec-link" @click="goLogin">{{ $t('auth.emailLogin') }}</text>
			</view>
			<view class="policy">
				<text class="muted">{{ $t('auth.agreePrefix') }}</text>
				<text class="link" @click="openUrl(tos)">{{ $t('common.userAgreement') }}</text>
				<text class="muted"> {{ $t('common.and') }} </text>
				<text class="link" @click="openUrl(privacy)">{{ $t('common.privacyPolicy') }}</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiWechatLogin, apiAppleLogin } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { SITE_DOMAIN } from '@/config/config.js'
import { isFirebaseMock, isAppleSignInConfigured } from '@/utils/capabilities.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'

const tos = ref(`https://${SITE_DOMAIN}/tos`)
const privacy = ref(`https://${SITE_DOMAIN}/privacy`)

onMounted(() => {
	const token = uni.getStorageSync('token')
	if (token) {
		uni.switchTab({ url: '/pages/discover/index' })
		return
	}
	const boot = uni.getStorageSync('bootstrap') || {}
	if (boot.tos_url) tos.value = boot.tos_url
	if (boot.privacy_url) privacy.value = boot.privacy_url
	track('auth_welcome_view')
})

function afterAuth(data) {
	uni.setStorageSync('token', data.token)
	uni.setStorageSync('userInfo', data.user || {})
	const user = data.user || {}
	const afterNav = () => { try { refreshTabBadges({ force: true }) } catch (e) {} }
	if (!user.profile_complete && !user.age) {
		uni.redirectTo({ url: '/pages/auth/onboarding', complete: afterNav })
	} else {
		uni.switchTab({ url: '/pages/discover/index', success: afterNav, fail: afterNav })
	}
}

function goLogin() {
	uni.navigateTo({ url: '/pages/auth/login?tab=email' })
}
function goRegister() {
	trackClick('auth_continue')
	uni.navigateTo({ url: '/pages/auth/register' })
}
function phoneLogin() {
	trackClick('auth_phone')
	uni.navigateTo({ url: '/pages/auth/phone' })
}

async function appleLogin() {
	trackClick('auth_apple')
	try {
		const res = await apiAppleLogin({})
		track('auth_apple_ok')
		afterAuth(res.results || {})
	} catch (e) {
		if (isFirebaseMock() || !isAppleSignInConfigured()) {
			uni.showToast({
				title: (e && e.message) || 'Apple 登录暂不可用，请用手机号',
				icon: 'none',
			})
			return
		}
		uni.showToast({ title: (e && e.message) || 'Apple 登录失败', icon: 'none' })
	}
}

async function wechatLogin() {
	trackClick('auth_wechat')
	try {
		const res = await apiWechatLogin({ code: `mock_wx_${Date.now()}` })
		track('auth_wechat_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '微信登录暂不可用，请用手机号', icon: 'none' })
		setTimeout(() => phoneLogin(), 600)
	}
}
function openUrl(url) {
	// #ifdef H5
	window.open(url, '_blank')
	// #endif
	// #ifndef H5
	uni.setClipboardData({ data: url })
	// #endif
}
</script>

<style scoped>
.welcome {
	min-height: 100vh;
	background: var(--bg, #FFF7FA);
	padding: 120rpx 48rpx 80rpx;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	box-sizing: border-box;
	position: relative;
	overflow: hidden;
}
.glow {
	position: absolute;
	left: -20%;
	top: 8%;
	width: 140%;
	height: 55%;
	background: radial-gradient(ellipse at center, rgba(255,107,154,0.28) 0%, transparent 70%);
	pointer-events: none;
}
.hero { position: relative; z-index: 1; padding-top: 80rpx; text-align: center; }
.heart-logo {
	width: 110rpx; height: 100rpx; margin: 0 auto 24rpx;
	background: linear-gradient(135deg, #FF6B9A, #FF8FB3);
	border-radius: 55rpx 55rpx 12rpx 12rpx;
	transform: rotate(-45deg);
}
.logo {
	font-size: 64rpx;
	color: #FF6B9A;
	font-weight: 800;
	letter-spacing: 2rpx;
	display: block;
}
.tagline {
	display: block;
	margin-top: 16rpx;
	color: rgba(80,40,60,0.7);
	font-size: 30rpx;
}
.actions { position: relative; z-index: 1; }
.btn {
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
	margin-bottom: 20rpx;
}
.btn text { font-size: 30rpx; font-weight: 600; }
.primary { background: linear-gradient(90deg, #FF6B9A, #FF8FB3); }
.primary text { color: #fff; }
.apple { background: #111; }
.apple text { color: #fff; }
.wechat { background: #07C160; }
.wechat text { color: #fff; }
.secondary-links {
	display: flex; flex-direction: row; justify-content: center; align-items: center;
	margin: 8rpx 0 20rpx;
}
.sec-link { color: #FF6B9A; font-size: 26rpx; }
.sec-dot { color: #ccc; margin: 0 16rpx; font-size: 26rpx; }
.policy { text-align: center; margin-top: 12rpx; }
.muted { color: #888; font-size: 22rpx; }
.link { color: #FF6B9A; font-size: 22rpx; }
</style>
