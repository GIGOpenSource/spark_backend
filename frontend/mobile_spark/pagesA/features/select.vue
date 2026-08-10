<template>
	<view class="page">
		<view class="header"><text class="back" @click="back">‹</text><text class="title">Select</text></view>
		<text class="sub">Apply for the curated Select pool</text>
		<view class="card"><text>Status: {{ status || '—' }}</text></view>
		<view class="btn" @click="apply"><text>Apply</text></view>
		<text class="sec">Select feed</text>
		<view v-for="u in list" :key="u.id" class="row" @click="open(u)">
			<image :src="u.avatar_url" class="av" mode="aspectFill" />
			<text>{{ u.nickname }}</text>
		</view>
		<view v-if="!list.length" class="empty"><text>Locked until selected (or Gold+)</text></view>
	</view>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { apiSelectApply, apiSelectStatus, apiSelectFeed } from '@/api/select.js'
const status = ref('')
const list = ref([])
function back() { uni.navigateBack() }
function open(u) { uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${u.id}` }) }
async function apply() {
	try {
		await apiSelectApply()
		uni.showToast({ title: 'Applied', icon: 'none' })
		load()
	} catch (e) { uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' }) }
}
async function load() {
	try {
		const s = await apiSelectStatus()
		status.value = (s.results && (s.results.status || s.results.state)) || ''
		const f = await apiSelectFeed()
		list.value = (f.results && f.results.list) || []
	} catch (e) {
		list.value = []
	}
}
onMounted(load)
</script>
<style scoped>
.page { min-height:100vh; background:var(--bg,#fff); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; align-items:center; margin-bottom:12rpx; }
.back { font-size:48rpx; width:60rpx; }
.title { font-size:40rpx; font-weight:700; }
.sub,.sec { display:block; color:var(--muted,#666); margin: 12rpx 0; }
.card { background:var(--surface,#f8f8f8); padding:20rpx; border-radius:16rpx; }
.btn { background:#FF4458; padding:24rpx; border-radius:999rpx; text-align:center; margin: 20rpx 0; }
.btn text { color:#fff; font-weight:700; }
.row { display:flex; align-items:center; padding:16rpx 0; }
.row > text + text, .row > view + view { margin-left: 16rpx; }
.av { width:72rpx; height:72rpx; border-radius:50%; background:#ddd; }
.empty { color:var(--muted,#666); }
</style>
