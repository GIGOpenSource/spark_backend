<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">{{ $t('auth.login') }}</text>

		<view class="tabs">
			<view class="tab" :class="{ on: mode === 'phone' }" @click="mode = 'phone'"><text>手机号</text></view>
			<view class="tab" :class="{ on: mode === 'email' }" @click="mode = 'email'"><text>邮箱</text></view>
		</view>

		<template v-if="mode === 'phone'">
			<input class="input" v-model="phone" type="number" maxlength="11" :placeholder="$t('auth.phonePlaceholder')" placeholder-class="ph" />
			<view class="code-row">
				<input class="input code" v-model="code" type="number" maxlength="6" :placeholder="$t('auth.codePlaceholder')" placeholder-class="ph" />
				<view class="code-btn" :class="{ disabled: codeCooldown > 0 }" @click="sendCode">
					<text>{{ codeCooldown > 0 ? `${codeCooldown}s` : $t('auth.sendCode') }}</text>
				</view>
			</view>
			<text class="hint" v-if="smsMock">演示：验证码 000000</text>
			<view class="btn" @click="submitPhone"><text>{{ $t('auth.continue') }}</text></view>
			<view class="btn apple" @click="appleLogin"><text>{{ $t('auth.apple') }}</text></view>
			<view class="btn wechat" @click="wechatLogin"><text>{{ $t('auth.wechat') }}</text></view>
			<view class="link-row" @click="goPhonePage"><text>独立手机号登录页 ›</text></view>
		</template>

		<template v-else>
			<input class="input" v-model="email" placeholder="邮箱" placeholder-class="ph" />
			<input class="input" v-model="password" password :placeholder="$t('auth.password')" placeholder-class="ph" />
			<text class="forgot" @click="forgot">{{ $t('auth.forgot') }}</text>
			<view class="btn" @click="submitEmail"><text>{{ $t('auth.continue') }}</text></view>
			<view class="btn apple" @click="appleLogin"><text>{{ $t('auth.apple') }}</text></view>
			<view class="demo" v-if="showDemo" @click="fillDemo"><text>使用演示账号</text></view>
		</template>

		<view class="link" @click="goRegister"><text>{{ $t('auth.register') }}</text></view>
	</view>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import {
	apiLogin, apiSmsSend, apiSmsVerify, apiWechatLogin, apiAppleLogin,
} from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { isFirebaseMock, isSmsMock } from '@/utils/capabilities.js'

const mode = ref('phone')
const phone = ref('')
const code = ref('')
const email = ref('test@spark.app')
const password = ref('SparkTest1')
const codeCooldown = ref(0)
const showDemo = computed(() => isFirebaseMock())
const smsMock = computed(() => isSmsMock())
let cooldownTimer = null

onLoad((q) => {
	if (q && q.tab === 'email') mode.value = 'email'
	else if (q && q.tab === 'phone') mode.value = 'phone'
})

onUnmounted(() => {
	if (cooldownTimer) clearInterval(cooldownTimer)
})

function fillDemo() {
	email.value = 'test@spark.app'
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
		await apiSmsSend({ phone: p })
		uni.showToast({ title: smsMock.value ? '已发送（演示码 000000）' : '验证码已发送', icon: 'none' })
		startCooldown()
	} catch (e) {
		if (smsMock.value) {
			startCooldown()
			uni.showToast({ title: '演示倒计时 · 输入 000000', icon: 'none' })
			return
		}
		uni.showToast({ title: (e && e.message) || '发送失败', icon: 'none' })
	}
}

async function submitPhone() {
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
		track('auth_phone_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '登录失败', icon: 'none' })
	}
}

async function submitEmail() {
	trackClick('auth_login_submit')
	try {
		const res = await apiLogin({ email: email.value, password: password.value, remember: true })
		track('auth_login_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '登录失败', icon: 'none' })
	}
}

async function appleLogin() {
	trackClick('auth_apple')
	try {
		const res = await apiAppleLogin({})
		track('auth_apple_ok')
		afterAuth(res.results || {})
	} catch (e) {
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
		uni.showToast({ title: (e && e.message) || '微信登录暂不可用', icon: 'none' })
	}
}

function forgot() {
	uni.navigateTo({ url: '/pages/auth/forgot' })
}
function goRegister() {
	uni.navigateTo({ url: '/pages/auth/register' })
}
function goPhonePage() {
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
	background: var(--bg, #FFF7FA);
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.back { color:#222; font-size:48rpx; display:block; margin-bottom:24rpx; }
.title {
	display:block; color:#222; font-size:48rpx; font-weight:800; margin-bottom:28rpx;
}
.tabs {
	display:flex; flex-direction:row; background:#fff; border-radius:999rpx; padding:6rpx;
	margin-bottom:28rpx; border: 1px solid rgba(255,107,154,0.2);
}
.tab {
	flex:1; text-align:center; padding:16rpx; border-radius:999rpx;
}
.tab.on { background: linear-gradient(90deg, #FF6B9A, #FF8FB3); }
.tab text { color:#666; font-size:26rpx; font-weight:600; }
.tab.on text { color:#fff; }
.input {
	background: #FFFFFF; border-radius: 20rpx; padding: 28rpx; color: #222;
	margin-bottom: 20rpx; font-size: 28rpx; border: 1px solid rgba(255,107,154,0.25);
}
.code-row { display:flex; flex-direction:row; align-items:center; margin-bottom: 8rpx; }
.input.code { flex:1; margin-bottom:0; margin-right: 12rpx; }
.code-btn {
	background: #FFF0F5; border: 1px solid rgba(255,107,154,0.35);
	border-radius: 20rpx; padding: 28rpx 22rpx; white-space: nowrap;
}
.code-btn text { color:#FF6B9A; font-size:24rpx; font-weight:600; }
.code-btn.disabled { opacity: 0.55; }
.hint { display:block; color:#999; font-size:22rpx; margin-bottom:16rpx; }
.ph { color:#999; }
.forgot { display:block; color:#FF6B9A; font-size:24rpx; margin-bottom:28rpx; }
.btn {
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3); border-radius:999rpx;
	padding: 28rpx; text-align:center; margin-bottom: 16rpx;
}
.btn text { color:#fff; font-weight:700; }
.btn.apple { background: #111; }
.btn.wechat { background: #07C160; }
.demo { text-align:center; margin: 12rpx 0 8rpx; }
.demo text { color:#888; font-size:24rpx; }
.link-row { text-align:center; margin: 8rpx 0 12rpx; }
.link-row text { color:#FF6B9A; font-size:24rpx; }
.link { text-align:center; margin-top: 24rpx; }
.link text { color:#666; }
</style>
