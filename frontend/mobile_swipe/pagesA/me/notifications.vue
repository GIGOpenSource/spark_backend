<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Notifications</text>
		</view>
		<view class="card card-switch" v-for="row in rows" :key="row.key">
			<view class="row-label">
				<text>{{ row.label }}</text>
				<text class="hint">{{ row.hint }}</text>
			</view>
			<switch :checked="prefs[row.key]" color="#FFC629" @change="(e) => toggle(row.key, e)" />
		</view>
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
	{ key: 'likes', label: 'New likes', hint: 'Beeline activity' },
	{ key: 'matches', label: 'Matches', hint: 'When you match' },
	{ key: 'messages', label: 'Messages', hint: 'Chat alerts' },
	{ key: 'marketing', label: 'Tips & offers', hint: 'Product updates' },
	{ key: 'silent_recall', label: 'Quiet reminders', hint: 'Come back nudges' },
]

onMounted(async () => {
	try {
		const res = await apiPushPrefsGet()
		Object.assign(prefs, res.results || {})
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
.page { min-height:100vh; background:#FFFDF6; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { color:#111; font-size:40rpx; font-weight:800; }
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(255,198,41,0.25);
}
.row-label { display:flex; flex-direction:column; flex:1; }
.row-label > text + text, .row-label > view + view { margin-top: 4rpx; }
.row-label text { color:#111; font-size:28rpx; }
.hint { color:#999; font-size:22rpx !important; }
</style>
