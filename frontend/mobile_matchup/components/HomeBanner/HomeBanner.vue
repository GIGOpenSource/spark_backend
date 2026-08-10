<template>
	<view class="banner-slot" v-if="visible" @click="onTap">
		<view class="banner-inner" :class="{ ops: !!banner.ops }">
			<text class="banner-title">{{ banner.title }}</text>
			<text class="banner-sub" v-if="banner.subtitle">{{ banner.subtitle }}</text>
		</view>
		<text class="banner-close" @click.stop="dismiss">×</text>
	</view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const TAB_PREFIXES = [
	'/pages/discover/index',
	'/pages/likes/index',
	'/pages/chat/index',
	'/pages/me/index',
]

const props = defineProps({
	/** From recommend feed: banners[] / official / hooks */
	items: { type: Array, default: () => [] },
	/** Soft fallback when API has no hooks */
	fallback: {
		type: Object,
		default: () => ({
			title: '今日推荐名额有限',
			subtitle: '认真滑完 21 人，遇见更对的人',
			action: 'discover',
		}),
	},
	dismissKey: { type: String, default: 'matchup_home_banner_dismissed' },
})

const emit = defineEmits(['action'])
const dismissed = ref(!!uni.getStorageSync(props.dismissKey))

watch(() => props.dismissKey, (k) => {
	dismissed.value = !!uni.getStorageSync(k)
})

const banner = computed(() => {
	const list = Array.isArray(props.items) ? props.items : []
	const first = list.find((x) => x && (x.title || x.text || x.image_url))
	if (first) {
		return {
			ops: true,
			title: first.title || first.text || '官方推荐',
			subtitle: first.subtitle || first.desc || '',
			url: first.url || first.link || first.deep_link || first.path || '',
			deep_link: first.deep_link || first.path || '',
			action: first.action || 'link',
			raw: first,
		}
	}
	return { ops: false, ...(props.fallback || {}) }
})

const visible = computed(() => !dismissed.value && !!(banner.value && banner.value.title))

function dismiss() {
	dismissed.value = true
	uni.setStorageSync(props.dismissKey, Date.now())
}

function isTabPath(path) {
	const p = (path || '').split('?')[0]
	return TAB_PREFIXES.some((t) => p === t || p.endsWith(t))
}

function navigateInApp(path) {
	if (!path || typeof path !== 'string') return false
	let url = path.trim()
	if (!url.startsWith('/')) url = '/' + url
	if (!url.startsWith('/pages')) return false
	if (isTabPath(url)) {
		uni.switchTab({ url: url.split('?')[0] })
	} else {
		uni.navigateTo({
			url,
			fail: () => uni.switchTab({ url: '/pages/discover/index' }),
		})
	}
	return true
}

function onTap() {
	emit('action', banner.value)
	const deep = banner.value.deep_link || ''
	const url = banner.value.url || ''
	if (deep && navigateInApp(deep)) return
	if (url.startsWith('/pages') && navigateInApp(url)) return
	if (url) {
		// #ifdef H5
		window.open(url, '_blank')
		// #endif
		// #ifndef H5
		uni.setClipboardData({ data: url })
		uni.showToast({ title: '链接已复制', icon: 'none' })
		// #endif
	}
}
</script>

<style scoped>
.banner-slot {
	margin: 0 0 16rpx;
	position: relative;
	border-radius: 20rpx;
	overflow: hidden;
	background: linear-gradient(90deg, rgba(255,107,154,0.14), rgba(255,143,179,0.1));
	border: 1px solid rgba(255,107,154,0.22);
}
.banner-inner { padding: 22rpx 56rpx 22rpx 24rpx; }
.banner-inner.ops {
	background: linear-gradient(90deg, rgba(255,198,41,0.18), rgba(255,107,154,0.12));
}
.banner-title { display:block; color:#222; font-size:26rpx; font-weight:700; }
.banner-sub { display:block; color:#888; font-size:22rpx; margin-top:6rpx; }
.banner-close {
	position:absolute; right:16rpx; top:12rpx; color:#999; font-size:32rpx; line-height:1; padding:8rpx;
}
</style>
