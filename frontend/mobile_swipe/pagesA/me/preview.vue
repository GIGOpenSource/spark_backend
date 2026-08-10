<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">{{ $t('me.previewTitle') }}</text>
		</view>
		<text class="sub">{{ $t('me.previewSub') }}</text>

		<scroll-view scroll-y class="scroller" v-if="profile.nickname || loading === false">
			<view class="hero">
				<swiper class="hero-swiper" :current="photoIndex" @change="onSwiper">
					<swiper-item v-for="(p, i) in photos" :key="i">
						<image class="hero-img" :src="p.url || p" mode="aspectFill" />
					</swiper-item>
				</swiper>
				<view class="dots" v-if="photos.length > 1">
					<view v-for="(p, i) in photos" :key="i" class="dot" :class="{ on: i === photoIndex }" />
				</view>
			</view>
			<view class="sheet">
				<view class="name-row">
					<text class="name display-font">{{ profile.nickname || 'You' }}</text>
					<text class="age" v-if="profile.age">{{ profile.age }}</text>
					<view v-if="profile.is_verified" class="verified"><text>✓</text></view>
				</view>
				<view class="pill-row">
					<view class="pill" v-if="profile.job"><text>{{ profile.job }}</text></view>
					<view class="pill" v-if="profile.city"><text>{{ profile.city }}</text></view>
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
			</view>
		</scroll-view>
		<view v-else class="loading"><text>Loading…</text></view>
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiProfilePreview } from '@/api/profile.js'

const profile = ref({})
const photoIndex = ref(0)
const loading = ref(true)

const photos = computed(() => {
	const list = profile.value.photos || []
	if (list.length) return list
	if (profile.value.avatar_url) return [{ url: profile.value.avatar_url }]
	return [{ url: '' }]
})

onMounted(async () => {
	try {
		const res = await apiProfilePreview()
		profile.value = res.results || {}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Preview failed', icon: 'none' })
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

<!-- F-11: gap removed; prefer sibling margin -->
<style scoped>
.page {
	min-height: 100vh;
	background: var(--bg, #FFFDF6);
	padding-top: calc(env(safe-area-inset-top) + 8rpx);
}
.header {
	display: flex;
	flex-direction: row;
	align-items: center;
	padding: 16rpx 24rpx;
}
.back { color: var(--text, #111); font-size: 48rpx; width: 60rpx; }
.title { color: var(--text, #111); font-size: 40rpx; font-weight: 800; }
.sub {
	display: block;
	color: var(--muted, #888);
	font-size: 24rpx;
	padding: 0 32rpx 16rpx;
}
.scroller { height: calc(100vh - 160rpx); }
.hero { position: relative; height: 720rpx; }
.hero-swiper, .hero-img { width: 100%; height: 720rpx; }
.dots {
	position: absolute; left: 0; right: 0; bottom: 24rpx;
	display: flex; flex-direction: row; justify-content: center;
}
.dot { width: 12rpx; height: 12rpx; border-radius: 50%; background: rgba(255,255,255,0.45); }
.dot.on { background: #FFC629; }
.sheet {
	margin-top: -40rpx;
	background: var(--bg, #FFFDF6);
	border-radius: 32rpx 32rpx 0 0;
	padding: 36rpx 28rpx 80rpx;
	position: relative;
}
.name-row { display: flex; flex-direction: row; align-items: baseline margin-bottom: 16rpx; }
.name-row > text + text, .name-row > view + view { margin-left: 12rpx; }
.name { color: var(--text, #111); font-size: 48rpx; font-weight: 800; }
.age { color: var(--muted, #666); font-size: 40rpx; }
.verified {
	width: 36rpx; height: 36rpx; border-radius: 50%; background: #FFC629;
	display: flex; align-items: center; justify-content: center;
}
.verified text { font-size: 20rpx; color: #111; font-weight: 800; }
.pill-row { display: flex; flex-direction: row; flex-wrap: wrap; margin-bottom: 20rpx; }
.pill-row > view + view { margin-left: 12rpx; }
.pill {
	background: #FFF8E1; border-radius: 999rpx; padding: 10rpx 20rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.pill text { color: #333; font-size: 24rpx; }
.section { margin-bottom: 28rpx; }
.section-title {
	display: block; color: var(--text, #111); font-size: 30rpx; font-weight: 800; margin-bottom: 12rpx;
}
.section-body { display: block; color: var(--muted, #444); font-size: 28rpx; line-height: 1.45; }
.loading { padding: 80rpx; text-align: center; color: #888; }
</style>
