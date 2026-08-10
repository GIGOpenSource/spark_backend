<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">设置</text>
		</view>

		<text class="section">{{ $t('settings.preferences') }}</text>
		<view class="card" @click="openLang">
			<text>{{ $t('settings.language') }}</text>
			<text class="val">{{ langLabel }} ›</text>
		</view>
		<view class="card" @click="openTheme">
			<text>{{ $t('settings.appearance') }}</text>
			<text class="val">{{ appearanceLabel }} ›</text>
		</view>
		<view class="card card-switch">
			<view class="row-label">
				<text>隐身模式</text>
				<text v-if="needPlusLock" class="lock-hint">会员</text>
			</view>
			<switch :checked="invisible" color="#FF6B9A" @change="onInvisibleChange" />
		</view>
		<view class="card" @click="goSocial">
			<text>社交账号</text>
			<text class="val">›</text>
		</view>
		<view class="card" @click="goNotif">
			<text>通知设置</text>
			<text class="val">›</text>
		</view>

		<text class="section">信任与安全</text>
		<view class="card" @click="goSafety">
			<text>{{ $t('settings.safety') }}</text>
			<text class="val">›</text>
		</view>
		<view class="card" @click="goVerify">
			<text>真人认证</text>
			<text class="val">›</text>
		</view>
		<view class="card" @click="showBlocks = !showBlocks">
			<text>黑名单</text>
			<text class="val">{{ blocks.length }} ›</text>
		</view>
		<view v-if="showBlocks" class="blocks">
			<view v-for="b in blocks" :key="b.id" class="block-row">
				<image :src="b.avatar_url" class="b-avatar" mode="aspectFill" />
				<text class="b-name">{{ b.nickname }}</text>
				<text class="unblock" @click="doUnblock(b)">解除</text>
			</view>
			<view v-if="!blocks.length" class="empty"><text>暂无拉黑用户</text></view>
		</view>

		<text class="section">账号</text>
		<view class="card" @click="onWechat">
			<text>微信账号</text>
			<text class="val">{{ wechatBound ? '已绑定 · 解绑' : '绑定' }}</text>
		</view>
		<view class="card" @click="onApple">
			<text>Apple 账号</text>
			<text class="val">{{ appleBound ? '已绑定 · 解绑' : '绑定' }}</text>
		</view>
		<view class="card muted-card" @click="onGoogle">
			<text>Google 账号</text>
			<text class="val">{{ googleBound ? '已绑定' : '可选' }}</text>
		</view>
		<view class="card" @click="restore">
			<text>恢复购买</text>
			<text class="val">{{ restoring ? '…' : (iapMock ? '演示' : '›') }}</text>
		</view>
		<view class="card" @click="goLegal">
			<text>法律与数据</text>
			<text class="val">›</text>
		</view>

		<view class="card danger" @click="logout">
			<text>退出登录</text>
		</view>

		<view class="sheet-mask" v-if="showLang" @click="showLang = false">
			<view class="lang-sheet" @click.stop>
				<text class="sheet-title">{{ $t('settings.language') }}</text>
				<view class="lang-chips">
					<view
						v-for="l in LANGS"
						:key="l.code"
						class="lang-chip"
						:class="{ on: localePref === l.code }"
						@click="pickLang(l.code)"
					>
						<text>{{ l.label }}</text>
					</view>
				</view>
			</view>
		</view>

		<view class="sheet-mask" v-if="showAppearance" @click="showAppearance = false">
			<view class="lang-sheet" @click.stop>
				<text class="sheet-title">{{ $t('settings.appearance') }}</text>
				<view class="lang-chips">
					<view
						v-for="a in APPEARANCES"
						:key="a.code"
						class="lang-chip"
						:class="{ on: themePref === a.code }"
						@click="pickAppearance(a.code)"
					>
						<text>{{ a.label }}</text>
					</view>
				</view>
			</view>
		</view>

		<VipSheet v-model:show="showVip" reason="need_plus" @purchased="onVip" />
	</view>
</template>

