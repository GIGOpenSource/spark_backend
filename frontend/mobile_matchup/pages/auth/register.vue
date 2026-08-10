<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">注册账号</text>
		<input class="input" v-model="email" placeholder="邮箱" placeholder-class="ph" />
		<input class="input" v-model="password" password placeholder="密码（8位以上，含字母和数字）" placeholder-class="ph" />
		<input class="input" v-model="confirm" password placeholder="确认密码" placeholder-class="ph" />
		<view class="btn" :class="{ busy: submitting }" @click="submit">
			<text>{{ submitting ? '创建中…' : '注册' }}</text>
		</view>
		<view class="btn google" @click="googleLogin"><text>使用 Google 继续</text></view>
		<view class="link" @click="goLogin"><text>已有账号？去登录</text></view>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { apiRegister, apiGoogleLogin } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'

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
		uni.showToast({ title: '请填写邮箱和密码', icon: 'none' })
		return
	}
	if (password.value.length < 8) {
		uni.showToast({ title: '密码太短', icon: 'none' })
		return
	}
	if (!/[A-Za-z]/.test(password.value) || !/[0-9]/.test(password.value)) {
		uni.showToast({ title: '密码需包含字母和数字', icon: 'none' })
		return
	}
	if (password.value !== confirm.value) {
		uni.showToast({ title: '两次密码不一致', icon: 'none' })
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
		uni.showToast({ title: (e && e.message) || '注册失败', icon: 'none' })
	}
	submitting.value = false
}

async function googleLogin() {
	trackClick('auth_google')
	try {
		const res = await apiGoogleLogin({})
		track('auth_google_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Google 登录失败', icon: 'none' })
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
	background: #FFF7FA;
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.back { color:#222; font-size:48rpx; display:block; margin-bottom:24rpx; }
.title {
	display: block;
	color: #222;
	font-size: 56rpx;
	font-weight: 800;
	margin-bottom: 48rpx;
}
.input {
	background: #fff;
	border-radius: 20rpx;
	padding: 28rpx;
	color: #222;
	margin-bottom: 20rpx;
	font-size: 28rpx;
	border: 1px solid rgba(255,107,154,0.25);
}
.ph { color: #999; }
.btn {
	margin-top: 20rpx;
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3);
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.btn text { color: #fff; font-weight: 800; }
.btn.busy { opacity: 0.7; }
.btn.google { background:#fff; border: 1px solid rgba(255,107,154,0.35); }
.btn.google text { color:#222; }
.link { text-align: center; margin-top: 28rpx; }
.link text { color: #666; font-size: 24rpx; }
</style>
