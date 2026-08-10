<template>
	<view class="page">
		<view class="hero">
			<view class="photo-grid">
				<view
					v-for="(slot, i) in 6"
					:key="i"
					class="cell"
					:class="{ primary: i === 0, empty: !gridPhotos[i] }"
					@click="goEdit"
				>
					<image v-if="gridPhotos[i]" :src="gridPhotos[i]" class="cell-img" mode="aspectFill" />
					<text v-else class="plus">+</text>
					<view v-if="i === 0 && completeness < 100" class="complete-chip" @click.stop="goEdit">
						<text>{{ completeness }}%</text>
					</view>
				</view>
			</view>
			<view class="identity">
				<image class="bee-mark" src="/static/icons/bee-sm.png" mode="aspectFit" />
				<text class="name display-font">{{ user.nickname || 'Me' }}</text>
				<text class="tier">{{ tierLabel }}</text>
				<view class="progress-wrap">
					<view class="progress-bar"><view class="progress-fill" :style="{ width: completeness + '%' }" /></view>
					<text class="progress-text">Profile {{ completeness }}% complete</text>
				</view>
			</view>
		</view>

		<view class="vip-card" @click="onVipCard">
			<view class="vip-left">
				<text class="vip-title">{{ isVip ? ($t('me.managePlan') + ' · ' + tierLabel) : $t('me.getPremium') }}</text>
				<text class="vip-sub">{{ isVip ? ($t('me.plan') + ': ' + tierLabel) : $t('me.premiumSub') }}</text>
			</view>
			<text class="vip-cta">{{ isVip ? $t('me.manage') : $t('me.upgrade') }}</text>
		</view>
		<view class="card" v-if="isVip" @click="openShop('need_vip')"><text>{{ $t('me.buyMore') }}</text></view>

		<view class="inventory">
			<view class="inv-item" @click="openShop('need_super_like')">
				<text class="inv-label">{{ superLikeLabel() }}</text>
				<text class="inv-val">{{ balances.super_like }}</text>
			</view>
			<view class="inv-item" @click="openShop('need_boost')">
				<text class="inv-label">{{ boostLabel() }}s</text>
				<text class="inv-val">{{ balances.boost }}</text>
			</view>
			<view class="inv-item" @click="openShop('need_extend')">
				<text class="inv-label">Extends</text>
				<text class="inv-val">{{ balances.extend }}</text>
			</view>
			<view class="inv-item" @click="doBoost">
				<text class="inv-label">{{ boostLabel() }}</text>
				<text class="inv-val">⚡</text>
			</view>
		</view>

		<view class="extras">
			<view class="extra" @click="openShop('need_hive')">
				<text class="ex-title">Hive</text>
				<text class="ex-sub">{{ balances.hive ? 'Active' : 'Group events near you' }}</text>
			</view>
			<view class="extra" @click="openShop('need_connect')">
				<text class="ex-title">Connect</text>
				<text class="ex-sub">{{ balances.connect ? 'Boosted' : 'Interest priority' }}</text>
			</view>
			<view class="extra" @click="openShop('need_date_night')">
				<text class="ex-title">Date Night</text>
				<text class="ex-sub">{{ balances.date_night ? 'Unlocked' : 'Ideas for matches' }}</text>
			</view>
			<view class="extra" @click="openShop('need_rematch')">
				<text class="ex-title">Rematch</text>
				<text class="ex-sub">{{ balances.rematch }} left</text>
			</view>
		</view>

		<view class="card" @click="goEdit"><text>{{ $t('me.editProfile') }}</text></view>
		<view class="card" @click="go('/pagesA/features/swipe-night')"><text>Swipe Night</text></view>
		<view class="card" @click="go('/pagesA/features/matchmaker')"><text>Matchmaker</text></view>
		<view class="card" @click="go('/pagesA/features/campus')"><text>Campus</text></view>
		<view class="card" @click="go('/pagesA/features/select')"><text>Select</text></view>
		<view class="card" @click="go('/pagesA/features/face-to-face')"><text>Face to Face</text></view>
		<view class="card" @click="shareProfile"><text>{{ $t('me.shareProfile') }}</text></view>
		<view class="card" @click="inviteFriends"><text>{{ $t('me.inviteFriends') }}</text></view>
		<view class="card" @click="goSettings"><text>{{ $t('me.settings') }}</text></view>
		<view class="card" @click="goVerify"><text>{{ $t('me.verify') }}</text></view>
		<view class="card" @click="goSafety"><text>{{ $t('me.safety') }}</text></view>
		<view class="card" @click="openPolicy('tos')"><text>{{ $t('me.terms') }}</text></view>
		<view class="card" @click="openPolicy('privacy')"><text>{{ $t('me.privacy') }}</text></view>
		<view class="card danger" @click="logout"><text>{{ $t('common.logout') }}</text></view>
		<VipSheet v-model:show="showVip" :reason="vipReason" @purchased="refresh" />
		<SparkTabBar />
	</view>
</template>

