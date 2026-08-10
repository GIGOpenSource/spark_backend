<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">{{ $t('auth.phone') }}</text>
		<text class="sub" v-if="smsMock">演示模式：验证码输入 000000</text>

		<input
			class="input"
			v-model="phone"
			type="number"
			maxlength="11"
			:placeholder="$t('auth.phonePlaceholder')"
			placeholder-class="ph"
		/>
		<view class="code-row">
			<input
				class="input code"
				v-model="code"
				type="number"
				maxlength="6"
				:placeholder="$t('auth.codePlaceholder')"
				placeholder-class="ph"
			/>
			<view class="code-btn" :class="{ disabled: codeCooldown > 0 }" @click="sendCode">
				<text>{{ codeCooldown > 0 ? `${codeCooldown}s` : $t('auth.sendCode') }}</text>
			</view>
		</view>
		<view class="btn" @click="submit"><text>{{ $t('auth.continue') }}</text></view>
		<view class="link" @click="goEmail"><text>{{ $t('auth.emailLogin') }}</text></view>
	</view>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { apiSmsSend, apiSmsVerify } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { isSmsMock } from '@/utils/capabilities.js'

const phone = ref('')
const code = ref('')
const codeCooldown = ref(0)
const smsMock = computed(() => isSmsMock())
let cooldownTimer = null

onUnmounted(() => {
	if (cooldownTimer) clearInterval(cooldownTimer)
})

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

function startCooldown() {
	codeCooldown.value = 60
	if (cooldownTimer) clearInterval(cooldownTimer)
	cooldownTimer = setInterval(() => {
		codeCooldown.value -= 1
		if (codeCooldown.value <= 0) {
			clearInterval(cooldownTimer)
			cooldownTimer = null
		}
	}, 1000)
}

async function sendCode() {
	if (codeCooldown.value > 0) return
	trackClick('auth_sms_send')
	const p = (phone.value || '').trim()
	if (!/^1\d{10}$/.test(p)) {
		uni.showToast({ title: '请输入正确手机号', icon: 'none' })
		return
	}
	try {
		const res = await apiSmsSend({ phone: p })
		const mock = !!(res.results && res.results.mock) || smsMock.value
		uni.showToast({
			title: mock ? '验证码已发送（演示码 000000）' : '验证码已发送',
			icon: 'none',
		})
		startCooldown()
	} catch (e) {
		if (smsMock.value) {
			startCooldown()
			uni.showToast({ title: '演示模式：请输入 000000', icon: 'none' })
			return
		}
		uni.showToast({ title: (e && e.message) || '发送失败', icon: 'none' })
	}
}

async function submit() {
	trackClick('auth_phone')
	const p = (phone.value || '').trim()
	const c = (code.value || '').trim()
	if (!/^1\d{10}$/.test(p)) {
		uni.showToast({ title: '请输入正确手机号', icon: 'none' })
		return
	}
	if (!c) {
		uni.showToast({ title: '请输入验证码', icon: 'none' })
		return
	}
	try {
		const res = await apiSmsVerify({ phone: p, code: c })
		track('auth_sms_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '登录失败', icon: 'none' })
	}
}

function goEmail() {
	uni.navigateTo({ url: '/pages/auth/login?tab=email' })
}
function back() {
	uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/auth/welcome' }) })
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: var(--bg, #FFF7FA);
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.back { color: var(--text, #222); font-size: 48rpx; display: block; margin-bottom: 24rpx; }
.title {
	display: block; color: var(--text, #222); font-size: 48rpx; font-weight: 800; margin-bottom: 12rpx;
}
.sub { display: block; color: var(--muted, #888); font-size: 24rpx; margin-bottom: 28rpx; }
.input {
	background: #FFFFFF; border-radius: 20rpx; padding: 28rpx; color: #222;
	margin-bottom: 20rpx; font-size: 28rpx; border: 1px solid rgba(255,107,154,0.25);
}
.code-row { display: flex; flex-direction: row; align-items: center; margin-bottom: 8rpx; }
.input.code { flex: 1; margin-bottom: 0; margin-right: 12rpx; }
.code-btn {
	background: #FFF0F5; border: 1px solid rgba(255,107,154,0.35);
	border-radius: 20rpx; padding: 28rpx 22rpx; white-space: nowrap;
}
.code-btn text { color: #FF6B9A; font-size: 24rpx; font-weight: 600; }
.code-btn.disabled { opacity: 0.55; }
.ph { color: #999; }
.btn {
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3); border-radius: 999rpx;
	padding: 28rpx; text-align: center; margin-top: 16rpx;
}
.btn text { color: #fff; font-weight: 700; }
.link { text-align: center; margin-top: 28rpx; }
.link text { color: #666; }
</style>
