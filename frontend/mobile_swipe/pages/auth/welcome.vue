<template>
	<view class="welcome">
		<view class="glow" />
		<view class="hero">
			<view class="bee-logo" />
			<text class="logo">{{ APP_NAME_DISPLAY }}</text>
			<text class="tagline">{{ $t('auth.tagline') }}</text>
		</view>
		<view class="actions">
			<view class="btn primary" @click="goRegister"><text>{{ $t('auth.createAccount') }}</text></view>
			<view class="btn ghost" @click="goLogin"><text>{{ $t('auth.signIn') }}</text></view>
			<view class="btn apple" @click="appleLogin"><text>{{ $t('auth.continueApple') }}</text></view>
			<view class="btn phone" @click="goPhone"><text>{{ $t('auth.continuePhone') }}</text></view>
			<view class="btn google" @click="googleLogin"><text>{{ $t('auth.continueGoogle') }}</text></view>
			<view class="policy">
				<text class="muted">{{ $t('auth.agreePrefix') }} </text>
				<text class="link" @click="openUrl(tos)">{{ $t('auth.terms') }}</text>
				<text class="muted"> & </text>
				<text class="link" @click="openUrl(privacy)">{{ $t('auth.privacy') }}</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiGoogleLogin, apiAppleLogin } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { APP_NAME_DISPLAY, SITE_DOMAIN } from '@/config/config.js'
import { isFirebaseMock } from '@/utils/capabilities.js'

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
	if (!user.profile_complete && !user.age) {
		uni.redirectTo({ url: '/pages/auth/onboarding' })
	} else {
		uni.switchTab({ url: '/pages/discover/index' })
	}
}

function goLogin() {
	uni.navigateTo({ url: '/pages/auth/login' })
}
function goRegister() {
	trackClick('auth_continue')
	uni.navigateTo({ url: '/pages/auth/register' })
}
function goPhone() {
	trackClick('auth_phone')
	uni.navigateTo({ url: '/pages/auth/phone' })
}

async function googleLogin() {
	trackClick('auth_google')
	try {
		const payload = isFirebaseMock()
			? {
				email: `demo.google.${Date.now() % 100000}@bee.app`,
				nickname: 'Google User',
				avatar_url: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400',
			}
			: {}
		const res = await apiGoogleLogin(payload)
		track('auth_google_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({
			title: (e && e.message) || (isFirebaseMock() ? 'Google login failed' : 'Google SDK required'),
			icon: 'none',
		})
	}
}

async function appleLogin() {
	trackClick('auth_apple')
	try {
		const payload = isFirebaseMock()
			? {
				email: `demo.apple.${Date.now() % 100000}@privaterelay.bee.app`,
				nickname: 'Apple User',
			}
			: {}
		const res = await apiAppleLogin(payload)
		track('auth_apple_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({
			title: (e && e.message) || (isFirebaseMock() ? 'Apple login failed' : 'Apple Sign In required'),
			icon: 'none',
		})
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
	background: var(--bg, #FFFFFF);
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
	background: radial-gradient(ellipse at center, rgba(255,198,41,0.55) 0%, rgba(255,224,130,0.28) 35%, transparent 70%);
	pointer-events: none;
}
.hero { position: relative; z-index: 1; padding-top: 80rpx; text-align: center; }
.bee-logo {
	width: 140rpx; height: 140rpx; margin: 0 auto 24rpx;
	background: url('/static/icons/bee.png') center/contain no-repeat;
}
.logo {
	font-size: 72rpx;
	color: var(--text, #111);
	font-weight: 900;
	letter-spacing: 2rpx;
	display: block;
	font-family: 'Montserrat', 'Helvetica Neue', sans-serif;
}
.tagline {
	display: block;
	margin-top: 16rpx;
	color: var(--muted, #666);
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
.primary { background: #FFC629; }
.primary text { color: #111; }
.ghost {
	background: transparent;
	border: 1px solid #111;
}
.ghost text { color: var(--text, #111); }
.apple {
	background: #111;
}
.apple text { color: #fff; }
.phone {
	background: #FFF8E1;
	border: 1px solid rgba(255,198,41,0.45);
}
.phone text { color: #111; }
.google {
	background: #fff;
	border: 1px solid rgba(0,0,0,0.12);
}
.google text { color: #111; }
.policy { text-align: center; margin-top: 12rpx; }
.muted { color: #888; font-size: 22rpx; }
.link { color: #FFC629; font-size: 22rpx; }
</style>
