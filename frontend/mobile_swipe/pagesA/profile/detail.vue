<template>
	<view class="detail-page">
		<scroll-view scroll-y class="scroller">
			<view class="hero">
				<swiper class="hero-swiper" :current="photoIndex" @change="onSwiper">
					<swiper-item v-for="(p, i) in photos" :key="i">
						<image class="hero-img" :src="p.url" mode="aspectFill" />
					</swiper-item>
				</swiper>
				<view class="close-btn" @click="goBack"><text>×</text></view>
				<view class="more-btn" @click="more"><text>⋯</text></view>
				<view class="dots" v-if="photos.length">
					<view v-for="(p, i) in photos" :key="i" class="dot" :class="{ on: i === photoIndex }" />
				</view>
			</view>

			<view class="sheet">
				<view class="name-row">
					<text class="name display-font">{{ profile.nickname }}</text>
					<text class="age">{{ profile.age }}</text>
					<view v-if="profile.is_verified" class="verified"><text>★</text></view>
					<view v-if="profile.is_online" class="online-dot" />
				</view>
				<view class="pill-row">
					<view class="pill lavender" v-if="profile.job"><text>{{ profile.job }}</text></view>
					<view class="pill lavender" v-if="profile.city"><text>📍 {{ profile.city }}</text></view>
					<view class="pill lavender" v-if="profile.is_traveling"><text>✈ Traveling</text></view>
				</view>

				<view class="section">
					<text class="section-title display-font">Description</text>
					<text class="section-body" @click="openComplimentKind('bio')">{{ profile.bio || defaultBio }}</text>
					<text class="compl-link" v-if="profile.bio" @click="openComplimentKind('bio')">Compliment bio ›</text>
				</view>

				<view class="pill-row">
					<view class="pill pink" v-if="profile.mbti"><text>{{ profile.mbti }}</text></view>
					<view class="pill pink" v-if="profile.zodiac"><text>{{ profile.zodiac }}</text></view>
					<view class="pill pink" v-if="profile.relationship"><text>{{ profile.relationship }}</text></view>
				</view>

				<view class="inline-photo" v-if="photos[1]">
					<image :src="photos[1].url" mode="aspectFill" class="inline-img" />
					<view class="loc-chip" v-if="profile.city"><text>📍 {{ profile.city }}</text></view>
				</view>

				<view class="section" v-if="profile.looking_for">
					<text class="section-title display-font">Looking for</text>
					<text class="section-body">{{ profile.looking_for }}</text>
				</view>

				<view class="section prompt-card" v-for="(pr, i) in promptEntries" :key="'p'+i" @click="openComplimentKind('prompt', i)">
					<text class="prompt-q">{{ pr.q }}</text>
					<text class="prompt-a">{{ pr.a }}</text>
					<text class="compl-link">Compliment ›</text>
				</view>

				<view class="section" v-if="openingMoves.length">
					<text class="section-title display-font">Opening Moves</text>
					<view class="om" v-for="(m, i) in openingMoves" :key="'om'+i">
						<text>{{ m }}</text>
					</view>
				</view>

				<view class="section media-prompt" v-if="voicePrompt.url">
					<text class="section-title display-font">Voice prompt</text>
					<text class="prompt-q">{{ voicePrompt.q }}</text>
					<Waveform :seed="voicePrompt.url" label="Play" @toggle="playPrompt(voicePrompt.url)" />
					<text class="compl-link" @click="openComplimentKind('voice')">Compliment voice ›</text>
				</view>
				<view class="section media-prompt" v-if="videoPrompt.url">
					<text class="section-title display-font">Video prompt</text>
					<text class="prompt-q">{{ videoPrompt.q }}</text>
					<video class="prompt-video" :src="videoPrompt.url" controls />
					<text class="compl-link" @click="openComplimentKind('video')">Compliment video ›</text>
				</view>

				<view class="section" v-if="lifestyleEntries.length">
					<text class="section-title display-font">Lifestyle</text>
					<view class="pill-row">
						<view class="pill lavender" v-for="(t, i) in lifestyleEntries" :key="i"><text>{{ t }}</text></view>
					</view>
				</view>

				<view class="section" v-if="badgeList.length">
					<text class="section-title display-font">Badges</text>
					<view class="pill-row">
						<view class="pill lavender" v-for="b in badgeList" :key="b.id"><text>{{ b.label }}</text></view>
					</view>
				</view>

				<view class="section" v-if="(profile.interests || []).length">
					<text class="section-title display-font">Interests</text>
					<view class="pill-row">
						<view
							class="pill lavender"
							:class="{ common: isCommonInterest(t) }"
							v-for="(t, i) in profile.interests"
							:key="i"
						><text>{{ t }}</text></view>
					</view>
				</view>

				<view class="inline-photo" v-if="photos[2]">
					<image :src="photos[2].url" mode="aspectFill" class="inline-img" />
				</view>

				<view class="section" v-if="socialEntries.length">
					<text class="section-title display-font">Social</text>
					<view class="pill-row">
						<view class="pill lavender" v-for="(s, i) in socialEntries" :key="i"><text>{{ s }}</text></view>
					</view>
				</view>

				<view class="bottom-space" />
			</view>
		</scroll-view>

		<view class="action-bar">
			<view class="bar-inner">
				<view class="act pass" @click="act('pass')"><text>×</text></view>
				<view class="act super" @click="openCompliment"><text>★</text></view>
				<view class="act like" @click="act('like')"><text>♥</text></view>
			</view>
		</view>
		<ComplimentSheet
			v-model:show="showCompliment"
			:user="profile"
			:photo-url="currentPhoto"
			:initial-kind="complimentKind"
			:initial-prompt-index="complimentPromptIndex"
			@sent="onComplimentSent"
			@need-shop="onComplimentNeedShop"
		/>
		<VipSheet v-model:show="showVip" :reason="vipReason" />
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiProfileDetail, apiBlock, apiReport } from '@/api/profile.js'
import { apiSwipe } from '@/api/recommend.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import ComplimentSheet from '@/components/ComplimentSheet/ComplimentSheet.vue'
import Waveform from '@/components/Waveform/Waveform.vue'
import { isComplimentEnabled, resolveBadges } from '@/utils/productProfile.js'