<script setup>
import { ref, computed, onMounted, getCurrentInstance } from 'vue'
import { apiProfileMe, apiProfileUpdate, apiBlocks, apiUnblock } from '@/api/profile.js'
import { apiRestorePurchases } from '@/api/vip.js'
import {
	apiLogout, apiBootstrap, apiGoogleBind, apiGoogleUnbind,
	apiWechatBind, apiWechatUnbind, apiAppleBind, apiAppleUnbind,
} from '@/api/auth.js'
import { APP_ID, PACKAGE_NAME } from '@/config/config.js'
import { isIapMock, isFirebaseMock } from '@/utils/capabilities.js'
import { getThemePref, setThemePref, applyTheme } from '@/utils/theme.js'
import { setLocale } from '@/i18n/index.js'
import { trackClick } from '@/utils/analytics.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'

const LANGS = [
	{ code: 'zh', label: '中文' },
	{ code: 'en', label: 'English' },
]
const APPEARANCES = [
	{ code: 'system', label: '跟随系统' },
	{ code: 'light', label: '浅色' },
	{ code: 'dark', label: '深色' },
]

const invisible = ref(false)
const needPlusLock = ref(false)
const blocks = ref([])
const showBlocks = ref(false)
const showVip = ref(false)
const showLang = ref(false)
const showAppearance = ref(false)
const localePref = ref('zh')
const themePref = ref('system')
const restoring = ref(false)
const iapMock = computed(() => isIapMock())
const firebaseMock = computed(() => isFirebaseMock())
const googleBound = ref(!!(uni.getStorageSync('userInfo') || {}).firebase_uid || !!uni.getStorageSync('google_bound_mock'))
const wechatBound = ref(!!(uni.getStorageSync('userInfo') || {}).wechat_openid || !!uni.getStorageSync('wechat_bound_mock'))
const appleBound = ref(!!uni.getStorageSync('apple_bound_mock'))

const langLabel = computed(() => {
	if (localePref.value === 'en') return 'English'
	return '中文'
})
const appearanceLabel = computed(() => {
	const hit = APPEARANCES.find((a) => a.code === themePref.value)
	return (hit && hit.label) || '跟随系统'
})

function setI18nLocale(code) {
	try {
		const proxy = getCurrentInstance()?.proxy
		if (proxy && proxy.$i18n) proxy.$i18n.locale = code
	} catch (e) {}
	try {
		const app = getApp && getApp()
		if (app && app.$i18n) {
			if (app.$i18n.locale && typeof app.$i18n.locale === 'object' && 'value' in app.$i18n.locale) {
				app.$i18n.locale.value = code
			} else {
				app.$i18n.locale = code
			}
		}
	} catch (e) {}
}

onMounted(async () => {
	await ensureBootstrap()
	try {
		const res = await apiProfileMe()
		const u = res.results || {}
		invisible.value = !!u.invisible_mode
		needPlusLock.value = !(u.vip_tier && u.vip_tier !== 'none')
		googleBound.value = !!(u.firebase_uid)
	} catch (e) {}
	const stored = uni.getStorageSync('user_locale_preference') || uni.getStorageSync('currentLanguage') || 'zh'
	localePref.value = stored === 'device' ? 'zh' : stored
	uni.setStorageSync('currentLanguage', resolveLocale(localePref.value))
	setI18nLocale(resolveLocale(localePref.value))
	themePref.value = getThemePref()
	applyTheme(themePref.value)
	loadBlocks()
})

async function ensureBootstrap() {
	let boot = uni.getStorageSync('bootstrap') || {}
	if (!boot.tos_url || !boot.privacy_url) {
		try {
			const res = await apiBootstrap({
				app_id: APP_ID, platform: 'h5', package_name: PACKAGE_NAME, app_version: '1.0.0',
			})
			boot = res.results || {}
			uni.setStorageSync('bootstrap', boot)
		} catch (e) {}
	}
}

async function loadBlocks() {
	try {
		const res = await apiBlocks()
		blocks.value = (res.results && res.results.list) || []
	} catch (e) {
		uni.showToast({ title: '加载失败', icon: 'none' })
	}
}

function resolveLocale(code) {
	if (code && code !== 'device') return code
	try {
		const sys = uni.getSystemInfoSync()
		const raw = (sys.language || sys.osLanguage || 'zh').toString()
		return raw.split('-')[0] || 'zh'
	} catch (e) {
		return 'zh'
	}
}

