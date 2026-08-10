<template>
	<view class="mask" v-if="show" @click="close">
		<view class="sheet" @click.stop>
			<text class="title">Super Like + note</text>
			<text class="sub">Add a short note on their photo</text>
			<scroll-view v-if="photos.length > 1" scroll-x class="photo-row">
				<view
					v-for="(p, i) in photos"
					:key="i"
					class="thumb"
					:class="{ on: i === selectedIndex }"
					@click="selectedIndex = i"
				>
					<image :src="p.url || p" class="thumb-img" mode="aspectFill" />
				</view>
			</scroll-view>
			<image v-if="activePhoto" :src="activePhoto" class="photo" mode="aspectFill" />
			<textarea class="input" v-model="message" maxlength="150" placeholder="Say something specific…" placeholder-class="ph" auto-height />
			<text class="count">{{ message.length }}/150</text>
			<view class="btn" :class="{ disabled: !canSend }" @click="submit"><text>Send Super Like</text></view>
			<view class="cancel" @click="close"><text>Cancel</text></view>
		</view>
	</view>
</template>
<script setup>
import { ref, computed, watch } from 'vue'
import { apiCompliment } from '@/api/likes.js'
import { trackClick } from '@/utils/analytics.js'

const props = defineProps({
	show: Boolean,
	user: { type: Object, default: null },
	photoUrl: { type: String, default: '' },
})
const emit = defineEmits(['update:show', 'sent', 'need-shop'])
const message = ref('')
const sending = ref(false)
const selectedIndex = ref(0)
const photos = computed(() => {
	const u = props.user || {}
	const list = Array.isArray(u.photos) ? u.photos : []
	if (list.length) return list
	const fallback = props.photoUrl || u.avatar_url || ''
	return fallback ? [{ url: fallback }] : []
})
const activePhoto = computed(() => {
	const p = photos.value[selectedIndex.value]
	return (p && (p.url || p)) || ''
})
const canSend = computed(() => message.value.trim().length > 0 && !!props.user && !sending.value)
watch(() => props.show, (v) => {
	if (v) {
		message.value = ''
		selectedIndex.value = 0
	}
})
function close() { emit('update:show', false) }
async function submit() {
	if (!canSend.value) return
	trackClick('compliment_send')
	sending.value = true
	try {
		await apiCompliment({
			target_id: props.user.id,
			message: message.value.trim(),
			photo_url: activePhoto.value,
			target_kind: 'photo',
		})
		emit('sent')
		close()
	} catch (e) {
		const msg = (e && e.message) || ''
		if (/need_super_like|need_shop/.test(msg)) emit('need-shop')
		else uni.showToast({ title: msg || 'Failed', icon: 'none' })
	} finally {
		sending.value = false
	}
}
</script>
<style scoped>
.mask { position:fixed; inset:0; z-index:1200; background:rgba(0,0,0,.45); display:flex; align-items:flex-end; }
.sheet { width:100%; background:#fff; border-radius:32rpx 32rpx 0 0; padding:32rpx 28rpx calc(env(safe-area-inset-bottom) + 28rpx); }
.title { display:block; font-size:36rpx; font-weight:800; }
.sub { display:block; color:#666; font-size:24rpx; margin:8rpx 0 20rpx; }
.photo-row { white-space:nowrap; margin-bottom:16rpx; }
.thumb { display:inline-block; width:96rpx; height:96rpx; margin-right:12rpx; border-radius:12rpx; overflow:hidden; border:4rpx solid transparent; }
.thumb.on { border-color:#FF4458; }
.thumb-img,.photo { width:100%; height:100%; }
.photo { height:280rpx; border-radius:16rpx; margin-bottom:16rpx; }
.input { width:100%; min-height:120rpx; background:#F8F8F8; border-radius:16rpx; padding:20rpx; box-sizing:border-box; }
.ph { color:#999; }
.count { display:block; text-align:right; color:#999; font-size:22rpx; margin:8rpx 0 16rpx; }
.btn { background:#FF4458; border-radius:999rpx; height:88rpx; display:flex; align-items:center; justify-content:center; }
.btn.disabled { opacity:.5; }
.btn text { color:#fff; font-weight:700; }
.cancel { text-align:center; margin-top:16rpx; color:#666; }
</style>