const profile = ref({})
const photoIndex = ref(0)
const userId = ref(null)
const showVip = ref(false)
const showCompliment = ref(false)
const vipReason = ref('need_vip')
const complimentKind = ref('photo')
const complimentPromptIndex = ref(0)
const defaultBio = 'I love museum stand-up comedy; sincerity comes first. Looking for someone who is sincere, gentle, somewhat introverted, and empathetic.'

const photos = computed(() => {
	const list = profile.value.photos || []
	if (list.length) return list
	if (profile.value.avatar_url) return [{ url: profile.value.avatar_url }]
	return []
})

const currentPhoto = computed(() => {
	if (!photos.value.length) return profile.value.avatar_url || ''
	return photos.value[Math.min(photoIndex.value, photos.value.length - 1)].url
})

const socialEntries = computed(() => {
	const links = profile.value.social_links || {}
	return Object.keys(links).map((k) => `${k}: ${links[k]}`)
})

const lifestyleEntries = computed(() => {
	const life = profile.value.lifestyle || {}
	return Object.keys(life)
		.filter((k) => !['prompt', 'prompts', 'opening_moves', 'voice_prompt', 'video_prompt', 'audience_strict', 'badges', 'dating_mode', 'women_first_role', 'opener_role'].includes(k) && typeof life[k] !== 'object')
		.map((k) => `${k}: ${life[k]}`)
})

const promptEntries = computed(() => {
	const life = profile.value.lifestyle || {}
	const list = Array.isArray(life.prompts) ? life.prompts : []
	if (list.length) return list.filter((p) => p && p.q && p.a)
	if (life.prompt && life.prompt.q && life.prompt.a) return [life.prompt]
	return []
})

const openingMoves = computed(() => {
	const list = (profile.value.lifestyle && profile.value.lifestyle.opening_moves) || []
	return Array.isArray(list) ? list.filter(Boolean) : []
})

const voicePrompt = computed(() => (profile.value.lifestyle && profile.value.lifestyle.voice_prompt) || {})
const videoPrompt = computed(() => (profile.value.lifestyle && profile.value.lifestyle.video_prompt) || {})
const badgeList = computed(() => resolveBadges(profile.value))

const commonInterestSet = computed(() => {
	const list = profile.value.common_interests || []
	return new Set((list || []).map((x) => String(x).toLowerCase()))
})

function isCommonInterest(t) {
	return commonInterestSet.value.has(String(t || '').toLowerCase())
}

const REPORT_REASONS = [
	{ key: 'spam', label: 'Spam' },
	{ key: 'harassment', label: 'Harassment' },
	{ key: 'inappropriate', label: 'Inappropriate' },
	{ key: 'fake', label: 'Fake profile' },
	{ key: 'underage', label: 'Underage' },
	{ key: 'other', label: 'Other' },
]

