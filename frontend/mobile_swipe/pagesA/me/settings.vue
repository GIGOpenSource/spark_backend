<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Settings</text>
		</view>

		<text class="section">{{ $t('settings.preferences') }}</text>
		<view class="card" @click="openLang">
			<text>{{ $t('settings.language') }}</text>
			<text class="val">{{ langLabel }} ›</text>
		</view>
		<view class="card" @click="openTheme">
			<text>{{ $t('settings.appearance') }}</text>
			<text class="val">{{ themeLabel }} ›</text>
		</view>
		<view class="card card-switch">
			<view class="row-label">
				<text>{{ $t('settings.invisible') }}</text>
				<text v-if="needPlusLock" class="lock-hint">Premium</text>
			</view>
			<switch :checked="invisible" color="#FFC629" @change="onInvisibleChange" />
		</view>
		<view class="card" @click="go('/pagesA/me/notifications')">
			<text>Notifications</text>
			<text class="val">›</text>
		</view>
		<view class="card" @click="goSocial">
			<text>Social links</text>
			<text class="val">›</text>
		</view>

		<text class="section">Trust & safety</text>
		<view class="card" @click="go('/pagesA/me/verify')">
			<text>Photo verification</text>
			<text class="val">{{ verified ? 'Verified' : '›' }}</text>
		</view>
		<view class="card" @click="go('/pagesA/me/safety')">
			<text>Safety toolkit</text>
			<text class="val">›</text>
		</view>
		<view class="card" @click="showBlocks = !showBlocks">
			<text>Blocked users</text>
			<text class="val">{{ blocks.length }} ›</text>
		</view>
		<view v-if="showBlocks" class="blocks">
			<view v-for="b in blocks" :key="b.id" class="block-row">
				<image :src="b.avatar_url" class="b-avatar" mode="aspectFill" />
				<text class="b-name">{{ b.nickname }}</text>
				<text class="unblock" @click="doUnblock(b)">Unblock</text>
			</view>
			<view v-if="!blocks.length" class="empty"><text>No blocked users</text></view>
		</view>

		<text class="section">Account</text>
		<view class="card" @click="bindGoogle">
			<text>Google account</text>
			<text class="val">{{ googleBound ? (showFirebaseMock ? 'Bound (demo)' : 'Bound · tap to unbind') : (showFirebaseMock ? 'Bind (demo)' : 'Bind') }}</text>
		</view>
		<view class="card" @click="restore">
			<text>Restore purchases</text>
			<text class="val">{{ restoring ? '…' : (showIapMock ? 'Demo' : '›') }}</text>
		</view>
		<view class="card" @click="go('/pagesA/me/legal')">
			<text>Legal & data</text>
			<text class="val">›</text>
		</view>

		<view class="card danger" @click="logout">
			<text>Log out</text>
		</view>

		<view class="sheet-mask" v-if="showLang" @click="showLang = false">
			<view class="lang-sheet" @click.stop>
				<text class="sheet-title">{{ $t('settings.language') }}</text>
				<view class="lang-chips">
					<view class="lang-chip" :class="{ on: localePref === 'device' }" @click="pickLang('device')">
						<text>Follow system</text>
					</view>
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

		<view class="sheet-mask" v-if="showTheme" @click="showTheme = false">
			<view class="lang-sheet" @click.stop>
				<text class="sheet-title">{{ $t('settings.appearance') }}</text>
				<view class="lang-chips">
					<view class="lang-chip" :class="{ on: themePref === 'system' }" @click="pickTheme('system')">
						<text>{{ $t('settings.themeSystem') }}</text>
					</view>
					<view class="lang-chip" :class="{ on: themePref === 'light' }" @click="pickTheme('light')">
						<text>{{ $t('settings.themeLight') }}</text>
					</view>
					<view class="lang-chip" :class="{ on: themePref === 'dark' }" @click="pickTheme('dark')">
						<text>{{ $t('settings.themeDark') }}</text>
					</view>
				</view>
			</view>
		</view>

		<VipSheet v-model:show="showVip" reason="need_plus" @purchased="onVip" />
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiProfileMe, apiProfileUpdate, apiBlocks, apiUnblock } from '@/api/profile.js'
import { apiRestorePurchases } from '@/api/vip.js'
import { apiLogout, apiBootstrap, apiGoogleBind, apiGoogleUnbind } from '@/api/auth.js'
import { APP_ID, PACKAGE_NAME, USE_IAP_MOCK, USE_FIREBASE_MOCK } from '@/config/config.js'
import { isIapMock, isFirebaseMock } from '@/utils/capabilities.js'
import { setLocale } from '@/i18n/index.js'
import { getThemePref, setThemePref, resolveTheme } from '@/utils/theme.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import { trackClick } from '@/utils/analytics.js'

