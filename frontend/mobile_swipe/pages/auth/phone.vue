<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title">{{ $t('auth.phoneTitle') }}</text>
		<text class="sub">{{ $t('auth.phoneSub') }}</text>
		<input
			class="input"
			v-model="phone"
			type="number"
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
			<view class="send-btn" :class="{ disabled: cooldown > 0 || sending }" @click="sendCode">
				<text>{{ cooldown > 0 ? `${cooldown}s` : $t('auth.sendCode') }}</text>
			</view>
		</view>
		<text class="hint" v-if="mockHint">{{ $t('auth.smsMockHint') }}</text>
		<view class="btn" @click="verify"><text>{{ $t('auth.continue') }}</text></view>
	</view>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { apiSmsSend, apiSmsVerify } from '@/api/auth.js'
import { track, trackClick } from '@/utils/analytics.js'
import { refreshTabBadges } from '@/utils/tabBadges.js'
import { isSmsMock } from '@/utils/capabilities.js'

const phone = ref('')
const code = ref('')
const sending = ref(false)
const cooldown = ref(0)
const mockHint = ref(isSmsMock())
let timer = null

onUnmounted(() => {
	if (timer) clearInterval(timer)
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

function startCooldown(sec = 60) {
	cooldown.value = sec
	if (timer) clearInterval(timer)
	timer = setInterval(() => {
		cooldown.value -= 1
		if (cooldown.value <= 0) {
			clearInterval(timer)
			timer = null
		}
	}, 1000)
}

async function sendCode() {
	if (sending.value || cooldown.value > 0) return
	trackClick('auth_sms_send')
	const p = (phone.value || '').trim()
	if (!p || p.length < 6) {
		uni.showToast({ title: 'Enter a valid phone', icon: 'none' })
		return
	}
	sending.value = true
	try {
		const res = await apiSmsSend({ phone: p })
		const data = res.results || {}
		mockHint.value = !!data.mock || isSmsMock()
		startCooldown(60)
		uni.showToast({
			title: mockHint.value ? 'Code sent (mock: 000000)' : 'Code sent',
			icon: 'none',
		})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Send failed', icon: 'none' })
	}
	sending.value = false
}

async function verify() {
	trackClick('auth_phone')
	const p = (phone.value || '').trim()
	const c = (code.value || '').trim()
	if (!p || !c) {
		uni.showToast({ title: 'Phone and code required', icon: 'none' })
		return
	}
	try {
		const res = await apiSmsVerify({ phone: p, code: c })
		track('auth_sms_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Verify failed', icon: 'none' })
	}
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
	margin-bottom: 12rpx;
}
.sub {
	display: block;
	color: var(--muted, #666);
	font-size: 26rpx;
	margin-bottom: 40rpx;
}
.input {
	background: #FFF8E1;
	border-radius: 20rpx;
	padding: 28rpx;
	color: var(--text, #111);
	margin-bottom: 20rpx;
	font-size: 28rpx;
	border: 1px solid rgba(255,198,41,0.35);
	flex: 1;
}
.ph { color: #999; }
.code-row { display: flex; flex-direction: row; align-items: center; margin-bottom: 12rpx; }
.code-row > view + view, .code-row > input + button { margin-left: 16rpx; }
.code-row .code { margin-bottom: 0; }
.send-btn {
	background: #FFC629;
	border-radius: 999rpx;
	padding: 24rpx 28rpx;
	white-space: nowrap;
}
.send-btn.disabled { opacity: 0.55; }
.send-btn text { color: #111; font-weight: 800; font-size: 24rpx; }
.hint { display: block; color: #B8860B; font-size: 22rpx; margin-bottom: 12rpx; }
.btn {
	margin-top: 20rpx;
	background: #FFC629;
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.btn text { color: #111; font-weight: 800; }
</style>
