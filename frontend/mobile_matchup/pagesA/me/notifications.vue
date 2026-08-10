<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">通知设置</text>
		</view>

		<view class="card card-switch" v-for="row in rows" :key="row.key">
			<view class="row-label">
				<text>{{ row.label }}</text>
				<text class="hint">{{ row.hint }}</text>
			</view>
			<switch :checked="!!prefs[row.key]" color="#FF6B9A" @change="(e) => toggle(row.key, e)" />
		</view>

		<view class="save" :class="{ busy: saving }" @click="save"><text>{{ saving ? '保存中…' : '保存' }}</text></view>
	</view>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { apiPushPrefsGet, apiPushPrefsUpdate } from '@/api/push.js'

const prefs = reactive({
	match: true,
	message: true,
	like: true,
	marketing: false,
})
const saving = ref(false)

const rows = [
	{ key: 'match', label: '配对通知', hint: '有人与你配对时' },
	{ key: 'message', label: '消息通知', hint: '新消息与问答提醒' },
	{ key: 'like', label: '喜欢通知', hint: '有人喜欢你时' },
	{ key: 'marketing', label: '活动与优惠', hint: '会员与运营活动' },
]

onMounted(async () => {
	try {
		const res = await apiPushPrefsGet()
		const data = res.results || {}
		Object.keys(prefs).forEach((k) => {
			if (typeof data[k] === 'boolean') prefs[k] = data[k]
		})
	} catch (e) {}
})

function toggle(key, e) {
	prefs[key] = !!(e && e.detail && e.detail.value)
}

async function save() {
	if (saving.value) return
	saving.value = true
	try {
		await apiPushPrefsUpdate({ ...prefs })
		uni.showToast({ title: '已保存', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '保存失败', icon: 'none' })
	}
	saving.value = false
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFF7FA; padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:#222; font-size:48rpx; width:60rpx; }
.title { color:#222; font-size:40rpx; font-weight:700; }
.card {
	background:#fff; border-radius:20rpx; padding:28rpx; margin-bottom:16rpx;
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	border: 1px solid rgba(255,107,154,0.12);
}
.row-label { flex:1; margin-right:16rpx; }
.row-label text { display:block; color:#222; font-size:28rpx; }
.hint { color:#999 !important; font-size:22rpx !important; margin-top:6rpx; }
.save {
	margin-top: 32rpx; background: linear-gradient(90deg,#FF6B9A,#FF8FB3);
	border-radius:999rpx; padding:28rpx; text-align:center;
}
.save.busy { opacity:0.7; }
.save text { color:#fff; font-weight:700; }
</style>
