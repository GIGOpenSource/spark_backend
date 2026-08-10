<template>
	<view class="sheet-mask" v-if="show" @click="close">
		<view class="sheet" @click.stop>
			<text class="title">Filters</text>
			<view class="row col">
				<text class="label" id="age-label">Age {{ form.age_min }}–{{ form.age_max }}</text>
				<slider
					aria-labelledby="age-label"
					:value="form.age_min"
					:min="18"
					:max="80"
					activeColor="#FF4458"
					@change="(e) => form.age_min = Math.min(Number(e.detail.value), Number(form.age_max))"
				/>
				<slider
					aria-label="Maximum age"
					:value="form.age_max"
					:min="18"
					:max="80"
					activeColor="#FF4458"
					@change="(e) => form.age_max = Math.max(Number(e.detail.value), Number(form.age_min))"
				/>
			</view>
			<view class="row col">
				<text class="label" id="dist-label">Distance {{ form.distance_km }} km</text>
				<slider
					aria-labelledby="dist-label"
					:value="form.distance_km"
					:min="1"
					:max="200"
					activeColor="#FF4458"
					@change="(e) => form.distance_km = Number(e.detail.value)"
				/>
			</view>
			<text class="label block">Gender</text>
			<view class="chips">
				<view class="chip" :class="{ on: form.gender === '' }" @click="form.gender = ''"><text>All</text></view>
				<view class="chip" :class="{ on: form.gender === 'female' }" @click="form.gender = 'female'"><text>Women</text></view>
				<view class="chip" :class="{ on: form.gender === 'male' }" @click="form.gender = 'male'"><text>Men</text></view>
			</view>

			<view class="adv-head">
				<text class="adv-title">Advanced</text>
				<text class="lock" v-if="!advancedUnlocked" @click="openGold">Gold 🔒</text>
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
				<input class="input wide" v-model="form.mbti" :disabled="!advancedUnlocked" placeholder="e.g. ENTP" placeholder-class="ph" @focus="guardAdv" />
			</view>
			<view class="row" :class="{ dim: !advancedUnlocked }">
				<text class="label">Zodiac</text>
				<input class="input wide" v-model="form.zodiac" :disabled="!advancedUnlocked" placeholder="e.g. Virgo" placeholder-class="ph" @focus="guardAdv" />
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
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import { trackClick } from '@/utils/analytics.js'

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
	background: rgba(0,0,0,.55); z-index: 1000;
	display: flex; align-items: flex-end;
}
.sheet {
	width: 100%; background: #FFFFFF; border-radius: 32rpx 32rpx 0 0;
	padding: 40rpx 32rpx calc(env(safe-area-inset-bottom) + 40rpx);
	max-height: 85vh; overflow-y: auto;
}
.title { display:block; color:#111; font-size:36rpx; font-weight:700; margin-bottom:24rpx; }
.row { display:flex; flex-direction:row; align-items:center; margin-bottom:20rpx; }
.row.col { flex-direction:column; align-items:stretch; }
.label { color:#666; width:160rpx; font-size:26rpx; }
.label.block { display:block; width:auto; margin-bottom:12rpx; }
.input {
	background:#F3F0F7; color:#111; border-radius:12rpx; padding:16rpx; width:120rpx; font-size:26rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.input.wide { flex:1; width:auto; }
.dash { color:#111; margin:0 12rpx; }
.ph { color:#999; }
.unit { color:#666; margin-left:10rpx; font-size:22rpx; }
.chips { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:20rpx; }
.chips.flex { flex:1; }
.chip {
	border-radius:999rpx; padding:14rpx 24rpx; margin-right:10rpx; margin-bottom:10rpx;
	background:#F3F0F7; border: 1px solid rgba(0,0,0,0.04);
}
.chip.sm { padding:10rpx 18rpx; }
.chip text { color:#222; font-size:24rpx; }
.chip.on { background:rgba(253,38,122,0.12); border-color: rgba(253,38,122,0.3); }
.chip.on text { color:#FD267A; }
.adv-head {
	display:flex; flex-direction:row; justify-content:space-between; align-items:center;
	margin: 12rpx 0 16rpx; padding-top: 12rpx; border-top: 1px solid rgba(0,0,0,0.06);
}
.adv-title { color:#111; font-size:28rpx; font-weight:600; }
.lock { color:#FF4B55; font-size:24rpx; }
.dim { opacity: 0.45; }
.btn {
	margin-top:20rpx; background: linear-gradient(90deg, #FD267A, #FF6036); border-radius:999rpx; padding:24rpx; text-align:center;
}
.btn text { color:#fff; font-weight:700; }
</style>