const LANGS = [
	{ code: 'en', label: 'English' },
	{ code: 'zh', label: '中文' },
	{ code: 'ja', label: '日本語' },
	{ code: 'ko', label: '한국어' },
	{ code: 'es', label: 'Español' },
	{ code: 'pt', label: 'Português' }
]

const invisible = ref(false)
const needPlusLock = ref(false)
const blocks = ref([])
const showBlocks = ref(false)
const showVip = ref(false)
const showLang = ref(false)
const showTheme = ref(false)
const localePref = ref('device')
const themePref = ref(getThemePref())
const restoring = ref(false)
const showIapMock = computed(() => isIapMock() || !!USE_IAP_MOCK)
const showFirebaseMock = computed(() => isFirebaseMock() || !!USE_FIREBASE_MOCK)
const googleBound = ref(!!(uni.getStorageSync('userInfo') || {}).firebase_uid)
const verified = ref(!!(uni.getStorageSync('userInfo') || {}).is_verified)

const langLabel = computed(() => {
	if (localePref.value === 'device') {
		const resolved = resolveLocale('device')
		const hit = LANGS.find((x) => x.code === resolved)
		const name = (hit && hit.label) || resolved
		return `Follow system · ${name}`
	}
	const hit = LANGS.find((x) => x.code === localePref.value)
	return (hit && hit.label) || localePref.value
})

const themeLabel = computed(() => {
	const map = { system: 'System', light: 'Light', dark: 'Dark' }
	const pref = themePref.value || 'system'
	if (pref === 'system') return `System · ${resolveTheme('system')}`
	return map[pref] || pref
})

onLoad((q) => {
	if (q && q.focus === 'blocks') showBlocks.value = true
})

onMounted(async () => {
	await ensureBootstrap()
	const res = await apiProfileMe()
	const u = res.results || {}
	invisible.value = !!u.invisible_mode
	needPlusLock.value = !(u.vip_tier && u.vip_tier !== 'none')
	googleBound.value = !!(u.firebase_uid)
	verified.value = !!u.is_verified
	const stored = uni.getStorageSync('user_locale_preference')
	localePref.value = stored || 'device'
	const resolved = resolveLocale(localePref.value)
	uni.setStorageSync('currentLanguage', resolved)
	loadBlocks()
})

async function ensureBootstrap() {
	let boot = uni.getStorageSync('bootstrap') || {}
	if (!boot.tos_url || !boot.privacy_url) {
		try {
			const res = await apiBootstrap({ app_id: APP_ID, platform: 'h5', package_name: PACKAGE_NAME, app_version: '1.0.0' })
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
		uni.showToast({ title: 'Failed to load blocks', icon: 'none' })
	}
}

function resolveLocale(code) {
	if (code && code !== 'device') return code
	try {
		const sys = uni.getSystemInfoSync()
		const raw = (sys.language || sys.osLanguage || 'en').toString()
		return raw.split('-')[0] || 'en'
	} catch (e) {
		return 'en'
	}
}

function pickLang(code) {
	localePref.value = code
	const resolved = resolveLocale(code)
	uni.setStorageSync('user_locale_preference', code)
	uni.setStorageSync('currentLanguage', resolved)
	setLocale(resolved)
	showLang.value = false
	uni.showToast({ title: 'Language updated', icon: 'none' })
}

function pickTheme(pref) {
	themePref.value = pref
	setThemePref(pref)
	showTheme.value = false
	uni.showToast({ title: 'Appearance updated', icon: 'none' })
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
		uni.showToast({ title: next ? 'Invisible on' : 'Invisible off', icon: 'none' })
	} catch (e) {
		if (e && (e.message === 'need_plus' || (e.data && e.data.need_vip) || (e.results && e.results.need_vip))) {
			showVip.value = true
		} else {
			uni.showToast({ title: (e && e.message) || 'Update failed', icon: 'none' })
		}
	}
}

async function doUnblock(b) {
	await apiUnblock(b.id)
	blocks.value = blocks.value.filter((x) => x.id !== b.id)
	uni.showToast({ title: 'Unblocked', icon: 'none' })
}

