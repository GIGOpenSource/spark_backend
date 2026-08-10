<template>
	<view class="sheet-mask" v-if="show" @click="close">
		<view class="sheet" @click.stop>
			<text class="title">筛选</text>
			<view class="row">
				<text class="label">年龄</text>
				<input class="input" type="number" v-model="form.age_min" placeholder="18" />
				<text class="dash">-</text>
				<input class="input" type="number" v-model="form.age_max" placeholder="50" />
			</view>
			<view class="row">
				<text class="label">距离</text>
				<input class="input wide" type="number" v-model="form.distance_km" />
				<text class="unit">公里</text>
			</view>
			<text class="label block">性别</text>
			<view class="chips">
				<view class="chip" :class="{ on: form.gender === '' }" @click="form.gender = ''"><text>全部</text></view>
				<view class="chip" :class="{ on: form.gender === 'female' }" @click="form.gender = 'female'"><text>女生</text></view>
				<view class="chip" :class="{ on: form.gender === 'male' }" @click="form.gender = 'male'"><text>男生</text></view>
			</view>

			<view class="adv-head">
				<text class="adv-title">高级筛选</text>
				<text class="lock" v-if="!advancedUnlocked" @click="openGold">高级会员 🔒</text>
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }">
				<text class="label">类型</text>
				<view class="chips flex">
					<view class="chip sm" :class="{ on: form.recommend_type === 'precise' }" @click="setAdv('recommend_type','precise')"><text>精准</text></view>
					<view class="chip sm" :class="{ on: form.recommend_type === 'fun' }" @click="setAdv('recommend_type','fun')"><text>有趣</text></view>
				</view>
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }">
				<text class="label">MBTI</text>
				<input class="input wide" v-model="form.mbti" :disabled="!advancedUnlocked" placeholder="如 ENTP" @focus="guardAdv" />
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }">
				<text class="label">星座</text>
				<input class="input wide" v-model="form.zodiac" :disabled="!advancedUnlocked" placeholder="如 处女座" @focus="guardAdv" />
			</view>
			<text class="label block" :class="{ dim: !advancedUnlocked }">学历</text>
			<view class="chips" :class="{ dim: !advancedUnlocked }">
				<view
					v-for="t in educationOptions"
					:key="t"
					class="chip sm"
					:class="{ on: form.education === t }"
					@click="setEducation(t)"
				>
					<text>{{ t }}</text>
				</view>
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }" @click="toggleAudience">
				<text class="label">谁能看到我</text>
				<view class="chip sm" :class="{ on: form.audience_strict }"><text>{{ form.audience_strict ? '仅偏好' : '所有人' }}</text></view>
			</view>

			<view class="btn" @click="save"><text>应用</text></view>
		</view>
		<VipSheet v-model:show="showVip" reason="need_gold" @purchased="onPurchased" />
	</view>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { apiFiltersGet, apiFiltersSave } from '@/api/profile.js'
import { trackClick } from '@/utils/analytics.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['update:show', 'saved'])
const form = reactive({
	age_min: 18, age_max: 50, distance_km: 100, gender: '',
	mbti: '', zodiac: '', education: '', recommend_type: 'precise', audience_strict: false
})
const educationOptions = ['高中', '本科', '硕士', '博士']
const advancedUnlocked = ref(false)
const showVip = ref(false)

async function reloadFilters() {
	try {
		const res = await apiFiltersGet()
		Object.assign(form, res.results || {})
		advancedUnlocked.value = !!(res.results && res.results.advanced_unlocked)
	} catch (e) {
		uni.showToast({ title: '筛选加载失败', icon: 'none' })
	}
}

watch(() => props.show, async (v) => {
	if (!v) return
	await reloadFilters()
})

function onPurchased() {
	showVip.value = false
	reloadFilters()
}

function close() {
	emit('update:show', false)
}

function openGold() {
	showVip.value = true
}

function guardAdv() {
	if (!advancedUnlocked.value) showVip.value = true
}

function setAdv(key, val) {
	if (!advancedUnlocked.value) {
		showVip.value = true
		return
	}
	form[key] = val
}

function setEducation(val) {
	if (!advancedUnlocked.value) {
		showVip.value = true
		return
	}
	form.education = form.education === val ? '' : val
}

function toggleAudience() {
	if (!advancedUnlocked.value) {
		showVip.value = true
		return
	}
	form.audience_strict = !form.audience_strict
}

async function save() {
	trackClick('filter_apply')
	const payload = {
		age_min: Number(form.age_min) || 18,
		age_max: Number(form.age_max) || 50,
		distance_km: Number(form.distance_km) || 100,
		gender: form.gender || ''
	}
	if (advancedUnlocked.value) {
		payload.mbti = form.mbti
		payload.zodiac = form.zodiac
		payload.education = form.education || ''
		payload.recommend_type = form.recommend_type
		payload.audience_strict = !!form.audience_strict
	}
	try {
		await apiFiltersSave(payload)
		emit('saved')
		close()
	} catch (e) {
		if (e && e.message === 'need_gold') showVip.value = true
		else uni.showToast({ title: (e && e.message) || '应用失败', icon: 'none' })
	}
}
</script>

<style scoped>
.sheet-mask {
	position: fixed; left:0; right:0; top:0; bottom:0;
	background: rgba(0,0,0,.4); z-index: 1000;
	display: flex; align-items: flex-end;
}
.sheet {
	width: 100%; background: #FFFFFF; border-radius: 32rpx 32rpx 0 0;
	padding: 40rpx 32rpx calc(env(safe-area-inset-bottom) + 40rpx);
	max-height: 85vh; overflow-y: auto;
}
.title { display:block; color:#222; font-size:36rpx; font-weight:800; margin-bottom:24rpx; }
.row { display:flex; flex-direction:row; align-items:center; margin-bottom:20rpx; }
.label { color:#666; width:160rpx; font-size:26rpx; }
.label.block { display:block; width:auto; margin-bottom:12rpx; color:#666; }
.input {
	background:#FFF7FA; color:#222; border-radius:12rpx; padding:16rpx; width:120rpx; font-size:26rpx;
	border: 1px solid rgba(255,107,154,0.25);
}
.input.wide { flex:1; width:auto; }
.dash { color:#333; margin:0 12rpx; }
.unit { color:#888; margin-left:10rpx; font-size:22rpx; }
.chips { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:20rpx; }
.chips.flex { flex:1; }
.chip {
	border-radius:999rpx; padding:14rpx 24rpx; margin-right:10rpx; margin-bottom:10rpx;
	background:#FFF7FA; border: 1px solid rgba(255,107,154,0.2);
}
.chip.sm { padding:10rpx 18rpx; }
.chip text { color:#333; font-size:24rpx; }
.chip.on { background:rgba(255,107,154,0.15); border-color:#FF6B9A; }
.chip.on text { color:#FF6B9A; font-weight:700; }
.adv-head {
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	margin: 12rpx 0 16rpx; padding-top: 12rpx; border-top: 1px solid rgba(255,107,154,0.12);
}
.adv-title { color:#222; font-size:28rpx; font-weight:700; }
.lock { color:#FF6B9A; font-size:24rpx; }
.dim { opacity: 0.45; }
.btn {
	margin-top:20rpx; background: linear-gradient(90deg,#FF6B9A,#FF8FB3); border-radius:999rpx; padding:24rpx; text-align:center;
}
.btn text { color:#fff; font-weight:800; }
</style>
