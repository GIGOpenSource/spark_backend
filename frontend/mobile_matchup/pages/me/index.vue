<template>
	<view class="page">
		<view class="header">
			<image :src="user.avatar_url || placeholder" class="avatar" mode="aspectFill" />
			<text class="name display-font">{{ user.nickname || '我' }}</text>
			<text class="tier">{{ tierLabel }}</text>
			<view class="progress-wrap">
				<view class="progress-bar"><view class="progress-fill" :style="{ width: completeness + '%' }" /></view>
				<text class="progress-text">资料完整度 {{ completeness }}%</text>
			</view>
		</view>

		<view class="vip-card">
			<view class="vip-left" @click="openShop('need_vip')">
				<text class="vip-title">{{ isVip ? '会员中心' : '开通会员' }}</text>
				<text class="vip-sub">{{ isVip ? ('当前：' + tierLabel) : '查看喜欢你的人 · 反悔 · 曝光' }}</text>
			</view>
			<view class="vip-actions">
				<text class="vip-cta" @click.stop="manageSubscription">{{ isVip ? '管理订阅' : '升级' }}</text>
				<text v-if="isVip" class="vip-cta ghost" @click.stop="openShop('need_vip')">加购</text>
			</view>
		</view>

		<view class="inventory">
			<view class="inv-item" @click="openShop('need_super_like')">
				<text class="inv-label">{{ slLabel }}</text>
				<text class="inv-val">{{ balances.super_like }}</text>
			</view>
			<view class="inv-item" @click="openShop('need_boost')">
				<text class="inv-label">{{ blLabel }}</text>
				<text class="inv-val">{{ balances.boost }}</text>
			</view>
			<view class="inv-item" @click="openShop('need_rewind')">
				<text class="inv-label">反悔</text>
				<text class="inv-val">{{ balances.rewind }}</text>
			</view>
			<view class="inv-item" @click="doBoost">
				<text class="inv-label">开启{{ blLabel }}</text>
				<text class="inv-val">⚡</text>
			</view>
		</view>

		<view class="card" @click="goEdit"><text>{{ $t('me.edit') }}</text></view>
		<view class="card" @click="go('/pagesA/features/swipe-night')"><text>Swipe Night</text></view>
		<view class="card" @click="go('/pagesA/features/matchmaker')"><text>Matchmaker</text></view>
		<view class="card" @click="go('/pagesA/features/campus')"><text>Campus</text></view>
		<view class="card" @click="go('/pagesA/features/select')"><text>Select</text></view>
		<view class="card" @click="go('/pagesA/features/face-to-face')"><text>Face to Face</text></view>
		<view class="card" @click="go('/pagesA/me/safety')"><text>Safety</text></view>
		<view class="card" @click="shareProfile"><text>{{ $t('me.share') }}</text></view>
		<view class="card" @click="inviteFriends"><text>{{ $t('me.invite') }}</text></view>
		<view class="card" @click="goSettings"><text>{{ $t('me.settings') }}</text></view>
		<view class="card" @click="openPolicy('tos')"><text>{{ $t('common.userAgreement') }}</text></view>
		<view class="card" @click="openPolicy('privacy')"><text>{{ $t('common.privacyPolicy') }}</text></view>
		<view class="card danger" @click="logout"><text>{{ $t('common.logout') }}</text></view>
		<VipSheet v-model:show="showVip" :reason="vipReason" @purchased="refresh" />
		<SparkTabBar :current="3" />
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
import { tierDisplayName, superLikeLabel, boostLabel } from '@/utils/productProfile.js'
import { openManageSubscriptions } from '@/utils/capabilities.js'
import { SITE_DOMAIN } from '@/config/config.js'
import { trackClick } from '@/utils/analytics.js'

const user = ref(uni.getStorageSync('userInfo') || {})
const showVip = ref(false)
const vipReason = ref('need_vip')
const balances = ref({ super_like: 0, boost: 0, rewind: 0 })
const displayTier = ref('')
const placeholder = 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400'

const tierLabel = computed(() => {
	if (displayTier.value) return displayTier.value
	const t = user.value && user.value.vip_tier
	return !t || t === 'none' ? '免费' : tierDisplayName(t)
})
const isVip = computed(() => tierLabel.value !== '免费' && tierLabel.value !== 'Free')
const slLabel = computed(() => superLikeLabel())
const blLabel = computed(() => boostLabel())

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
				rewind: spend.rewind || 0
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
		uni.showToast({ title: '刷新失败', icon: 'none' })
	}
}