function onVip() {
	needPlusLock.value = false
	setInvisible(!invisible.value)
}

function goSocial() {
	trackClick('settings_accounts')
	uni.navigateTo({ url: '/pagesA/me/edit?focus=social' })
}

function go(url) {
	const map = {
		'/pagesA/me/notifications': 'open_notifications',
		'/pagesA/me/verify': 'open_verify',
		'/pagesA/me/safety': 'open_safety',
		'/pagesA/me/legal': 'open_legal',
	}
	if (map[url]) trackClick(map[url])
	uni.navigateTo({ url })
}

async function bindGoogle() {
	trackClick('settings_accounts')
	if (googleBound.value) {
		uni.showModal({
			title: 'Unbind Google?',
			success: async (m) => {
				if (!m.confirm) return
				try {
					await apiGoogleUnbind()
					googleBound.value = false
					uni.showToast({ title: 'Unbound', icon: 'none' })
				} catch (e) {
					uni.showToast({ title: (e && e.message) || 'Unbind failed', icon: 'none' })
				}
			},
		})
		return
	}
	try {
		const payload = showFirebaseMock.value
			? { email: (uni.getStorageSync('userInfo') || {}).email || `bind.${Date.now()}@swipe.app` }
			: {}
		const res = await apiGoogleBind(payload)
		googleBound.value = !!(res.results && res.results.bound)
		uni.showToast({ title: showFirebaseMock.value ? 'Google bound (demo)' : 'Google bound', icon: 'none' })
	} catch (e) {
		uni.showToast({
			title: (e && e.message) || (showFirebaseMock.value ? 'Bind failed' : 'Google SDK required'),
			icon: 'none',
		})
	}
}

async function restore() {
	if (restoring.value) return
	restoring.value = true
	try {
		const res = await apiRestorePurchases()
		const tier = (res.results && res.results.vip_tier) || 'none'
		uni.showToast({
			title: tier && tier !== 'none' ? `Restored · ${tier}` : (showIapMock.value ? 'Purchases restored (demo)' : 'Purchases restored'),
			icon: 'none'
		})
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Restore failed', icon: 'none' })
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
	showTheme.value = true
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFFDF6; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { display:block; color:#111; font-size:40rpx; font-weight:800; }
.section {
	display:block; color:#888; font-size:22rpx; letter-spacing:1rpx;
	text-transform:uppercase; margin: 28rpx 8rpx 12rpx;
}
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(255,198,41,0.25);
}
.card text { color:#111; font-size:28rpx; }
.card.danger { margin-top: 32rpx; }
.card.danger text { color:#C0392B; }
.card-switch { cursor:default; }
.row-label { display:flex; flex-direction:column; flex:1; }
.row-label > text + text, .row-label > view + view { margin-top: 4rpx; }
.lock-hint { color:#999; font-size:22rpx; }
.val { color:#999; }
.blocks { margin-bottom: 20rpx; }
.block-row {
	display:flex; flex-direction:row; align-items:center;
	background:#fff; border-radius:16rpx; padding:16rpx; margin-bottom:10rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.b-avatar { width:64rpx; height:64rpx; border-radius:50%; margin-right:16rpx; }
.b-name { flex:1; color:#111; font-size:26rpx; }
.unblock { color:#B8860B; font-size:24rpx; font-weight:700; }
.empty { padding:20rpx; text-align:center; color:#888; }
.sheet-mask {
	position:fixed; inset:0; background:rgba(0,0,0,0.35);
	display:flex; flex-direction:column; justify-content:flex-end; z-index:999;
}
.lang-sheet {
	background:#FFFDF6; border-radius:32rpx 32rpx 0 0;
	padding: 32rpx 28rpx calc(env(safe-area-inset-bottom) + 32rpx);
}
.sheet-title { display:block; color:#111; font-size:32rpx; font-weight:700; margin-bottom:24rpx; }
.lang-chips { display:flex; flex-direction:row; flex-wrap:wrap }
.lang-chips > view + view, .lang-chips > text + text { margin-left: 16rpx; }
.lang-chip {
	padding:16rpx 28rpx; border-radius:999rpx;
	background:#fff; border:1px solid rgba(255,198,41,0.35);
}
.lang-chip text { color:#333; font-size:26rpx; }
.lang-chip.on { background:#FFC629; border-color:#FFC629; }
.lang-chip.on text { color:#111; font-weight:600; }
</style>
