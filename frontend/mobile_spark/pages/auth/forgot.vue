<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">Forgot password</text>

		<template v-if="step === 'email'">
			<text class="sub">Enter your email and we’ll send a reset code.</text>
			<input class="input" v-model="email" placeholder="Email" placeholder-class="ph" />
			<view class="btn" :class="{ busy: submitting }" @click="sendCode">
				<text>{{ submitting ? 'Sending…' : 'Send reset code' }}</text>
			</view>
		</template>

		<template v-else-if="step === 'reset'">
			<text class="sub">Enter the code sent to {{ email }} and choose a new password.</text>
			<input class="input" v-model="code" placeholder="6-digit code" placeholder-class="ph" maxlength="6" />
			<input class="input" v-model="password" password placeholder="New password (6+)" placeholder-class="ph" />
			<input class="input" v-model="confirm" password placeholder="Confirm password" placeholder-class="ph" />
			<text v-if="debugCode" class="debug">Dev code: {{ debugCode }}</text>
			<view class="btn" :class="{ busy: submitting }" @click="doReset">
				<text>{{ submitting ? 'Saving…' : 'Reset password' }}</text>
			</view>
			<view class="link" @click="sendCode"><text>Resend code</text></view>
		</template>

		<template v-else>
			<text class="done-title">Password updated</text>
			<text class="done-sub">You can sign in with your new password.</text>
			<view class="btn" @click="goLogin"><text>Back to sign in</text></view>
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
const debugCode = ref('')
const step = ref('email')
const submitting = ref(false)

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
		if (data.debug_code) debugCode.value = data.debug_code
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
	if (!password.value || password.value.length < 6) {
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
		step.value = 'done'
	} catch (err) {
		uni.showToast({ title: (err && err.message) || 'Reset failed', icon: 'none' })
	}
	submitting.value = false
}

function goLogin() {
	uni.redirectTo({ url: '/pages/auth/login' })
}
function back() {
	if (step.value === 'reset') {
		step.value = 'email'
		return
	}
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
	background: #FFF5F7; border-radius: 20rpx; padding: 28rpx; color: #111;
	margin-bottom: 24rpx; font-size: 28rpx; border: 1px solid rgba(253,38,122,0.22);
}
.ph { color:#999; }
.btn {
	background: linear-gradient(90deg, #FD267A, #FF4458); border-radius:999rpx;
	padding: 28rpx; text-align:center;
}
.btn.busy { opacity: 0.7; }
.btn text { color:#fff; font-weight:700; }
.debug { display:block; color:#FD267A; font-size:22rpx; margin-bottom:16rpx; }
.link { text-align:center; margin-top:24rpx; }
.link text { color:#666; font-size:24rpx; }
.done-title { display:block; color:#111; font-size:36rpx; font-weight:800; margin: 40rpx 0 16rpx; }
.done-sub { display:block; color:#666; font-size:26rpx; margin-bottom:40rpx; line-height:1.5; }
</style>
