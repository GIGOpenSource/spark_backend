<template>
	<view class="page">
		<view class="header"><text class="back" @click="back">‹</text><text class="title">Campus</text></view>
		<input class="input" v-model="school" placeholder="School name" />
		<input class="input" v-model="eduEmail" placeholder="edu email (optional)" />
		<view class="btn" @click="bind"><text>Bind school</text></view>
		<view class="btn ghost" @click="verify"><text>Verify .edu stub</text></view>
		<text class="sec">Campus feed</text>
		<view v-for="u in list" :key="u.id" class="row" @click="open(u)">
			<image :src="u.avatar_url" class="av" mode="aspectFill" />
			<text>{{ u.nickname }}{{ u.age ? `, ${u.age}` : '' }}</text>
		</view>
	</view>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { apiCampusBind, apiCampusVerifyStub, apiCampusFeed } from '@/api/campus.js'
const school = ref('')
const eduEmail = ref('')
const list = ref([])
function back() { uni.navigateBack() }
function open(u) { uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${u.id}` }) }
async function bind() {
	try {
		await apiCampusBind({ school: school.value, edu_email: eduEmail.value })
		uni.showToast({ title: 'Bound', icon: 'none' })
		load()
	} catch (e) { uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' }) }
}
async function verify() {
	try {
		await apiCampusVerifyStub()
		uni.showToast({ title: 'Verified', icon: 'none' })
	} catch (e) { uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' }) }
}
async function load() {
	try {
		const res = await apiCampusFeed()
		list.value = (res.results && res.results.list) || []
	} catch (e) { list.value = [] }
}
onMounted(load)
</script>
<style scoped>
.page { min-height:100vh; background:var(--bg,#fff); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; align-items:center; margin-bottom:12rpx; }
.back { font-size:48rpx; width:60rpx; }
.title { font-size:40rpx; font-weight:700; }
.input { background:var(--surface,#f8f8f8); padding:20rpx; border-radius:12rpx; margin-bottom:12rpx; }
.btn { background:#FF4458; padding:24rpx; border-radius:999rpx; text-align:center; margin-bottom:12rpx; }
.btn text { color:#fff; font-weight:700; }
.btn.ghost { background:transparent; border:2rpx solid #FF4458; }
.btn.ghost text { color:#FF4458; }
.sec { display:block; color:var(--muted,#666); margin: 20rpx 0 12rpx; }
.row { display:flex; align-items:center; padding:16rpx 0; }
.row > text + text, .row > view + view { margin-left: 16rpx; }
.av { width:72rpx; height:72rpx; border-radius:50%; background:#ddd; }
</style>