function pickLang(code) {
	localePref.value = code
	uni.setStorageSync('user_locale_preference', code)
	const resolved = resolveLocale(code)
	uni.setStorageSync('currentLanguage', resolved)
	setLocale(resolved)
	setI18nLocale(resolved)
	showLang.value = false
	uni.showToast({ title: '语言已更新', icon: 'none' })
}

function pickAppearance(code) {
	themePref.value = code
	setThemePref(code)
	showAppearance.value = false
	uni.showToast({ title: '外观已更新', icon: 'none' })
}

function onInvisibleChange(e) {
	const next = e.detail.value
	if (next === invisible.value) return
	setInvisible(next)
}

async function setInvisible(next) {
	try {
		await apiProfileUpdate({ invisible_mode: next })
		invisible.value = next
		needPlusLock.value = false
		uni.showToast({ title: next ? '已开启隐身' : '已关闭隐身', icon: 'none' })
	} catch (e) {
		if (e && (e.message === 'need_plus' || (e.data && e.data.need_vip) || (e.results && e.results.need_vip))) {
			showVip.value = true
		} else {
			uni.showToast({ title: (e && e.message) || '更新失败', icon: 'none' })
		}
	}
}

async function doUnblock(b) {
	await apiUnblock(b.id)
	blocks.value = blocks.value.filter((x) => x.id !== b.id)
	uni.showToast({ title: '已解除拉黑', icon: 'none' })
}

function onVip() {
	needPlusLock.value = false
	setInvisible(!invisible.value)
}

function goSocial() {
	trackClick('settings_accounts')
	uni.navigateTo({ url: '/pagesA/me/edit?focus=social' })
}
function goNotif() {
	trackClick('open_notifications')
	uni.navigateTo({ url: '/pagesA/me/notifications' })
}
function goVerify() {
	trackClick('open_verify')
	uni.navigateTo({ url: '/pagesA/me/verify' })
}
function goLegal() {
	trackClick('open_legal')
	uni.navigateTo({ url: '/pagesA/me/legal' })
}
function goSafety() {
	trackClick('open_safety')
	uni.navigateTo({ url: '/pagesA/me/safety' })
}

async function onWechat() {
	trackClick('settings_accounts')
	if (wechatBound.value) {
		uni.showModal({
			title: '解绑微信',
			content: '解绑后仍可用手机号或邮箱登录。',
			success: async (m) => {
				if (!m.confirm) return
				try {
					await apiWechatUnbind()
					wechatBound.value = false
					uni.removeStorageSync('wechat_bound_mock')
					uni.showToast({ title: '已解绑', icon: 'none' })
				} catch (e) {
					wechatBound.value = false
					uni.removeStorageSync('wechat_bound_mock')
					uni.showToast({ title: '已解绑（本地）', icon: 'none' })
				}
			},
		})
		return
	}
	try {
		await apiWechatBind({ code: `mock_bind_${Date.now()}` })
		wechatBound.value = true
		uni.setStorageSync('wechat_bound_mock', true)
		uni.showToast({ title: '已绑定微信', icon: 'none' })
	} catch (e) {
		wechatBound.value = true
		uni.setStorageSync('wechat_bound_mock', true)
		uni.showToast({ title: '已绑定微信（演示）', icon: 'none' })
	}
}

async function onApple() {
	trackClick('settings_accounts')
	if (appleBound.value) {
		uni.showModal({
			title: '解绑 Apple',
			content: '解绑后仍可用其他方式登录。',
			success: async (m) => {
				if (!m.confirm) return
				try {
					await apiAppleUnbind()
					appleBound.value = false
					uni.removeStorageSync('apple_bound_mock')
					uni.showToast({ title: '已解绑', icon: 'none' })
				} catch (e) {
					uni.showToast({ title: (e && e.message) || '解绑失败', icon: 'none' })
				}
			},
		})
		return
	}
	try {
		await apiAppleBind({})
		appleBound.value = true
		uni.showToast({ title: firebaseMock.value ? '已绑定（演示）' : '已绑定', icon: 'none' })
	} catch (e) {
		if (firebaseMock.value) {
			appleBound.value = true
			uni.setStorageSync('apple_bound_mock', true)
			uni.showToast({ title: '已绑定 Apple（演示）', icon: 'none' })
		} else {
			uni.showToast({ title: (e && e.message) || '需要原生 Apple SDK', icon: 'none' })
		}
	}
}

