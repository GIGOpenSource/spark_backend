<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">忘记密码</text>

		<template v-if="step === 'email'">
			<text class="sub">输入注册邮箱，我们将发送重置验证码。</text>
			<input class="input" v-model="email" placeholder="邮箱" placeholder-class="ph" />
			<view class="btn" :class="{ busy: submitting }" @click="sendCode">
				<text>{{ submitting ? '发送中…' : '发送验证码' }}</text>
			</view>
		</template>

		<template v-else-if="step === 'reset'">
			<text class="sub">输入发送至 {{ email }} 的验证码，并设置新密码。</text>
			<input class="input" v-model="code" placeholder="6 位验证码" placeholder-class="ph" maxlength="6" />
			<input class="input" v-model="password" password placeholder="新密码（至少 6 位）" placeholder-class="ph" />
			<input class="input" v-model="confirm" password placeholder="确认密码" placeholder-class="ph" />
			<text v-if="debugCode" class="debug">开发码：{{ debugCode }}</text>
			<view class="btn" :class="{ busy: submitting }" @click="doReset">
				<text>{{ submitting ? '保存中…' : '重置密码' }}</text>
			</view>
			<view class="link" @click="sendCode"><text>重新发送</text></view>
		</template>

		<template v-else>
			<text class="done-title">密码已更新</text>
			<text class="done-sub">请使用新密码登录。</text>
			<view class="btn" @click="goLogin"><text>返回登录</text></view>
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
		uni.showToast({ title: '请输入有效邮箱', icon: 'none' })
		return
	}
	submitting.value = true
	try {
		const res = await apiPasswordForgot({ email: e })
		const data = res.results || {}
		if (data.debug_code) debugCode.value = data.debug_code
		step.value = 'reset'
		uni.showToast({ title: '请查收邮件', icon: 'none' })
	} catch (err) {
		uni.showToast({ title: (err && err.message) || '发送失败', icon: 'none' })
	}
	submitting.value = false
}

async function doReset() {
	if (submitting.value) return
	if (!code.value.trim()) {
		uni.showToast({ title: '请输入验证码', icon: 'none' })
		return
	}
	if (!password.value || password.value.length < 6) {
		uni.showToast({ title: '密码太短', icon: 'none' })
		return
	}
	if (password.value !== confirm.value) {
		uni.showToast({ title: '两次密码不一致', icon: 'none' })
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
		uni.showToast({ title: (err && err.message) || '重置失败', icon: 'none' })
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
	min-height: 100vh; background: #FFF7FA;
	padding: 100rpx 48rpx 80rpx; box-sizing: border-box;
}
.back { color:#222; font-size:48rpx; display:block; margin-bottom:24rpx; }
.title { display:block; color:#222; font-size:48rpx; font-weight:800; margin-bottom:12rpx; }
.sub { display:block; color:#888; font-size:26rpx; margin-bottom:36rpx; line-height:1.45; }
.input {
	background: #FFFFFF; border-radius: 20rpx; padding: 28rpx; color: #222;
	margin-bottom: 24rpx; font-size: 28rpx; border: 1px solid rgba(255,107,154,0.25);
}
.ph { color:#999; }
.btn {
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3); border-radius:999rpx;
	padding: 28rpx; text-align:center;
}
.btn.busy { opacity: 0.7; }
.btn text { color:#fff; font-weight:700; }
.debug { display:block; color:#FF6B9A; font-size:22rpx; margin-bottom:16rpx; }
.link { text-align:center; margin-top:24rpx; }
.link text { color:#888; font-size:24rpx; }
.done-title { display:block; color:#222; font-size:36rpx; font-weight:800; margin: 40rpx 0 16rpx; }
.done-sub { display:block; color:#888; font-size:26rpx; margin-bottom:40rpx; line-height:1.5; }
</style>
