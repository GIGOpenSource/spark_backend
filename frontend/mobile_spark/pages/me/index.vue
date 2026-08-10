<template>
	<view class="page">
		<view class="header">
			<image :src="user.avatar_url || placeholder" class="avatar" mode="aspectFill" />
			<text class="name spark-serif">{{ user.nickname || 'Me' }}</text>
			<text class="tier">{{ tierLabel }}</text>
			<view class="progress-wrap">
				<view class="progress-bar"><view class="progress-fill" :style="{ width: completeness + '%' }" /></view>
				<text class="progress-text">{{ $t('me.profileComplete', { n: completeness }) }}</text>
			</view>
		</view>

		<view class="vip-card" @click="onVipCard">
			<view class="vip-left">
				<text class="vip-title">{{ isVip ? $t('me.manageSub') : ('Get ' + goldName) }}</text>
				<text class="vip-sub">{{ isVip ? ('Plan: ' + tierLabel) : 'See who likes you · Rewind · Boost' }}</text>
			</view>
			<text class="vip-cta">{{ isVip ? $t('me.manage') : $t('me.upgrade') }}</text>
		</view>
		<view class="card" v-if="isVip" @click="openShop('need_gold')">
			<text>{{ $t('me.buyUpgrade') }}</text>
			<text class="val">›</text>
		</view>

		<view class="inventory">
			<view class="inv-item" @click="openShop('need_super_like')">
				<text class="inv-label">{{ superLikeLabel() }}</text>
				<text class="inv-val">{{ balances.super_like }}</text>
			</view>
			<view class="inv-item" @click="openShop('need_boost')">
				<text class="inv-label">{{ boostLabel() }}s</text>
				<text class="inv-val">{{ balances.boost }}</text>
			</view>
			<view class="inv-item" @click="openShop('need_rewind')">
				<text class="inv-label">Rewinds</text>
				<text class="inv-val">{{ balances.rewind }}</text>
			</view>
			<view class="inv-item" @click="openShop('need_likes_unlock')">
				<text class="inv-label">Unlocks</text>
				<text class="inv-val">{{ balances.likes_unlock || 0 }}</text>
			</view>
		</view>

		<text class="sec">Features</text>
		<view class="card" @click="go('/pagesA/features/swipe-night')"><text>Swipe Night</text></view>
		<view class="card" @click="go('/pagesA/features/matchmaker')"><text>Matchmaker</text></view>
		<view class="card" @click="go('/pagesA/features/campus')"><text>Campus</text></view>
		<view class="card" @click="go('/pagesA/features/select')"><text>Select</text></view>
		<view class="card" @click="go('/pagesA/features/face-to-face')"><text>Face to Face</text></view>
		<view class="card" @click="openBoostReport"><text>Boost report</text></view>

		<view class="card" @click="goEdit"><text>{{ $t('me.editProfile') }}</text></view>
		<view class="card" @click="goPreview"><text>{{ $t('me.preview') }}</text></view>
		<view class="card" @click="shareProfile"><text>{{ $t('me.shareProfile') }}</text></view>
		<view class="card" @click="inviteFriends"><text>{{ $t('me.inviteFriends') }}</text></view>
		<view class="card" @click="goSettings"><text>{{ $t('me.settings') }}</text></view>
		<view class="card" @click="openPolicy('tos')"><text>{{ $t('me.terms') }}</text></view>
		<view class="card" @click="openPolicy('privacy')"><text>{{ $t('me.privacy') }}</text></view>
		<view class="card danger" @click="logout"><text>{{ $t('me.logout') }}</text></view>
		<VipSheet v-model:show="showVip" :reason="vipReason" @purchased="refresh" />
		<SparkTabBar :current="3" />
	</view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiProfileMe } from '@/api/profile.js'
import { apiLogout, apiInviteTrack } from '@/api/auth.js'
import { apiEntitlements, apiBoost, apiBoostReport } from '@/api/vip.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import SparkTabBar from '@/components/SparkTabBar/SparkTabBar.vue'
import { tierDisplayName, superLikeLabel, boostLabel } from '@/utils/productProfile.js'
import { detectStorePlatform } from '@/utils/capabilities.js'
import { SITE_DOMAIN, PACKAGE_NAME } from '@/config/config.js'
import { trackClick } from '@/utils/analytics.js'

