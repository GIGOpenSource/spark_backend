<template>
	<view class="sheet-mask" v-if="show" @click="close">
		<view class="sheet" @click.stop>
			<text class="title">Passport</text>
			<text class="sub">Change your discovery location · Plus</text>
			<view class="passport-hero">
				<text class="ph-city">{{ city || 'Pick a city' }}</text>
				<text class="ph-hint">Browse as if you’re there</text>
			</view>
			<map
				class="map-view"
				:provider="provider"
				:latitude="mapLat"
				:longitude="mapLng"
				:scale="11"
				:markers="markers"
				show-location
				@tap="onMapTap"
			/>
			<input
				class="input"
				v-model="city"
				placeholder="Search a city"
				placeholder-class="ph"
				confirm-type="search"
				@confirm="searchCity"
			/>
			<view class="search-row">
				<view class="search-btn" @click="searchCity"><text>Search</text></view>
				<view class="search-btn ghost" @click="useMyLocation"><text>Near me</text></view>
			</view>
			<view class="results" v-if="results.length">
				<view
					class="result"
					v-for="(r, i) in results"
					:key="i"
					@click="pickResult(r)"
				>
					<text class="r-name">{{ r.city || r.name }}</text>
					<text class="r-addr" v-if="r.address && r.address !== r.city">{{ r.address }}</text>
				</view>
			</view>
			<text class="sec">Popular</text>
			<view class="quick">
				<view class="q" v-for="c in cities" :key="c" :class="{ on: city === c }" @click="pickPopular(c)">
					<text>{{ c }}</text>
				</view>
			</view>
			<view class="btn" @click="save"><text>Go there</text></view>
			<view class="link" @click="clear"><text>Back to {{ homeCity || 'my location' }}</text></view>
		</view>
		<VipSheet v-model:show="showVip" reason="need_plus" @purchased="save" />
	</view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { apiProfileUpdate, apiProfileMe } from '@/api/profile.js'
import { apiMapsGeocode } from '@/api/maps.js'
import { getMapProvider, locateWithCity } from '@/utils/maps.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import { trackClick } from '@/utils/analytics.js'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['update:show', 'saved'])
const city = ref('')
const homeCity = ref('')
const showVip = ref(false)
const mapLat = ref(31.2304)
const mapLng = ref(121.4737)
const results = ref([])
const provider = ref(getMapProvider())
const cities = ['Tokyo', 'Seoul', 'New York', 'London', 'Paris', 'Shanghai', 'Los Angeles', 'Berlin']

const markers = computed(() => [{
	id: 1,
	latitude: mapLat.value,
	longitude: mapLng.value,
	width: 24,
	height: 24,
}])

watch(() => props.show, async (v) => {
	if (!v) return
	provider.value = getMapProvider()
	results.value = []
	try {
		const res = await apiProfileMe()
		homeCity.value = (res.results && res.results.city) || ''
		city.value = (res.results && (res.results.passport_city || res.results.city)) || ''
		const lat = res.results && (res.results.passport_lat != null ? res.results.passport_lat : res.results.lat)
		const lng = res.results && (res.results.passport_lng != null ? res.results.passport_lng : res.results.lng)
		if (lat != null && lng != null) {
			mapLat.value = Number(lat)
			mapLng.value = Number(lng)
		} else {
			const cached = uni.getStorageSync('maps_last_coords')
			if (cached && cached.lat != null) {
				mapLat.value = Number(cached.lat)
				mapLng.value = Number(cached.lng)
			}
		}
		if (city.value) {
			searchCity(true)
		}
	} catch (e) {
		uni.showToast({ title: 'Failed to load passport', icon: 'none' })
	}
})

function close() {
	emit('update:show', false)
}

async function searchCity(silent) {
	const q = (city.value || '').trim()
	if (!q) {
		if (!silent) uni.showToast({ title: 'Enter a city', icon: 'none' })
		return
	}
	try {
		const res = await apiMapsGeocode(q)
		const list = (res.results && res.results.results) || []
		results.value = list
		if (list.length) {
			mapLat.value = Number(list[0].lat)
			mapLng.value = Number(list[0].lng)
			if (!city.value) city.value = list[0].city || list[0].name || q
		} else if (!silent) {
			uni.showToast({ title: 'No places found', icon: 'none' })
		}
	} catch (e) {
		if (!silent) uni.showToast({ title: (e && e.message) || 'Search failed', icon: 'none' })
	}
}

