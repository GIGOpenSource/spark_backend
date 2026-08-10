<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">{{ $t('auth.signIn') }}</text>
		<input class="input" v-model="email" :placeholder="$t('auth.email')" placeholder-class="ph" />
		<input class="input" v-model="password" password :placeholder="$t('auth.password')" placeholder-class="ph" />
		<text class="forgot" @click="forgot">{{ $t('auth.forgot') }}</text>
		<view class="btn" @click="submit"><text>{{ $t('auth.continue') }}</text></view>
		<view class="btn apple" @click="appleLogin"><text>{{ $t('auth.continueApple') }}</text></view>
		<view class="btn phone" @click="goPhone"><text>{{ $t('auth.continuePhone') }}</text></view>
		<view class="btn google" @click="googleLogin"><text>{{ $t('auth.continueGoogle') }}</text></view>
		<view class="demo" @click="fillDemo"><text>{{ $t('auth.useDemo') }}</text></view>
		<view class="link" @click="goRegister"><text>{{ $t('auth.createAccount') }}</text></view>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { apiLogin, apiGoogleLogin, apiAppleLogin } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { isFirebaseMock } from '@/utils/capabilities.js'

const email = ref('test@bee.app')
const password = ref('SparkTest1')

function fillDemo() {
	email.value = 'test@bee.app'
	password.value = 'SparkTest1'
}

function afterAuth(data) {
	uni.setStorageSync('token', data.token)
	uni.setStorageSync('userInfo', data.user || {})
	const user = data.user || {}
	const afterNav = () => { try { refreshTabBadges({ force: true }) } catch (e) {} }
	if (!user.profile_complete && !user.age && !user.birthday) {
		uni.redirectTo({ url: '/pages/auth/onboarding', complete: afterNav })
	} else {
		uni.switchTab({ url: '/pages/discover/index', success: afterNav, fail: afterNav })
	}
}

async function submit() {
	trackClick('auth_login_submit')
	try {
		const res = await apiLogin({ email: email.value, password: password.value, remember: true })
		track('auth_login_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Login failed', icon: 'none' })
	}
}

async function googleLogin() {
	trackClick('auth_google')
	try {
		const payload = isFirebaseMock()
			? { email: `demo.google.${Date.now() % 100000}@bee.app`, nickname: 'Google User' }
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
			? { email: `demo.apple.${Date.now() % 100000}@privaterelay.bee.app`, nickname: 'Apple User' }
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

function forgot() {
	uni.navigateTo({ url: '/pages/auth/forgot' })
}
function goRegister() {
	uni.navigateTo({ url: '/pages/auth/register' })
}
function goPhone() {
	trackClick('auth_phone')
	uni.navigateTo({ url: '/pages/auth/phone' })
}
function back() {
	uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/auth/welcome' }) })
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: var(--bg, #FFFFFF);
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.back { color: var(--text, #111); font-size: 48rpx; display: block; margin-bottom: 24rpx; }
.title {
	display: block;
	color: var(--text, #111);
	font-size: 56rpx;
	font-weight: 800;
	margin-bottom: 48rpx;
}
.input {
	background: #FFF8E1;
	border-radius: 20rpx;
	padding: 28rpx;
	color: var(--text, #111);
	margin-bottom: 20rpx;
	font-size: 28rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.ph { color: #999; }
.forgot { display: block; color: #B8860B; font-size: 24rpx; margin-bottom: 12rpx; text-align: right; }
.btn {
	margin-top: 20rpx;
	background: #FFC629;
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.btn text { color: #111; font-weight: 800; }
.btn.apple { background: #111; }
.btn.apple text { color: #fff; }
.btn.phone { background: #FFF8E1; border: 1px solid rgba(255,198,41,0.45); }
.btn.phone text { color: #111; }
.btn.google { background: #fff; border: 1px solid #111; }
.btn.google text { color: #111; }
.demo { text-align: center; margin-top: 20rpx; }
.demo text { color: #B8860B; font-size: 24rpx; font-weight: 600; }
.link { text-align: center; margin-top: 28rpx; }
.link text { color: var(--muted, #666); }
</style>