<script setup>
import { ref, computed } from 'vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { onShow } from '@dcloudio/uni-app'
import { apiProfileMe } from '@/api/profile.js'
import { apiLogout, apiInviteTrack } from '@/api/auth.js'
import { apiEntitlements, apiBoost } from '@/api/vip.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import { SITE_DOMAIN, PACKAGE_NAME } from '@/config/config.js'
import { tierDisplayName, superLikeLabel, boostLabel } from '@/utils/productProfile.js'
import { openManageSubscriptionsUrl } from '@/utils/capabilities.js'
import { trackClick } from '@/utils/analytics.js'

const user = ref(uni.getStorageSync('userInfo') || {})
const showVip = ref(false)
const vipReason = ref('need_vip')
const balances = ref({
	super_like: 0, boost: 0, rewind: 0, extend: 0, rematch: 0, hive: 0, connect: 0, date_night: 0,
})
const displayTier = ref('')

const tierLabel = computed(() => {
	if (displayTier.value) return displayTier.value
	const t = user.value && user.value.vip_tier
	return !t || t === 'none' ? 'Single' : tierDisplayName(t)
})
const isVip = computed(() => tierLabel.value !== 'Single')

const gridPhotos = computed(() => {
	const u = user.value || {}
	const photos = (u.photos || []).map((p) => p.url || p).filter(Boolean)
	const out = [...photos]
	if (!out.length && u.avatar_url) out.push(u.avatar_url)
	while (out.length < 6) out.push('')
	return out.slice(0, 6)
})

const completeness = computed(() => {
	const u = user.value || {}
	const life = u.lifestyle || {}
	const checks = [
		!!u.nickname,
		!!u.avatar_url || (u.photos && u.photos.length),
		(u.photos || []).length >= 2,
		!!u.bio,
		!!u.job,
		!!u.city,
		!!u.mbti,
		!!u.zodiac,
		!!u.relationship,
		!!(u.interests && u.interests.length),
		!!u.looking_for,
		!!(life.prompts && life.prompts.length) || !!(life.prompt && life.prompt.q),
		!!(life.opening_moves && life.opening_moves.length),
		!!(life.badges && life.badges.length),
	]
	const done = checks.filter(Boolean).length
	return Math.round((done / checks.length) * 100)
})

async function refresh() {
	try {
		const [p, e] = await Promise.all([apiProfileMe(), apiEntitlements()])
		user.value = p.results || {}
		uni.setStorageSync('userInfo', user.value)
		const ent = e.results || {}
		displayTier.value = ent.vip_tier_display || ''
		if (ent.vip_tier) user.value.vip_tier = ent.vip_tier
		const spend = ent.spendable || {}
		balances.value = {
			super_like: spend.super_like || 0,
			boost: spend.boost || 0,
			rewind: spend.rewind || 0,
			extend: spend.extend || 0,
			rematch: spend.rematch || 0,
			hive: spend.hive || 0,
			connect: spend.connect || 0,
			date_night: spend.date_night || 0,
		}
	} catch (err) {
		uni.showToast({ title: 'Failed to refresh profile', icon: 'none' })
	}
}

function openShop(reason) {
	trackClick('open_vip')
	vipReason.value = reason
	showVip.value = true
}

function onVipCard() {
	if (isVip.value) {
		openManageSubscriptionsUrl()
		return
	}
	openShop('need_vip')
}

function profileShareLink() {
	const u = user.value || {}
	const code = u.invite_code || u.id || ''
	return `https://${SITE_DOMAIN}/u/${code}?app=${PACKAGE_NAME}`
}

function shareProfile() {
	const link = profileShareLink()
	const text = `Check out my bee profile: ${link}`
	// #ifdef APP-PLUS
	uni.share({
		provider: 'system',
		type: 1,
		summary: text,
		fail: () => uni.setClipboardData({ data: text }),
	})
	// #endif
	// #ifndef APP-PLUS
	uni.setClipboardData({ data: text })
	uni.showToast({ title: 'Profile link copied', icon: 'none' })
	// #endif
}

async function inviteFriends() {
	const u = user.value || {}
	const code = u.invite_code || String(u.id || '')
	const link = `https://${SITE_DOMAIN}/invite/${code}?app=${PACKAGE_NAME}`
	const text = `Join me on bee — invite code ${code}: ${link}`
	try {
		await apiInviteTrack({ invite_code: code })
	} catch (e) {}
	uni.setClipboardData({ data: text })
	uni.showToast({ title: 'Invite link copied', icon: 'none' })
}

async function doBoost() {
	try {
		await apiBoost()
		uni.showToast({ title: boostLabel() + ' on', icon: 'none' })
		refresh()
	} catch (e) {
		openShop('need_boost')
	}
}

function openPolicy(kind) {
	trackClick('open_legal')
	const boot = uni.getStorageSync('bootstrap') || {}
	const fallback = `https://${SITE_DOMAIN}`
	const url = kind === 'privacy'
		? (boot.privacy_url || `${fallback}/privacy`)
		: (boot.tos_url || `${fallback}/tos`)
	// #ifdef H5
	window.open(url, '_blank')
	// #endif
	// #ifndef H5
	uni.setClipboardData({ data: url })
	uni.showToast({ title: 'Link copied', icon: 'none' })
	// #endif
}