const user = ref(uni.getStorageSync('userInfo') || {})
const showVip = ref(false)
const vipReason = ref('need_vip')
const balances = ref({ super_like: 0, boost: 0, rewind: 0, likes_unlock: 0 })
const displayTier = ref('')
const placeholder = 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400'

const tierLabel = computed(() => {
	if (displayTier.value) return displayTier.value
	const t = user.value && user.value.vip_tier
	return !t || t === 'none' ? 'Free' : tierDisplayName(t)
})
const isVip = computed(() => tierLabel.value !== 'Free')
const goldName = tierDisplayName('gold')

const completeness = computed(() => {
	const u = user.value || {}
	const checks = [
		!!u.nickname, !!u.avatar_url || (u.photos && u.photos.length),
		!!u.bio, !!u.job, !!u.city, !!u.mbti, !!u.zodiac, !!u.relationship,
		!!(u.interests && u.interests.length), !!u.looking_for
	]
	const done = checks.filter(Boolean).length
	return Math.round((done / checks.length) * 100)
})

function inviteLink() {
	const code = user.value.invite_code || ''
	const base = `https://${SITE_DOMAIN}/invite`
	return code ? `${base}?code=${encodeURIComponent(code)}` : base
}

async function refresh() {
	try {
		const [p, e] = await Promise.all([apiProfileMe(), apiEntitlements()])
		user.value = p.results || {}
		uni.setStorageSync('userInfo', user.value)
		const ent = e.results || {}
		balances.value = (ent.spendable) || balances.value
		displayTier.value = ent.vip_tier_display || ''
		if (ent.vip_tier) user.value.vip_tier = ent.vip_tier
		const bal = (e.results && e.results.balances) || {}
		const spend = (e.results && e.results.spendable) || null
		if (spend) {
			balances.value = {
				super_like: spend.super_like || 0,
				boost: spend.boost || 0,
				rewind: spend.rewind || 0,
				likes_unlock: spend.likes_unlock || 0,
			}
		} else {
			balances.value = { super_like: 0, boost: 0, rewind: 0 }
			Object.keys(bal).forEach((k) => {
				if (k.includes('vip_')) return
				const v = bal[k] || 0
				if (k.startsWith('super_like')) balances.value.super_like += v
				if (k.startsWith('boost')) balances.value.boost += v
				if (k.startsWith('rewind')) balances.value.rewind += v
			})
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
		openManageSubscription()
	} else {
		openShop('need_gold')
	}
}

function openManageSubscription() {
	const platform = detectStorePlatform()
	let url = ''
	if (platform === 'ios') {
		url = 'https://apps.apple.com/account/subscriptions'
	} else if (platform === 'android') {
		url = `https://play.google.com/store/account/subscriptions?package=${PACKAGE_NAME || 'app.spark'}`
	}
	if (!url) {
		openShop('need_gold')
		return
	}
	// #ifdef H5
	window.open(url, '_blank')
	// #endif
	// #ifdef APP-PLUS
	try {
		plus.runtime.openURL(url)
		return
	} catch (e) {}
	// #endif
	// #ifndef H5
	uni.setClipboardData({ data: url })
	uni.showToast({ title: 'Subscriptions link copied', icon: 'none' })
	// #endif
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
	const boot = uni.getStorageSync('bootstrap') || {}
	const url = kind === 'privacy' ? (boot.privacy_url || 'https://spark.app/privacy') : (boot.tos_url || 'https://spark.app/tos')
	// #ifdef H5
	window.open(url, '_blank')
	// #endif
	// #ifndef H5
	uni.setClipboardData({ data: url })
	uni.showToast({ title: 'Link copied', icon: 'none' })
	// #endif
}

function shareOrCopy(title, link) {
	const payload = { title, summary: link, href: link }
	try {
		if (typeof uni.share === 'function') {
			uni.share({
				provider: 'system',
				type: 0,
				title,
				summary: link,
				href: link,
				success: () => {},
				fail: () => {
					uni.setClipboardData({ data: link })
					uni.showToast({ title: 'Link copied', icon: 'none' })
				},
			})
			return
		}
	} catch (e) {}
	uni.setClipboardData({ data: link })
	uni.showToast({ title: 'Link copied', icon: 'none' })
}

function shareProfile() {
	const link = inviteLink()
	const title = `${user.value.nickname || 'Me'} on SPARK`
	shareOrCopy(title, link)
	apiInviteTrack({ invite_code: user.value.invite_code || '', action: 'share_profile' }).catch(() => {})
}

function inviteFriends() {
	const code = user.value.invite_code || ''
	const link = inviteLink()
	const text = code
		? `Join me on SPARK! Use my invite code ${code}: ${link}`
		: `Join me on SPARK: ${link}`
	shareOrCopy('Invite friends', text)
	apiInviteTrack({ invite_code: code, action: 'invite_friends' }).catch(() => {})
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
async function openBoostReport() {
	try {
		const res = await apiBoostReport()
		const s = (res.results && res.results.session) || {}
		uni.showModal({
			title: 'Boost report',
			content: `Impressions ${s.impressions || 0} · Likes ${s.likes || 0} · Matches ${s.matches || 0}`,
			showCancel: false,
		})
	} catch (e) {
		uni.showToast({ title: 'No report yet', icon: 'none' })
	}
}
function goPreview() {
	trackClick('open_preview')
	uni.navigateTo({ url: '/pagesA/me/preview' })
}
function goSettings() {
	trackClick('open_settings')
	uni.navigateTo({ url: '/pagesA/me/settings' })
}
async function logout() {
	try { await apiLogout() } catch (e) {}
	uni.removeStorageSync('token')
	uni.removeStorageSync('userInfo')
	uni.reLaunch({ url: '/pages/auth/welcome' })
}

onShow(refresh)
</script>

<style scoped>
.page { min-height:100vh; background: var(--bg, #FFFFFF); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 180rpx; color: var(--text, #111); }
.sec { display:block; color:var(--muted,#666); font-size:22rpx; letter-spacing:1rpx; text-transform:uppercase; margin: 24rpx 8rpx 12rpx; }
.header { align-items:center; display:flex; flex-direction:column; margin-bottom:28rpx; }
.avatar { width:160rpx; height:160rpx; border-radius:50%; margin-bottom:16rpx; border: 4rpx solid #FF4458; }
.name { color: var(--text, #111); font-size:44rpx; font-weight:700; }
.spark-serif { font-family: inherit; }
.tier { color:#FF4458; margin-top:8rpx; font-size:24rpx; text-transform: capitalize; }
.progress-wrap { width: 70%; margin-top: 20rpx; }
.progress-bar { height: 12rpx; background: #E8E8E8; border-radius: 999rpx; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #FD267A, #FF6036); }
.progress-text { display:block; text-align:center; color:#666; font-size:22rpx; margin-top:8rpx; }
.vip-card {
	display:flex; flex-direction:row; align-items:center; justify-content:space-between;
	background: linear-gradient(135deg, #FFF6D6 0%, #FFE08A 50%, #F5D76E 100%);
	border: 1px solid rgba(201,162,39,0.5);
	border-radius: 28rpx; padding: 32rpx 28rpx; margin-bottom: 20rpx;
	box-shadow: 0 8rpx 24rpx rgba(201,162,39,0.18);
}
.vip-title { display:block; color:#1A1A1A; font-size:32rpx; font-weight:800; margin-bottom:8rpx; }
.vip-sub { display:block; color:#6B5400; font-size:22rpx; }
.vip-cta {
	color:#F5D76E; font-size:24rpx; font-weight:700;
	background: #1A1A1A; border-radius:999rpx; padding:14rpx 22rpx;
}
.inventory {
	display:flex; flex-direction:row; margin-bottom: 20rpx;
}
.inv-item {
	flex:1; background:#FFFFFF; border-radius:20rpx; padding:20rpx 12rpx; margin-right:12rpx; text-align:center;
	border: 1px solid rgba(0,0,0,0.06);
}
.inv-item:last-child { margin-right: 0; }
.inv-label { display:block; color:#666; font-size:20rpx; margin-bottom:8rpx; }
.inv-val { display:block; color:#111; font-size:30rpx; font-weight:700; }
.card {
	background:#FFFFFF; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	border: 1px solid rgba(0,0,0,0.06);
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
}
.card text { color:#111; font-size:28rpx; }
.val { color:#999; }
.danger text { color:#FF4458; }
</style>
