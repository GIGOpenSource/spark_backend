<template>
	<view class="page">
		<view class="header"><text class="back" @click="back">‹</text><text class="title">Face to Face</text></view>
		<text class="sub">Short window · nearby only</text>
		<view class="btn" @click="start"><text>{{ active ? 'Restart' : 'Start 30 min' }}</text></view>
		<view class="btn ghost" v-if="active" @click="stop"><text>Stop</text></view>
		<view v-for="u in list" :key="u.id" class="row" @click="open(u)">
			<image :src="u.avatar_url" class="av" mode="aspectFill" />
			<view>
				<text class="name">{{ u.nickname }}</text>
				<text class="dist" v-if="u.distance_km != null">{{ u.distance_km }} km</text>
			</view>
		</view>
		<view v-if="!list.length" class="empty"><text>No one nearby yet</text></view>
	</view>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { apiF2FStart, apiF2FFeed, apiF2FStop } from '@/api/faceToFace.js'
const list = ref([])
const active = ref(false)
function back() { uni.navigateBack() }
function open(u) { uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${u.id}` }) }
async function start() {
	try {
		const loc = await new Promise((resolve, reject) => {
			uni.getLocation({ type: 'gcj02', success: resolve, fail: reject })
		})
		await apiF2FStart({ lat: loc.latitude, lng: loc.longitude, minutes: 30 })
		active.value = true
		load()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Location required', icon: 'none' })
	}
}
async function stop() {
	try {
		await apiF2FStop()
		active.value = false
		list.value = []
	} catch (e) {}
}
async function load() {
	try {
		const res = await apiF2FFeed()
		list.value = (res.results && res.results.list) || []
		active.value = !!(res.results && res.results.active)
	} catch (e) { list.value = [] }
}
onMounted(load)
</script>
<style scoped>
.page { min-height:100vh; background:var(--bg,#fff); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; align-items:center; margin-bottom:12rpx; }
.back { font-size:48rpx; width:60rpx; }
.title { font-size:40rpx; font-weight:700; }
.sub { display:block; color:var(--muted,#666); margin-bottom:16rpx; }
.btn { background:#FF4458; padding:24rpx; border-radius:999rpx; text-align:center; margin-bottom:12rpx; }
.btn text { color:#fff; font-weight:700; }
.btn.ghost { background:transparent; border:2rpx solid #FF4458; }
.btn.ghost text { color:#FF4458; }
.row { display:flex; align-items:center; padding:16rpx 0; }
.row > text + text, .row > view + view { margin-left: 16rpx; }
.av { width:72rpx; height:72rpx; border-radius:50%; background:#ddd; }
.name { display:block; font-weight:600; }
.dist { display:block; color:var(--muted,#666); font-size:22rpx; }
.empty { color:var(--muted,#666); margin-top:24rpx; }
</style>
