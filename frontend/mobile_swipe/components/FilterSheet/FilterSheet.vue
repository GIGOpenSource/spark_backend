<template>
	<view class="sheet-mask" v-if="show" @click="close">
		<view class="sheet" @click.stop>
			<text class="title">Filters</text>
			<text class="sub-hint">Discovery & Beeline preferences</text>
			<view class="row">
				<text class="label">Age</text>
				<input class="input" type="number" v-model="form.age_min" placeholder="18" />
				<text class="dash">-</text>
				<input class="input" type="number" v-model="form.age_max" placeholder="50" />
			</view>
			<view class="row">
				<text class="label">Distance</text>
				<input class="input wide" type="number" v-model="form.distance_km" />
				<text class="unit">km</text>
			</view>
			<text class="label block">Gender</text>
			<view class="chips">
				<view class="chip" :class="{ on: form.gender === '' }" @click="form.gender = ''"><text>All</text></view>
				<view class="chip" :class="{ on: form.gender === 'female' }" @click="form.gender = 'female'"><text>Women</text></view>
				<view class="chip" :class="{ on: form.gender === 'male' }" @click="form.gender = 'male'"><text>Men</text></view>
			</view>

			<view class="adv-head">
				<text class="adv-title">Advanced</text>
				<text class="lock" v-if="!advancedUnlocked" @click="openGold">Premium+ 🔒</text>
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }">
				<text class="label">Type</text>
				<view class="chips flex">
					<view class="chip sm" :class="{ on: form.recommend_type === 'precise' }" @click="setAdv('recommend_type','precise')"><text>Precise</text></view>
					<view class="chip sm" :class="{ on: form.recommend_type === 'fun' }" @click="setAdv('recommend_type','fun')"><text>Fun</text></view>
				</view>
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }">
				<text class="label">MBTI</text>
				<input class="input wide" v-model="form.mbti" :disabled="!advancedUnlocked" placeholder="e.g. ENTP" @focus="guardAdv" />
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }">
				<text class="label">Zodiac</text>
				<input class="input wide" v-model="form.zodiac" :disabled="!advancedUnlocked" placeholder="e.g. Virgo" @focus="guardAdv" />
			</view>
			<text class="label block" :class="{ dim: !advancedUnlocked }">Education</text>
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
				<text class="label">Who can see me</text>
				<view class="chip sm" :class="{ on: form.audience_strict }"><text>{{ form.audience_strict ? 'Prefs only' : 'Everyone' }}</text></view>
			</view>

			<view class="btn" @click="save"><text>Apply</text></view>
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
const educationOptions = ['High school', 'Bachelor', 'Master', 'PhD']
const advancedUnlocked = ref(false)
const showVip = ref(false)

async function reloadFilters() {
	try {
		const res = await apiFiltersGet()
		Object.assign(form, res.results || {})
		advancedUnlocked.value = !!(res.results && res.results.advanced_unlocked)
	} catch (e) {
		uni.showToast({ title: 'Failed to load filters', icon: 'none' })
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
		else uni.showToast({ title: (e && e.message) || 'Apply failed', icon: 'none' })
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
	width: 100%; background: #FFFDF6; border-radius: 32rpx 32rpx 0 0;
	padding: 40rpx 32rpx calc(env(safe-area-inset-bottom) + 40rpx);
	max-height: 85vh; overflow-y: auto;
}
.title { display:block; color:#1A1A1A; font-size:36rpx; font-weight:800; margin-bottom:8rpx; }
.sub-hint { display:block; color:#888; font-size:22rpx; margin-bottom:24rpx; }
.row { display:flex; flex-direction:row; align-items:center; margin-bottom:20rpx; }
.label { color:#666; width:160rpx; font-size:26rpx; }
.label.block { display:block; width:auto; margin-bottom:12rpx; }
.input {
	background:#fff; color:#1A1A1A; border-radius:12rpx; padding:16rpx; width:120rpx; font-size:26rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.input.wide { flex:1; width:auto; }
.dash { color:#333; margin:0 12rpx; }
.unit { color:#888; margin-left:10rpx; font-size:22rpx; }
.chips { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:20rpx; }
.chips.flex { flex:1; }
.chip {
	border-radius:999rpx; padding:14rpx 24rpx; margin-right:10rpx; margin-bottom:10rpx;
	background:#fff; border: 1px solid rgba(0,0,0,0.08);
}
.chip.sm { padding:10rpx 18rpx; }
.chip text { color:#333; font-size:24rpx; }
.chip.on { background:#FFC629; border-color:#FFC629; }
.chip.on text { color:#1A1A1A; font-weight:700; }
.adv-head {
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	margin: 12rpx 0 16rpx; padding-top: 12rpx; border-top: 1px solid rgba(0,0,0,0.06);
}
.adv-title { color:#1A1A1A; font-size:28rpx; font-weight:700; }
.lock { color:#C9A000; font-size:24rpx; }
.dim { opacity: 0.45; }
.btn {
	margin-top:20rpx; background:#FFC629; border-radius:999rpx; padding:24rpx; text-align:center;
}
.btn text { color:#1A1A1A; font-weight:800; }
</style>
