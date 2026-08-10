<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">{{ step === 'reset' ? 'Reset password' : 'Forgot password' }}</text>
		<text class="sub" v-if="step === 'email'">Enter your email — we’ll send a 6-digit code.</text>
		<text class="sub" v-else-if="step === 'reset'">Enter the code from your email and a new password.</text>

		<template v-if="step === 'email'">
			<input class="input" v-model="email" placeholder="Email" placeholder-class="ph" />
			<view class="btn" :class="{ busy: submitting }" @click="sendCode">
				<text>{{ submitting ? 'Sending…' : 'Send code' }}</text>
			</view>
		</template>
		<template v-else>
			<input class="input" v-model="code" placeholder="6-digit code" placeholder-class="ph" />
			<input class="input" v-model="password" password placeholder="New password (6+)" placeholder-class="ph" />
			<input class="input" v-model="confirm" password placeholder="Confirm password" placeholder-class="ph" />
			<text v-if="debugCode" class="debug">Dev code: {{ debugCode }}</text>
			<view class="btn" :class="{ busy: submitting }" @click="doReset">
				<text>{{ submitting ? 'Saving…' : 'Reset password' }}</text>
			</view>
			<view class="link" @click="step = 'email'"><text>Resend code</text></view>
		</template>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { apiPasswordForgot, apiPasswordReset } from '@/api/auth.js'

const email = ref('')
const code = ref('')
const password = ref('')
const confirm = ref('')
const step = ref('email')
const submitting = ref(false)
const debugCode = ref('')

async function sendCode() {
	if (submitting.value) return
	const e = email.value.trim()
	if (!e || !e.includes('@')) {
		uni.showToast({ title: 'Enter a valid email', icon: 'none' })
		return
	}
	submitting.value = true
	try {
		const res = await apiPasswordForgot({ email: e })
		const data = res.results || {}
		debugCode.value = data.debug_code || ''
		step.value = 'reset'
		uni.showToast({ title: 'Check your inbox', icon: 'none' })
	} catch (err) {
		uni.showToast({ title: (err && err.message) || 'Send failed', icon: 'none' })
	}
	submitting.value = false
}

async function doReset() {
	if (submitting.value) return
	if (!code.value.trim()) {
		uni.showToast({ title: 'Enter the code', icon: 'none' })
		return
	}
	if (password.value.length < 6) {
		uni.showToast({ title: 'Password too short', icon: 'none' })
		return
	}
	if (password.value !== confirm.value) {
		uni.showToast({ title: 'Passwords do not match', icon: 'none' })
		return
	}
	submitting.value = true
	try {
		await apiPasswordReset({
			email: email.value.trim(),
			code: code.value.trim(),
			password: password.value,
		})
		uni.showToast({ title: 'Password updated', icon: 'none' })
		setTimeout(() => uni.redirectTo({ url: '/pages/auth/login' }), 400)
	} catch (err) {
		uni.showToast({ title: (err && err.message) || 'Reset failed', icon: 'none' })
	}
	submitting.value = false
}

function back() {
	uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/auth/login' }) })
}
</script>

<style scoped>
.page {
	min-height: 100vh; background: #FFFFFF;
	padding: 100rpx 48rpx 80rpx; box-sizing: border-box;
}
.back { color:#111; font-size:48rpx; display:block; margin-bottom:24rpx; }
.title { display:block; color:#111; font-size:48rpx; font-weight:800; margin-bottom:12rpx; }
.sub { display:block; color:#666; font-size:26rpx; margin-bottom:36rpx; line-height:1.45; }
.input {
	background: #FFF8E1; border-radius: 20rpx; padding: 28rpx; color: #111;
	margin-bottom: 24rpx; font-size: 28rpx; border: 1px solid rgba(255,198,41,0.35);
}
.ph { color:#999; }
.btn {
	background: #FFC629; border-radius:999rpx;
	padding: 28rpx; text-align:center;
}
.btn.busy { opacity: 0.7; }
.btn text { color:#111; font-weight:800; }
.debug { display:block; color:#B8860B; font-size:22rpx; margin-bottom:16rpx; }
.link { text-align:center; margin-top:24rpx; }
.link text { color:#666; font-size:26rpx; }
</style>