function goEdit() {
	trackClick('edit_profile')
	uni.navigateTo({ url: '/pagesA/me/edit' })
}
function go(url) {
	const featureMap = {
		'/pagesA/features/swipe-night': 'feature_swipe_night',
		'/pagesA/features/matchmaker': 'feature_matchmaker',
		'/pagesA/features/campus': 'feature_campus',
		'/pagesA/features/select': 'feature_select',
		'/pagesA/features/face-to-face': 'feature_face_to_face',
	}
	if (featureMap[url]) trackClick(featureMap[url])
	uni.navigateTo({ url })
}
function goSettings() {
	trackClick('open_settings')
	uni.navigateTo({ url: '/pagesA/me/settings' })
}
function goVerify() {
	trackClick('open_verify')
	uni.navigateTo({ url: '/pagesA/me/verify' })
}
function goSafety() {
	trackClick('open_safety')
	uni.navigateTo({ url: '/pagesA/me/safety' })
}
async function logout() {
	try { await apiLogout() } catch (e) {}
	uni.removeStorageSync('token')
	uni.removeStorageSync('userInfo')
	uni.reLaunch({ url: '/pages/auth/welcome' })
}

onShow(refresh)
</script>

<!-- F-11: gap removed; prefer sibling margin -->
<style scoped>
.page { min-height:100vh; background: var(--bg, #FFFFFF); padding: calc(env(safe-area-inset-top) + 16rpx) 24rpx 160rpx; }
.hero { margin-bottom: 24rpx; }
.photo-grid {
	display: grid;
	grid-template-columns: 2fr 1fr 1fr;
	grid-template-rows: 1fr 1fr;

	height: 420rpx;
	margin-bottom: 20rpx;
}
.cell {
	position: relative; border-radius: 20rpx; overflow: hidden; background: #F3F3F3;
	display:flex; align-items:center; justify-content:center;
}
.cell.primary { grid-row: 1 / span 2; }
.cell-img { width:100%; height:100%; }
.plus { color:#BBB; font-size:48rpx; font-weight:300; }
.complete-chip {
	position:absolute; left:16rpx; bottom:16rpx;
	background: rgba(255,198,41,0.95); border-radius:999rpx; padding: 8rpx 16rpx;
}
.complete-chip text { color:#111; font-size:20rpx; font-weight:800; }
.identity { align-items:center; display:flex; flex-direction:column; }
.bee-mark { width: 48rpx; height: 48rpx; margin-bottom: 8rpx; }
.name { color:#111; font-size:44rpx; font-weight:800; font-family: 'Montserrat', sans-serif; }
.display-font { font-family: 'Montserrat', sans-serif; }
.tier { color:#B8860B; margin-top:8rpx; font-size:24rpx; text-transform: capitalize; font-weight:700; }
.progress-wrap { width: 78%; margin-top: 16rpx; }
.progress-bar { height: 12rpx; background: #EEEEEE; border-radius: 999rpx; overflow: hidden; }
.progress-fill { height: 100%; background: #FFC629; }
.progress-text { display:block; text-align:center; color:#999; font-size:22rpx; margin-top:8rpx; }
.vip-card {
	display:flex; flex-direction:row; align-items:center; justify-content:space-between;
	background: linear-gradient(135deg, #FFF3C4 0%, #FFC629 45%, #FFE082 100%);
	border: 1px solid rgba(255,198,41,0.55);
	border-radius: 28rpx; padding: 32rpx 28rpx; margin-bottom: 20rpx;
}
.vip-title { display:block; color:#111; font-size:32rpx; font-weight:800; margin-bottom:8rpx; }
.vip-sub { display:block; color:#5C4A00; font-size:22rpx; }
.vip-cta {
	color:#111; font-size:24rpx; font-weight:800;
	background: #fff; border-radius:999rpx; padding:14rpx 22rpx;
}
.inventory { display:flex; flex-direction:row; margin-bottom: 16rpx; }
.inv-item {
	flex:1; background:#F7F7F7; border-radius:20rpx; padding:20rpx 8rpx; margin-right:10rpx; text-align:center;
}
.inv-item:last-child { margin-right: 0; }
.inv-label { display:block; color:#999; font-size:18rpx; margin-bottom:8rpx; }
.inv-val { display:block; color:#111; font-size:28rpx; font-weight:700; }
.extras {
	display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom: 16rpx;
}
.extra {
	width: calc(50% - 8rpx); box-sizing: border-box;
	background:#FFF8E1; border-radius:20rpx; padding:22rpx; margin-bottom:12rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.extra:nth-child(odd) { margin-right: 16rpx; }
.ex-title { display:block; color:#111; font-size:26rpx; font-weight:800; margin-bottom:6rpx; }
.ex-sub { display:block; color:#8A6D00; font-size:20rpx; }
.card {
	background:#F7F7F7; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
}
.card text { color:#111; font-size:28rpx; }
.danger text { color:#B8860B; }
</style>
