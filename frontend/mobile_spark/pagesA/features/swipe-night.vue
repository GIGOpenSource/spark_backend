<template>
	<view class="page">
		<view class="header"><text class="back" @click="back">‹</text><text class="title">Swipe Night</text></view>
		<text class="sub">Tonight’s picks · mutual matches after the window</text>
		<view class="card" v-if="session">
			<text>Session {{ session.status }}</text>
			<text class="muted">Ends {{ format(session.ends_at) }}</text>
		</view>
		<view class="grid">
			<view v-for="u in list" :key="u.id" class="tile" @click="pick(u)">
				<image :src="u.avatar_url" class="img" mode="aspectFill" />
				<text class="name">{{ u.nickname }}</text>
			</view>
		</view>
		<view class="btn" @click="settle"><text>Settle matches</text></view>
		<view v-if="!list.length && !loading" class="empty"><text>No candidates yet — check back tonight</text></view>
	</view>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { apiSwipeNightCurrent, apiSwipeNightCandidates, apiSwipeNightPick, apiSwipeNightSettle } from '@/api/swipeNight.js'
const session = ref(null)
const list = ref([])
const loading = ref(false)
function back() { uni.navigateBack() }
function format(iso) { return iso ? new Date(iso).toLocaleString() : '' }
async function load() {
	loading.value = true
	try {
		const s = await apiSwipeNightCurrent()
		session.value = (s.results && (s.results.session || s.results)) || null
		const c = await apiSwipeNightCandidates()
		list.value = (c.results && c.results.list) || []
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' })
	}
	loading.value = false
}
async function pick(u) {
	try {
		await apiSwipeNightPick(u.id)
		uni.showToast({ title: 'Picked', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' })
	}
}
async function settle() {
	try {
		const res = await apiSwipeNightSettle()
		const n = (res.results && res.results.matched) || 0
		uni.showToast({ title: `Matched ${n}`, icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' })
	}
}
onMounted(load)
</script>
<style scoped>
.page { min-height:100vh; background:var(--bg,#fff); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; align-items:center; margin-bottom:12rpx; }
.back { font-size:48rpx; width:60rpx; }
.title { font-size:40rpx; font-weight:700; }
.sub { display:block; color:var(--muted,#666); margin-bottom:20rpx; }
.card { background:var(--surface,#f8f8f8); padding:20rpx; border-radius:16rpx; margin-bottom:20rpx; }
.muted { display:block; color:var(--muted,#666); font-size:24rpx; margin-top:8rpx; }
.grid { display:flex; flex-wrap:wrap }
.grid > view { margin: 0 8rpx 8rpx 0; }
.tile { width:calc(50% - 8rpx); }
.img { width:100%; height:320rpx; border-radius:16rpx; background:#ddd; }
.name { display:block; margin-top:8rpx; font-weight:600; }
.btn { margin-top:28rpx; background:#FF4458; color:#fff; text-align:center; padding:24rpx; border-radius:999rpx; }
.btn text { color:#fff; font-weight:700; }
.empty { margin-top:40rpx; color:var(--muted,#666); text-align:center; }
</style>
