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
					<view class="pill lavender" v-if="profile.height_cm"><text>{{ profile.height_cm }} cm</text></view>
					<view class="pill lavender" v-if="profile.school"><text>{{ profile.school }}</text></view>
					<view class="pill lavender" v-if="profile.is_traveling"><text>✈ 旅行中</text></view>
				</view>

				<view class="section">
					<text class="section-title display-font">关于我</text>
					<text class="section-body">{{ profile.bio || defaultBio }}</text>
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
					<text class="section-title display-font">想找什么样的人</text>
					<text class="section-body">{{ profile.looking_for }}</text>
				</view>

				<view class="section prompt-card" v-for="(pr, i) in promptEntries" :key="'p'+i">
					<text class="prompt-q">{{ pr.q }}</text>
					<text class="prompt-a">{{ pr.a }}</text>
				</view>

				<view class="section" v-if="lifestyleEntries.length">
					<text class="section-title display-font">生活方式</text>
					<view class="pill-row">
						<view class="pill lavender" v-for="(t, i) in lifestyleEntries" :key="i"><text>{{ t }}</text></view>
					</view>
				</view>

				<view class="section" v-if="(profile.interests || []).length">
					<text class="section-title display-font">兴趣</text>
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
					<text class="section-title display-font">社交</text>
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
				<view class="act super" @click="act('super_like')"><text>★</text></view>
				<view class="act like" @click="act('like')"><text>♥</text></view>
			</view>
		</view>
		<VipSheet v-model:show="showVip" :reason="vipReason" />
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiProfileDetail, apiBlock, apiReport } from '@/api/profile.js'
import { apiSwipe } from '@/api/recommend.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'

const REPORT_REASONS = [
	{ key: 'spam', label: '垃圾信息' },
	{ key: 'harassment', label: '骚扰' },
	{ key: 'inappropriate', label: '不当内容' },
	{ key: 'fake', label: '虚假资料' },
	{ key: 'underage', label: '未成年' },
	{ key: 'other', label: '其他' },
]

const profile = ref({})
const photoIndex = ref(0)
const userId = ref(null)
const showVip = ref(false)
const vipReason = ref('need_vip')
const defaultBio = '真诚优先，喜欢博物馆和脱口秀。想认识真诚、温柔、略内向、有共情力的人。'

const photos = computed(() => {
	const list = profile.value.photos || []
	if (list.length) return list
	if (profile.value.avatar_url) return [{ url: profile.value.avatar_url }]
	return []
})

const commonSet = computed(() => {
	const list = profile.value.common_interests || []
	return new Set(list.map((x) => String(x).toLowerCase()))
})

function isCommonInterest(t) {
	return commonSet.value.has(String(t).toLowerCase())
}

const socialEntries = computed(() => {
	const links = profile.value.social_links || {}
	return Object.keys(links).map((k) => `${k}: ${links[k]}`)
})

const lifestyleEntries = computed(() => {
	const life = profile.value.lifestyle || {}
	return Object.keys(life)
		.filter((k) => k !== 'prompt' && k !== 'prompts' && k !== 'audience_strict' && typeof life[k] !== 'object')
		.map((k) => `${k}: ${life[k]}`)
})

const promptEntries = computed(() => {
	const life = profile.value.lifestyle || {}
	const list = Array.isArray(life.prompts) ? life.prompts : []
	if (list.length) return list.filter((p) => p && p.q && p.a)
	if (life.prompt && life.prompt.q && life.prompt.a) return [life.prompt]
	return []
})

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
		uni.showToast({ title: '资料加载失败', icon: 'none' })
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
		uni.showToast({ title: '暂不可用', icon: 'none' })
		return
	}
	uni.showActionSheet({
		itemList: ['拉黑', '举报'],
		success: async (r) => {
			try {
				if (r.tapIndex === 0) {
					uni.showModal({
						title: '拉黑',
						content: '双方将从推荐和聊天中消失。',
						success: async (m) => {
							if (!m.confirm) return
							await apiBlock(uid)
							uni.showToast({ title: '已拉黑', icon: 'none' })
							setTimeout(() => uni.navigateBack(), 400)
						}
					})
					return
				}
				if (r.tapIndex === 1) {
					uni.showActionSheet({
						itemList: REPORT_REASONS.map((x) => x.label),
						success: async (rr) => {
							const reason = REPORT_REASONS[rr.tapIndex] || REPORT_REASONS[REPORT_REASONS.length - 1]
							try {
								await apiReport({ user_id: uid, reason: reason.key })
								uni.showToast({ title: '已提交', icon: 'none' })
							} catch (e) {
								uni.showToast({ title: (e && e.message) || '举报失败', icon: 'none' })
							}
						},
					})
				}
			} catch (e) {
				uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
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
		uni.showToast({ title: msg || '操作失败', icon: 'none' })
	}
}
</script>

<style scoped>
.detail-page {
	min-height: 100vh;
	background: #FFF7FA;
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
	font-family: 'Playfair Display', 'Times New Roman', serif;
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
.lavender { background: #F3F0F7; }
.lavender text { color: #333; }
.pill.common { background: rgba(255,107,154,0.18); border: 1px solid #FF6B9A; }
.pill.common text { color: #FF6B9A; font-weight: 700; }
.pink { background: #FFF0F3; }
.pink text { color: #FF5A60; }
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
	background: #FFF5F8;
	border-radius: 24rpx;
	padding: 28rpx;
	border: 1px solid rgba(255,107,154,0.22);
}
.prompt-q {
	display: block;
	color: #FF6B9A;
	font-size: 24rpx;
	font-weight: 700;
	margin-bottom: 12rpx;
}
.prompt-a {
	display: block;
	color: #222;
	font-size: 30rpx;
	line-height: 1.45;
	font-family: 'PingFang SC', 'Hiragino Sans GB', sans-serif;
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
.super { background: #FF8FB3; width: 88rpx; height: 88rpx; }
.super text { color: #fff; font-size: 40rpx; }
.like { background: #FF6B9A; width: 112rpx; height: 112rpx; }
.like text { color: #fff; }
.bottom-space { height: 40rpx; }
</style>
