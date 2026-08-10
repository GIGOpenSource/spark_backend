<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Preview</text>
			<text class="edit" @click="goEdit">Edit</text>
		</view>

		<scroll-view scroll-y class="scroller" v-if="profile.id || profile.nickname">
			<view class="hero">
				<swiper class="hero-swiper" :current="photoIndex" @change="onSwiper">
					<swiper-item v-for="(p, i) in photos" :key="i">
						<image class="hero-img" :src="p.url" mode="aspectFill" />
					</swiper-item>
				</swiper>
				<view class="dots" v-if="photos.length > 1">
					<view v-for="(p, i) in photos" :key="i" class="dot" :class="{ on: i === photoIndex }" />
				</view>
			</view>

			<view class="sheet">
				<view class="name-row">
					<text class="name spark-serif">{{ profile.nickname || 'You' }}</text>
					<text class="age" v-if="profile.age">{{ profile.age }}</text>
					<view v-if="profile.is_verified" class="verified"><text>★</text></view>
				</view>
				<view class="pill-row">
					<view class="pill" v-if="profile.job"><text>{{ profile.job }}</text></view>
					<view class="pill" v-if="profile.city"><text>📍 {{ profile.city }}</text></view>
					<view class="pill" v-if="profile.height_cm"><text>{{ profile.height_cm }} cm</text></view>
					<view class="pill" v-if="profile.school"><text>{{ profile.school }}</text></view>
				</view>

				<view class="section" v-if="profile.bio">
					<text class="section-title">About</text>
					<text class="section-body">{{ profile.bio }}</text>
				</view>

				<view class="section" v-if="(profile.interests || []).length">
					<text class="section-title">Interests</text>
					<view class="pill-row">
						<view class="pill" v-for="(t, i) in profile.interests" :key="i"><text>{{ t }}</text></view>
					</view>
				</view>

				<view class="section" v-if="(profile.languages || []).length">
					<text class="section-title">Languages</text>
					<view class="pill-row">
						<view class="pill" v-for="(t, i) in profile.languages" :key="i"><text>{{ t }}</text></view>
					</view>
				</view>

				<view class="hint"><text>This is how others see your profile</text></view>
			</view>
		</scroll-view>
		<view v-else class="empty"><text>Loading…</text></view>
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiProfilePreview } from '@/api/profile.js'

const profile = ref({})
const photoIndex = ref(0)

const photos = computed(() => {
	const list = profile.value.photos || []
	if (list.length) return list
	if (profile.value.avatar_url) return [{ url: profile.value.avatar_url }]
	return [{ url: 'https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800' }]
})

onMounted(async () => {
	try {
		const res = await apiProfilePreview()
		profile.value = res.results || {}
	} catch (e) {
		uni.showToast({ title: 'Failed to load preview', icon: 'none' })
	}
})

function onSwiper(e) {
	photoIndex.value = e.detail.current
}
function goEdit() {
	uni.navigateTo({ url: '/pagesA/me/edit' })
}
function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height: 100vh; background: #F8F8F8; }
.header {
	position: fixed; left: 0; right: 0; z-index: 10;
	padding: calc(env(safe-area-inset-top) + 12rpx) 24rpx 12rpx;
	display: flex; flex-direction: row; align-items: center;
	background: linear-gradient(180deg, rgba(0,0,0,0.35), transparent);
}
.back { color: #fff; font-size: 48rpx; width: 60rpx; }
.title { flex: 1; color: #fff; font-size: 32rpx; font-weight: 700; }
.edit { color: #fff; font-size: 26rpx; }
.scroller { height: 100vh; }
.hero { position: relative; height: 780rpx; }
.hero-swiper, .hero-img { width: 100%; height: 780rpx; }
.dots {
	position: absolute; left: 0; right: 0; bottom: 72rpx;
	display: flex; flex-direction: row; justify-content: center;
}
.dot {
	width: 12rpx; height: 12rpx; border-radius: 50%;
	background: rgba(255,255,255,0.4); margin: 0 6rpx;
}
.dot.on { background: #fff; }
.sheet {
	margin-top: -56rpx; background: #fff; border-radius: 48rpx 48rpx 0 0;
	padding: 40rpx 32rpx 120rpx; position: relative; z-index: 1;
}
.name-row { display: flex; flex-direction: row; align-items: center; margin-bottom: 20rpx; }
.name { font-size: 52rpx; color: #111; font-weight: 700; margin-right: 12rpx; }
.spark-serif { font-family: 'Playfair Display', 'Times New Roman', serif; }
.age { font-size: 40rpx; color: #222; margin-right: 12rpx; }
.verified {
	width: 36rpx; height: 36rpx; background: #3B82F6; border-radius: 8rpx;
	display: flex; align-items: center; justify-content: center;
}
.verified text { color: #fff; font-size: 20rpx; }
.pill-row { display: flex; flex-direction: row; flex-wrap: wrap; margin-bottom: 24rpx; }
.pill {
	border-radius: 999rpx; padding: 12rpx 22rpx; margin-right: 12rpx; margin-bottom: 12rpx;
	background: #F3F0F7;
}
.pill text { font-size: 24rpx; color: #222; }
.section { margin-bottom: 28rpx; }
.section-title { display: block; font-size: 32rpx; font-weight: 700; color: #111; margin-bottom: 12rpx; }
.section-body { display: block; font-size: 28rpx; color: #222; line-height: 1.55; }
.hint { text-align: center; margin-top: 12rpx; }
.hint text { color: #999; font-size: 22rpx; }
.empty { padding-top: 40vh; text-align: center; color: #666; }
</style>