function openShop(reason) {
	trackClick('open_vip')
	vipReason.value = reason
	showVip.value = true
}

function manageSubscription() {
	if (!isVip.value) {
		openShop('need_vip')
		return
	}
	openManageSubscriptions()
}

function inviteLink() {
	const u = user.value || {}
	const code = u.invite_code || u.id || ''
	return `https://${SITE_DOMAIN}/invite?code=${encodeURIComponent(code)}`
}

function shareProfile() {
	const u = user.value || {}
	const link = inviteLink()
	const text = `${u.nickname || '她说'} 的资料：${link}`
	apiInviteTrack({ invite_code: u.invite_code || '', action: 'share_profile' }).catch(() => {})
	// #ifdef APP-PLUS
	try {
		uni.share({
			provider: 'weixin',
			type: 0,
			title: '来「她说」看看我',
			summary: text,
			href: link,
			fail: () => {
				uni.setClipboardData({ data: text })
				uni.showToast({ title: '链接已复制', icon: 'none' })
			},
		})
		return
	} catch (e) {}
	// #endif
	uni.setClipboardData({ data: text })
	uni.showToast({ title: '资料链接已复制', icon: 'none' })
}

function inviteFriends() {
	const u = user.value || {}
	const code = u.invite_code || String(u.id || '')
	const link = inviteLink()
	const text = `邀请你来「她说」：${link}`
	apiInviteTrack({ invite_code: code, action: 'invite' }).catch(() => {})
	uni.setClipboardData({ data: text })
	uni.showToast({ title: code ? `邀请码 ${code} 已复制` : '邀请链接已复制', icon: 'none' })
}

async function doBoost() {
	try {
		await apiBoost()
		uni.showToast({ title: blLabel.value + '已开启', icon: 'none' })
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
	uni.showToast({ title: '链接已复制', icon: 'none' })
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
		'/pagesA/me/safety': 'open_safety',
		'/pagesA/me/preview': 'open_preview',
	}
	if (featureMap[url]) trackClick(featureMap[url])
	uni.navigateTo({ url })
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
.page { min-height:100vh; background: var(--bg, #FFF7FA); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 160rpx; }
.header { align-items:center; display:flex; flex-direction:column; margin-bottom:28rpx; }
.avatar { width:160rpx; height:160rpx; border-radius:50%; margin-bottom:16rpx; border: 4rpx solid #FF6B9A; }
.name { color: var(--text, #222); font-size:44rpx; font-weight:700; }
.display-font { font-family: inherit; }
.tier { color:#FF6B9A; margin-top:8rpx; font-size:24rpx; text-transform: capitalize; }
.progress-wrap { width: 70%; margin-top: 20rpx; }
.progress-bar { height: 12rpx; background: #FFE4EE; border-radius: 999rpx; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #FF6B9A, #FF8FB3); }
.progress-text { display:block; text-align:center; color:#999; font-size:22rpx; margin-top:8rpx; }
.vip-card {
	display:flex; flex-direction:row; align-items:center; justify-content:space-between;
	background: linear-gradient(135deg, #FFE0EA 0%, #FFFFFF 55%, #FFF0F5 100%);
	border: 1px solid rgba(255,107,154,0.35);
	border-radius: 28rpx; padding: 32rpx 28rpx; margin-bottom: 20rpx;
}
.vip-title { display:block; color:#222; font-size:32rpx; font-weight:800; margin-bottom:8rpx; }
.vip-sub { display:block; color:#888; font-size:22rpx; }
.vip-actions { display:flex; flex-direction:column; align-items:flex-end; }
.vip-cta {
	color:#fff; font-size:24rpx; font-weight:700;
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3); border-radius:999rpx; padding:14rpx 22rpx;
	margin-bottom: 8rpx;
}
.vip-cta.ghost {
	background: transparent; color:#FF6B9A; border: 1px solid rgba(255,107,154,0.45);
	margin-bottom: 0;
}
.inventory {
	display:flex; flex-direction:row; margin-bottom: 20rpx;
}
.inv-item {
	flex:1; background:#FFFFFF; border-radius:20rpx; padding:20rpx 12rpx; margin-right:12rpx; text-align:center;
}
.inv-item:last-child { margin-right: 0; }
.inv-label { display:block; color:#999; font-size:20rpx; margin-bottom:8rpx; }
.inv-val { display:block; color:#FF6B9A; font-size:30rpx; font-weight:700; }
.card {
	background:#FFFFFF; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
}
.card text { color:#222; font-size:28rpx; }
.danger text { color:#FF6B9A; }
</style>
