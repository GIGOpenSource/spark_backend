<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title spark-serif">Create account</text>
		<input class="input" v-model="email" placeholder="Email" placeholder-class="ph" />
		<input class="input" v-model="password" password placeholder="Password (8+ letters & numbers)" placeholder-class="ph" />
		<input class="input" v-model="confirm" password placeholder="Confirm password" placeholder-class="ph" />
		<view class="btn" :class="{ busy: submitting }" @click="submit">
			<text>{{ submitting ? 'Creating…' : 'Register' }}</text>
		</view>
		<view class="btn google" @click="googleLogin"><text>Continue with Google</text></view>
		<view class="link" @click="goLogin"><text>Already have an account? Sign in</text></view>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { apiRegister, apiGoogleLogin } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { getGoogleIdToken, isFirebaseMock } from '@/utils/capabilities.js'

const email = ref('')
const password = ref('')
const confirm = ref('')
const submitting = ref(false)

function afterAuth(data) {
	uni.setStorageSync('token', data.token)
	uni.setStorageSync('userInfo', data.user || {})
	uni.redirectTo({ url: '/pages/auth/onboarding' })
}

async function submit() {
	if (submitting.value) return
	trackClick('auth_register_submit')
	if (!email.value || !password.value) {
		uni.showToast({ title: 'Email & password required', icon: 'none' })
		return
	}
	if (password.value.length < 8) {
		uni.showToast({ title: 'Password too short', icon: 'none' })
		return
	}
	if (!/[A-Za-z]/.test(password.value) || !/[0-9]/.test(password.value)) {
		uni.showToast({ title: 'Use letters and numbers', icon: 'none' })
		return
	}
	if (password.value !== confirm.value) {
		uni.showToast({ title: 'Passwords do not match', icon: 'none' })
		return
	}
	submitting.value = true
	try {
		const res = await apiRegister({
			email: email.value,
			password: password.value,
			confirm_password: confirm.value,
			remember: true
		})
		track('auth_register_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Register failed', icon: 'none' })
	}
	submitting.value = false
}

async function googleLogin() {
	trackClick('auth_google')
	try {
		const idToken = await getGoogleIdToken()
		if (!idToken && !isFirebaseMock()) {
			uni.showToast({ title: 'Google Sign-In needs native SDK', icon: 'none' })
			return
		}
		const payload = idToken ? { id_token: idToken } : {}
		const res = await apiGoogleLogin(payload)
		track('auth_google_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Google login failed', icon: 'none' })
	}
}

function goLogin() {
	uni.navigateTo({ url: '/pages/auth/login' })
}
function back() {
	uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/auth/welcome' }) })
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: #FFFFFF;
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.back { color:#111; font-size:48rpx; display:block; margin-bottom:24rpx; }
.title {
	display: block;
	color: #111;
	font-size: 56rpx;
	margin-bottom: 48rpx;
}
.spark-serif { font-family: 'Playfair Display', 'Times New Roman', serif; }
.input {
	background: #FFF5F7;
	border-radius: 20rpx;
	padding: 28rpx;
	color: #111;
	margin-bottom: 20rpx;
	font-size: 28rpx;
	border: 1px solid rgba(253,38,122,0.22);
}
.ph { color: #999; }
.btn {
	margin-top: 20rpx;
	background: linear-gradient(90deg, #FD267A, #FF4458);
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.btn text { color: #fff; font-weight: 600; }
.btn.busy { opacity: 0.7; }
.btn.google { background:#fff; border: 1px solid #111; }
.btn.google text { color:#111; }
.link { text-align: center; margin-top: 28rpx; }
.link text { color: #666; font-size: 24rpx; }
</style>