function playPrompt(url) {
	if (!url) return
	const ctx = uni.createInnerAudioContext()
	ctx.src = url
	ctx.play()
}

onLoad((q) => {
	userId.value = q.user_id
	if (q.photo) photoIndex.value = Number(q.photo) || 0
	if (q.funnel) {
		try {
			profile.value = JSON.parse(decodeURIComponent(q.funnel))
		} catch (e) {}
	}
})

onMounted(async () => {
	if (!userId.value || String(userId.value).startsWith('funnel')) return
	try {
		const res = await apiProfileDetail(userId.value)
		profile.value = { ...profile.value, ...(res.results || {}) }
	} catch (e) {
		uni.showToast({ title: 'Failed to load profile', icon: 'none' })
	}
})

function onSwiper(e) {
	photoIndex.value = e.detail.current
}

function goBack() {
	uni.navigateBack()
}

function more() {
	const uid = userId.value || profile.value.id
	if (!uid || String(uid).startsWith('funnel')) {
		uni.showToast({ title: 'Unavailable', icon: 'none' })
		return
	}
	uni.showActionSheet({
		itemList: ['Block', 'Report'],
		success: async (r) => {
			try {
				if (r.tapIndex === 0) {
					uni.showModal({
						title: 'Block',
						content: 'You both will disappear from recommendations and chats.',
						success: async (m) => {
							if (!m.confirm) return
							await apiBlock(uid)
							uni.showToast({ title: 'Blocked', icon: 'none' })
							setTimeout(() => uni.navigateBack(), 400)
						}
					})
				} else {
					uni.showActionSheet({
						itemList: REPORT_REASONS.map((x) => x.label),
						success: async (rr) => {
							const reason = REPORT_REASONS[rr.tapIndex]
							if (!reason) return
							try {
								await apiReport({ user_id: uid, reason: reason.key })
								uni.showToast({ title: 'Reported', icon: 'none' })
							} catch (e) {
								uni.showToast({ title: (e && e.message) || 'Report failed', icon: 'none' })
							}
						},
					})
				}
			} catch (e) {
				uni.showToast({ title: (e && e.message) || 'Action failed', icon: 'none' })
			}
		}
	})
}

async function act(action) {
	try {
		await apiSwipe({ target_id: userId.value || profile.value.id, action })
		uni.navigateBack()
	} catch (e) {
		const msg = (e && e.message) || ''
		if (/need_|daily_like|limit/.test(msg) || (e && e.results && e.results.need_vip)) {
			vipReason.value = msg || 'need_vip'
			showVip.value = true
			return
		}
		uni.showToast({ title: msg || 'failed', icon: 'none' })
	}
}

function openCompliment() {
	openComplimentKind('photo')
}

function openComplimentKind(kind = 'photo', promptIdx = 0) {
	if (!isComplimentEnabled()) {
		act('super_like')
		return
	}
	complimentKind.value = kind
	complimentPromptIndex.value = promptIdx
	showCompliment.value = true
}

function onComplimentNeedShop() {
	vipReason.value = 'need_super_like'
	showVip.value = true
}

function onComplimentSent(data) {
	if (data && data.matched) {
		uni.showToast({ title: "It's a Match!", icon: 'none' })
	} else {
		uni.showToast({ title: 'Compliment sent', icon: 'none' })
	}
	setTimeout(() => uni.navigateBack(), 400)
}
</script>

