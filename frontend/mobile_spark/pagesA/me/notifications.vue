<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Notifications</text>
		</view>
		<text class="section">Push preferences</text>
		<view class="card card-switch" v-for="row in rows" :key="row.key">
			<text>{{ row.label }}</text>
			<switch :checked="prefs[row.key]" color="#FD267A" @change="(e) => toggle(row.key, e)" />
		</view>
		<view class="hint"><text>Changes sync to the server immediately.</text></view>
	</view>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { apiPushPrefsGet, apiPushPrefsUpdate } from '@/api/push.js'

const prefs = reactive({
	likes: true,
	matches: true,
	messages: true,
	marketing: false,
	silent_recall: true,
})

const rows = [
	{ key: 'likes', label: 'New likes' },
	{ key: 'matches', label: 'New matches' },
	{ key: 'messages', label: 'Messages' },
	{ key: 'marketing', label: 'Tips & offers' },
	{ key: 'silent_recall', label: 'Quiet re-engagement' },
]

onMounted(async () => {
	try {
		const res = await apiPushPrefsGet()
		const data = res.results || {}
		rows.forEach((r) => {
			if (typeof data[r.key] === 'boolean') prefs[r.key] = data[r.key]
		})
	} catch (e) {}
})

async function toggle(key, e) {
	const next = !!(e && e.detail && e.detail.value)
	const prev = prefs[key]
	prefs[key] = next
	try {
		await apiPushPrefsUpdate({ [key]: next })
	} catch (err) {
		prefs[key] = prev
		uni.showToast({ title: (err && err.message) || 'Update failed', icon: 'none' })
	}
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFFFFF; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { display:block; color:#111; font-size:40rpx; font-weight:700; }
.section {
	display:block; color:#666; font-size:22rpx; letter-spacing:1rpx;
	text-transform:uppercase; margin: 12rpx 8rpx 12rpx;
}
.card {
	background:#FFFFFF; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(0,0,0,0.06);
}
.card text { color:#111; font-size:28rpx; }
.hint { margin-top: 20rpx; padding: 0 8rpx; }
.hint text { color:#999; font-size:22rpx; }
</style>