async function onGoogle() {
	trackClick('settings_accounts')
	if (googleBound.value) {
		uni.showModal({
			title: '解绑 Google',
			content: '解绑后仍可用邮箱登录。',
			success: async (m) => {
				if (!m.confirm) return
				try {
					await apiGoogleUnbind()
					googleBound.value = false
					uni.removeStorageSync('google_bound_mock')
					uni.showToast({ title: '已解绑', icon: 'none' })
				} catch (e) {
					uni.showToast({ title: (e && e.message) || '解绑失败', icon: 'none' })
				}
			},
		})
		return
	}
	try {
		await apiGoogleBind({})
		googleBound.value = true
		uni.showToast({ title: firebaseMock.value ? '已绑定（演示）' : '已绑定', icon: 'none' })
	} catch (e) {
		if (firebaseMock.value) {
			googleBound.value = true
			uni.setStorageSync('google_bound_mock', true)
			uni.showToast({ title: '已绑定 Google（演示）', icon: 'none' })
		} else {
			uni.showToast({ title: (e && e.message) || '需要原生 Google SDK', icon: 'none' })
		}
	}
}

async function restore() {
	if (restoring.value) return
	restoring.value = true
	try {
		const res = await apiRestorePurchases()
		const tier = (res.results && res.results.vip_tier) || 'none'
		uni.showToast({
			title: tier && tier !== 'none' ? `已恢复 · ${tier}` : (iapMock.value ? '已恢复（演示）' : '购买已恢复'),
			icon: 'none',
		})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || (iapMock.value ? '已恢复（演示）' : '恢复失败'), icon: 'none' })
	}
	restoring.value = false
}

async function logout() {
	trackClick('settings_logout')
	try { await apiLogout() } catch (e) {}
	uni.removeStorageSync('token')
	uni.removeStorageSync('userInfo')
	uni.reLaunch({ url: '/pages/auth/welcome' })
}

function openLang() {
	trackClick('settings_language')
	showLang.value = true
}

function openTheme() {
	trackClick('settings_theme')
	showAppearance.value = true
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFF7FA; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#222; font-size:48rpx; width:60rpx; }
.title { display:block; color:#222; font-size:40rpx; font-weight:700; }
.section {
	display:block; color:#999; font-size:22rpx; letter-spacing:1rpx;
	margin: 28rpx 8rpx 12rpx;
}
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(255,107,154,0.12);
}
.card text { color:#222; font-size:28rpx; }
.card.danger { margin-top: 32rpx; }
.card.danger text { color:#FF6B9A; }
.row-label { display:flex; flex-direction:column; flex:1; }
.lock-hint { color:#999; font-size:22rpx; margin-top:4rpx; }
.val { color:#999; }
.blocks { margin-bottom: 20rpx; }
.block-row {
	display:flex; flex-direction:row; align-items:center;
	background:#fff; border-radius:16rpx; padding:16rpx; margin-bottom:10rpx;
}
.b-avatar { width:64rpx; height:64rpx; border-radius:50%; margin-right:16rpx; }
.b-name { flex:1; color:#222; font-size:26rpx; }
.unblock { color:#FF6B9A; font-size:24rpx; }
.empty { padding:20rpx; text-align:center; color:#999; }
.sheet-mask {
	position:fixed; inset:0; background:rgba(0,0,0,0.35);
	display:flex; flex-direction:column; justify-content:flex-end; z-index:999;
}
.lang-sheet {
	background:#FFF7FA; border-radius:32rpx 32rpx 0 0;
	padding: 32rpx 28rpx calc(env(safe-area-inset-bottom) + 32rpx);
}
.sheet-title { display:block; color:#222; font-size:32rpx; font-weight:700; margin-bottom:24rpx; }
.lang-chips { display:flex; flex-direction:row; flex-wrap:wrap; }
.lang-chip {
	padding:16rpx 28rpx; border-radius:999rpx; margin-right:16rpx; margin-bottom:16rpx;
	background:#fff; border:1px solid rgba(255,107,154,0.2);
}
.lang-chip text { color:#333; font-size:26rpx; }
.lang-chip.on { background:#FF6B9A; border-color:#FF6B9A; }
.lang-chip.on text { color:#fff; }
.lang-chip.secondary { opacity: 0.75; }
.muted-card { opacity: 0.72; }
</style>