<style scoped>
.detail-page {
	min-height: 100vh;
	background: #FFFDF6;
}
.scroller { height: 100vh; }
.hero {
	position: relative;
	height: 780rpx;
}
.hero-swiper, .hero-img {
	width: 100%;
	height: 780rpx;
}
.close-btn {
	position: absolute;
	right: 28rpx;
	top: calc(env(safe-area-inset-top) + 20rpx);
	width: 64rpx;
	height: 64rpx;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 2;
}
.close-btn text { color: #111; font-size: 40rpx; }
.more-btn {
	position: absolute;
	left: 28rpx;
	top: calc(env(safe-area-inset-top) + 20rpx);
	width: 64rpx;
	height: 64rpx;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 2;
}
.more-btn text { color: #111; font-size: 36rpx; }
.dots {
	position: absolute;
	left: 0;
	right: 0;
	bottom: 72rpx;
	display: flex;
	flex-direction: row;
	justify-content: center;
	z-index: 2;
}
.dot {
	width: 12rpx;
	height: 12rpx;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.4);
	margin: 0 6rpx;
}
.dot.on { background: #fff; }
.sheet {
	margin-top: -56rpx;
	background: #fff;
	border-radius: 48rpx 48rpx 0 0;
	padding: 40rpx 32rpx 220rpx;
	min-height: 60vh;
	position: relative;
	z-index: 1;
	box-shadow: 0 -12rpx 40rpx rgba(0,0,0,0.12);
}
.name-row {
	display: flex;
	flex-direction: row;
	align-items: center;
	margin-bottom: 20rpx;
}
.name {
	font-size: 56rpx;
	color: #111;
	font-weight: 700;
	margin-right: 12rpx;
}
.display-font {
	font-family: 'Montserrat', 'Helvetica Neue', sans-serif;
}
.age {
	font-size: 44rpx;
	color: #333;
	margin-right: 12rpx;
}
.verified {
	width: 36rpx;
	height: 36rpx;
	background: #3B82F6;
	border-radius: 8rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: 10rpx;
}
.verified text { color: #fff; font-size: 20rpx; }
.online-dot {
	width: 18rpx;
	height: 18rpx;
	border-radius: 50%;
	background: #22C55E;
	border: 3rpx solid #fff;
}
.pill-row {
	display: flex;
	flex-direction: row;
	flex-wrap: wrap;
	margin-bottom: 28rpx;
}
.pill {
	border-radius: 999rpx;
	padding: 12rpx 22rpx;
	margin-right: 12rpx;
	margin-bottom: 12rpx;
}
.pill text { font-size: 24rpx; }
.lavender { background: #FFF8E1; }
.lavender text { color: #333; }
.pill.common {
	background: #FFC629;
	border: 1px solid #E6A800;
}
.pill.common text { color: #111; font-weight: 700; }
.pink { background: #FFF8E1; }
.pink text { color: #8A6D00; }
.section { margin-bottom: 28rpx; }
.section-title {
	display: block;
	font-size: 34rpx;
	font-weight: 700;
	color: #111;
	margin-bottom: 12rpx;
}
.section-body {
	display: block;
	font-size: 28rpx;
	color: #444;
	line-height: 1.55;
}
.prompt-card {
	background: #FFF9E6;
	border-radius: 24rpx;
	padding: 28rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.om {
	background: #FFF8E1; border-radius: 16rpx; padding: 18rpx 22rpx; margin-bottom: 12rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.om text { color:#111; font-size:26rpx; }
.play-btn {
	display:inline-block; background:#FFC629; border-radius:999rpx; padding:14rpx 28rpx; margin-top:12rpx;
}
.play-btn text { color:#111; font-weight:800; font-size:24rpx; }
.prompt-video { width:100%; height:360rpx; border-radius:20rpx; margin-top:12rpx; background:#111; }
.prompt-q {
	display: block;
	color: #B8860B;
	font-size: 24rpx;
	font-weight: 700;
	margin-bottom: 12rpx;
}
.prompt-a {
	display: block;
	color: #222;
	font-size: 30rpx;
	line-height: 1.45;
	font-family: 'Montserrat', 'Helvetica Neue', sans-serif;
}
.compl-link {
	display:block; color:#B8860B; font-size:22rpx; font-weight:800; margin-top:12rpx;
}
.inline-photo {
	position: relative;
	border-radius: 28rpx;
	overflow: hidden;
	height: 360rpx;
	margin-bottom: 28rpx;
}
.inline-img { width: 100%; height: 100%; }
.loc-chip {
	position: absolute;
	left: 20rpx;
	bottom: 20rpx;
	background: rgba(0, 0, 0, 0.55);
	border-radius: 999rpx;
	padding: 10rpx 18rpx;
}
.loc-chip text { color: #fff; font-size: 22rpx; }
.action-bar {
	position: fixed;
	left: 0;
	right: 0;
	bottom: calc(env(safe-area-inset-bottom) + 24rpx);
	display: flex;
	justify-content: center;
	z-index: 10;
}
.bar-inner {
	background: #222228;
	border-radius: 999rpx;
	padding: 16rpx 36rpx;
	display: flex;
	flex-direction: row;
	align-items: center;
}
.act {
	width: 96rpx;
	height: 96rpx;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	margin: 0 18rpx;
}
.act text { font-size: 48rpx; }
.pass { background: #fff; }
.pass text { color: #111; }
.super { background: #1DA1F2; width: 88rpx; height: 88rpx; }
.super text { color: #fff; font-size: 40rpx; }
.like { background: #FFC629; width: 112rpx; height: 112rpx; }
.like text { color: #111; }
.bottom-space { height: 40rpx; }
</style>