function pickResult(r) {
	city.value = r.city || r.name || ''
	mapLat.value = Number(r.lat)
	mapLng.value = Number(r.lng)
	results.value = []
}

async function pickPopular(name) {
	city.value = name
	await searchCity(true)
}

async function useMyLocation() {
	try {
		uni.showLoading({ title: 'Locating...' })
		const pos = await locateWithCity()
		mapLat.value = pos.lat
		mapLng.value = pos.lng
		if (pos.city) city.value = pos.city
		results.value = []
	} catch (e) {
		uni.showToast({ title: 'Location unavailable', icon: 'none' })
	} finally {
		uni.hideLoading()
	}
}

function onMapTap(e) {
	const detail = e && e.detail
	if (!detail) return
	if (detail.latitude != null) mapLat.value = Number(detail.latitude)
	if (detail.longitude != null) mapLng.value = Number(detail.longitude)
}

async function save() {
	trackClick('passport_apply')
	try {
		const payload = {
			passport_city: city.value,
			is_traveling: !!city.value,
			passport_lat: mapLat.value,
			passport_lng: mapLng.value,
		}
		await apiProfileUpdate(payload)
		emit('saved')
		close()
	} catch (e) {
		if (e && (e.message === 'need_plus' || (e.results && e.results.need_vip))) {
			showVip.value = true
		} else {
			uni.showToast({ title: (e && e.message) || 'Passport failed', icon: 'none' })
		}
	}
}

async function clear() {
	try {
		await apiProfileUpdate({ passport_city: '', is_traveling: false })
		emit('saved')
		close()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Reset failed', icon: 'none' })
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
	max-height: 92vh;
	overflow-y: auto;
}
.title { display:block; color:#111; font-size:40rpx; font-weight:800; margin-bottom:8rpx; font-family: 'Playfair Display', 'Times New Roman', serif; }
.sub { display:block; color:#666; font-size:24rpx; margin-bottom:16rpx; }
.passport-hero {
	background: linear-gradient(120deg, #FD267A 0%, #FF6036 100%);
	border-radius: 24rpx; padding: 28rpx; margin-bottom: 20rpx;
}
.ph-city { display:block; color:#fff; font-size:36rpx; font-weight:800; }
.ph-hint { display:block; color:rgba(255,255,255,0.85); font-size:22rpx; margin-top:6rpx; }
.map-view {
	width: 100%; height: 280rpx; border-radius: 20rpx; overflow: hidden;
	margin-bottom: 20rpx;
	border: 1px solid rgba(0,0,0,0.08);
}
.input {
	background:#F3F0F7; color:#111; border-radius:16rpx; padding:24rpx; font-size:28rpx; margin-bottom:12rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.ph { color:#999; }
.search-row { display:flex; flex-direction:row; margin-bottom:12rpx; }
.search-btn {
	flex:1; background: rgba(253,38,122,0.12); border-radius:999rpx; padding:16rpx; text-align:center; margin-right:12rpx;
}
.search-btn.ghost { background:#F3F0F7; margin-right:0; }
.search-btn text { color:#FD267A; font-size:24rpx; font-weight:600; }
.search-btn.ghost text { color:#444; }
.results { margin-bottom:12rpx; max-height: 220rpx; overflow-y: auto; }
.result {
	padding: 16rpx 8rpx; border-bottom: 1px solid rgba(0,0,0,0.06);
}
.r-name { display:block; color:#111; font-size:26rpx; font-weight:600; }
.r-addr { display:block; color:#888; font-size:22rpx; margin-top:4rpx; }
.sec { display:block; color:#666; font-size:22rpx; margin-bottom: 10rpx; }
.quick { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:20rpx; }
.q {
	background:#F3F0F7; border-radius:999rpx; padding:12rpx 22rpx; margin-right:10rpx; margin-bottom:10rpx;
	border: 1px solid rgba(0,0,0,0.04);
}
.q.on { border-color: #FD267A; background: rgba(253,38,122,0.1); }
.q text { color:#222; font-size:22rpx; }
.q.on text { color:#FD267A; font-weight:600; }
.btn { background: linear-gradient(90deg, #FD267A, #FF6036); border-radius:999rpx; padding:24rpx; text-align:center; }
.btn text { color:#fff; font-weight:700; }
.link { text-align:center; margin-top:20rpx; }
.link text { color:#666; }
</style>
