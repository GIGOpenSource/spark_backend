<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">别人眼中的我</text>
		</view>

		<view v-if="loading" class="empty"><text>加载中…</text></view>
		<template v-else>
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
					<text class="name">{{ profile.nickname || '我' }}</text>
					<text class="age" v-if="profile.age">{{ profile.age }}</text>
					<view v-if="profile.is_verified" class="verified"><text>✓</text></view>
				</view>
				<view class="pill-row">
					<view class="pill" v-if="profile.job"><text>{{ profile.job }}</text></view>
					<view class="pill" v-if="profile.city"><text>{{ profile.city }}</text></view>
					<view class="pill" v-if="profile.height_cm"><text>{{ profile.height_cm }} cm</text></view>
					<view class="pill" v-if="profile.school"><text>{{ profile.school }}</text></view>
				</view>
				<text class="bio" v-if="profile.bio">{{ profile.bio }}</text>
				<view class="sec" v-if="(profile.languages || []).length">
					<text class="sec-t">语言</text>
					<view class="pill-row">
						<view class="pill" v-for="(l, i) in profile.languages" :key="i"><text>{{ l }}</text></view>
					</view>
				</view>
				<view class="sec" v-if="(profile.interests || []).length">
					<text class="sec-t">兴趣</text>
					<view class="pill-row">
						<view class="pill" v-for="(t, i) in profile.interests" :key="i"><text>{{ t }}</text></view>
					</view>
				</view>
			</view>
		</template>
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiProfilePreview } from '@/api/profile.js'

const profile = ref({})
const loading = ref(true)
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
		uni.showToast({ title: (e && e.message) || '预览加载失败', icon: 'none' })
	}
	loading.value = false
})

function onSwiper(e) {
	photoIndex.value = e.detail.current
}
function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height: 100vh; background: var(--bg, #FFF7FA); padding-bottom: 60rpx; }
.header {
	padding: calc(env(safe-area-inset-top) + 16rpx) 24rpx 12rpx;
	display: flex; flex-direction: row; align-items: center;
}
.back { color: #222; font-size: 48rpx; width: 60rpx; }
.title { color: #222; font-size: 36rpx; font-weight: 700; }
.empty { padding: 80rpx; text-align: center; color: #999; }
.hero { position: relative; height: 72vh; background: #FFE0EA; }
.hero-swiper, .hero-img { width: 100%; height: 72vh; }
.dots {
	position: absolute; left: 0; right: 0; bottom: 24rpx;
	display: flex; flex-direction: row; justify-content: center;
}
.dot {
	width: 12rpx; height: 12rpx; border-radius: 50%; background: rgba(255,255,255,0.45); margin: 0 6rpx;
}
.dot.on { background: #fff; }
.sheet {
	margin-top: -40rpx; background: #fff; border-radius: 32rpx 32rpx 0 0;
	padding: 36rpx 28rpx 40rpx; position: relative;
}
.name-row { display: flex; flex-direction: row; align-items: baseline; margin-bottom: 16rpx; }
.name { color: #222; font-size: 44rpx; font-weight: 800; margin-right: 12rpx; }
.age { color: #666; font-size: 36rpx; }
.verified {
	margin-left: 12rpx; width: 36rpx; height: 36rpx; border-radius: 50%;
	background: #FF6B9A; display: flex; align-items: center; justify-content: center;
}
.verified text { color: #fff; font-size: 20rpx; }
.pill-row { display: flex; flex-direction: row; flex-wrap: wrap; margin-bottom: 12rpx; }
.pill {
	background: #FFF0F5; border-radius: 999rpx; padding: 10rpx 20rpx;
	margin-right: 12rpx; margin-bottom: 12rpx;
}
.pill text { color: #FF6B9A; font-size: 24rpx; }
.bio { display: block; color: #333; font-size: 28rpx; line-height: 1.5; margin: 8rpx 0 20rpx; }
.sec { margin-top: 12rpx; }
.sec-t { display: block; color: #999; font-size: 22rpx; margin-bottom: 10rpx; }
</style>
