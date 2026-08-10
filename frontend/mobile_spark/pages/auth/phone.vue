<template>
	<view class="page">
		<text class="back" @click="back">‹</text>
		<text class="title spark-serif">{{ $t('auth.phoneTitle') }}</text>
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
				<text>{{ cooldown > 0 ? `${cooldown}s` : (sending ? '…' : $t('auth.sendCode')) }}</text>
			</view>
		</view>

		<text class="hint" v-if="smsMock">{{ $t('auth.smsMockHint') }}</text>

		<view class="btn" :class="{ busy }" @click="verify"><text>{{ busy ? '…' : $t('auth.verifyContinue') }}</text></view>
		<view class="link" @click="goLogin"><text>{{ $t('auth.signInEmail') }}</text></view>
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
const sending = ref(false)
const busy = ref(false)
const cooldown = ref(0)
let timer = null

const smsMock = computed(() => isSmsMock())

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
			cooldown.value = 0
		}
	}, 1000)
}

async function sendCode() {
	if (sending.value || cooldown.value > 0) return
	trackClick('auth_sms_send')
	const p = phone.value.trim()
	if (!p || p.length < 8) {
		uni.showToast({ title: 'Enter a valid phone', icon: 'none' })
		return
	}
	sending.value = true
	try {
		const res = await apiSmsSend({ phone: p })
		const mock = !!(res.results && res.results.mock) || smsMock.value
		startCooldown(60)
		uni.showToast({
			title: mock ? 'Code sent (mock: 000000)' : 'Code sent',
			icon: 'none',
		})
		if (mock && !code.value) code.value = '000000'
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Send failed', icon: 'none' })
	}
	sending.value = false
}

async function verify() {
	if (busy.value) return
	trackClick('auth_phone')
	const p = phone.value.trim()
	const c = code.value.trim()
	if (!p || !c) {
		uni.showToast({ title: 'Phone and code required', icon: 'none' })
		return
	}
	busy.value = true
	try {
		const res = await apiSmsVerify({ phone: p, code: c, remember: true })
		track('auth_sms_ok')
		afterAuth(res.results || {})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Verify failed', icon: 'none' })
	}
	busy.value = false
}

function goLogin() {
	uni.navigateTo({ url: '/pages/auth/login' })
}
function back() {
	uni.navigateBack({ fail: () => uni.reLaunch({ url: '/pages/auth/welcome' }) })
}

onUnmounted(() => {
	if (timer) clearInterval(timer)
})
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: var(--bg, #FFFFFF);
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.back { color: var(--text, #111); font-size:48rpx; display:block; margin-bottom:24rpx; }
.title {
	display: block;
	color: var(--text, #111);
	font-size: 56rpx;
	margin-bottom: 12rpx;
}
.spark-serif { font-family: 'Playfair Display', 'Times New Roman', serif; }
.sub {
	display: block;
	color: var(--muted, #666);
	font-size: 26rpx;
	margin-bottom: 40rpx;
	line-height: 1.4;
}
.input {
	background: #FFF5F7;
	border-radius: 20rpx;
	padding: 28rpx;
	color: #111;
	margin-bottom: 20rpx;
	font-size: 28rpx;
	border: 1px solid rgba(253,38,122,0.22);
	box-sizing: border-box;
}
.code-row {
	display: flex;
	flex-direction: row;
	align-items: center;
	margin-bottom: 12rpx;
}
.code-row .code { flex: 1; margin-bottom: 0; margin-right: 16rpx; }
.send-btn {
	flex-shrink: 0;
	padding: 28rpx 24rpx;
	border-radius: 20rpx;
	background: rgba(253,38,122,0.12);
	border: 1px solid rgba(253,38,122,0.25);
}
.send-btn text { color: #FD267A; font-size: 24rpx; font-weight: 600; }
.send-btn.disabled { opacity: 0.5; }
.ph { color: #999; }
.hint {
	display: block;
	color: #FD267A;
	font-size: 22rpx;
	margin-bottom: 16rpx;
}
.btn {
	margin-top: 20rpx;
	background: linear-gradient(90deg, #FD267A, #FF4458);
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.btn text { color: #fff; font-weight: 600; }
.btn.busy { opacity: 0.7; }
.link { text-align: center; margin-top: 28rpx; }
.link text { color: var(--muted, #666); }
</style>
