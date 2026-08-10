<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">Safety</text>
		</view>

		<text class="section">Emergency contact</text>
		<input class="input" v-model="contactName" placeholder="Name" placeholder-class="ph" />
		<input class="input" v-model="contactPhone" placeholder="Phone" placeholder-class="ph" />
		<view class="btn ghost" @click="savePref"><text>Save</text></view>

		<text class="section">Share my date</text>
		<input class="input" v-model="venue" placeholder="Venue" placeholder-class="ph" />
		<input class="input" v-model="whenText" placeholder="When" placeholder-class="ph" />
		<input class="input" v-model="note" placeholder="Note" placeholder-class="ph" />
		<view class="btn ghost" @click="shareDate"><text>Create share link</text></view>

		<text class="section">SOS</text>
		<view class="card" @click="sos">
			<text>Call emergency contact / share location</text>
			<text class="val">›</text>
		</view>

		<text class="section">Blocked words</text>
		<input class="input" v-model="newWord" placeholder="Add a word" placeholder-class="ph" @confirm="addWord" />
		<view class="word-row" v-for="(w, i) in blockedWords" :key="i">
			<text>{{ w }}</text>
			<text class="rm" @click="removeWord(i)">Remove</text>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiSafetyPref, apiSafetyPrefUpdate, apiDateShare, apiSos } from '@/api/safety.js'

const contactName = ref('')
const contactPhone = ref('')
const blockedWords = ref([])
const newWord = ref('')
const venue = ref('')
const whenText = ref('')
const note = ref('')

async function load() {
	try {
		const res = await apiSafetyPref()
		const d = res.results || {}
		const c = d.emergency_contact || {}
		contactName.value = c.name || ''
		contactPhone.value = c.phone || ''
		blockedWords.value = d.blocked_words || []
	} catch (e) {
		const c = uni.getStorageSync('safety_emergency_contact') || {}
		contactName.value = c.name || ''
		contactPhone.value = c.phone || ''
		blockedWords.value = uni.getStorageSync('safety_blocked_words') || []
	}
}

async function savePref() {
	const payload = {
		emergency_contact: { name: contactName.value.trim(), phone: contactPhone.value.trim() },
		blocked_words: blockedWords.value,
	}
	try {
		await apiSafetyPrefUpdate(payload)
		uni.showToast({ title: 'Saved', icon: 'none' })
	} catch (e) {
		uni.setStorageSync('safety_emergency_contact', payload.emergency_contact)
		uni.setStorageSync('safety_blocked_words', blockedWords.value)
		uni.showToast({ title: 'Saved locally', icon: 'none' })
	}
}

async function shareDate() {
	try {
		const res = await apiDateShare({
			venue: venue.value,
			place: venue.value,
			when_text: whenText.value,
			note: note.value,
		})
		const text = (res.results && (res.results.share_text || res.results.share_url)) || ''
		if (text) {
			uni.setClipboardData({ data: text })
			uni.showToast({ title: 'Link copied', icon: 'none' })
		}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' })
	}
}

async function sos() {
	try { await apiSos({}) } catch (e) {}
	const phone = contactPhone.value.trim()
	if (phone) {
		uni.makePhoneCall({ phoneNumber: phone, fail: () => {} })
	}
	uni.getLocation({
		type: 'gcj02',
		success: (loc) => {
			const msg = `SOS — my location: ${loc.latitude},${loc.longitude}`
			uni.setClipboardData({ data: msg })
			uni.showToast({ title: 'Location copied', icon: 'none' })
		},
		fail: () => uni.showToast({ title: 'Enable location for SOS', icon: 'none' }),
	})
}

function addWord() {
	const w = newWord.value.trim().toLowerCase()
	if (!w) return
	if (!blockedWords.value.includes(w)) {
		blockedWords.value = [...blockedWords.value, w]
		savePref()
	}
	newWord.value = ''
}

function removeWord(i) {
	blockedWords.value = blockedWords.value.filter((_, idx) => idx !== i)
	savePref()
}

function back() { uni.navigateBack() }
onMounted(load)
</script>

<style scoped>
.page { min-height:100vh; background:var(--bg,#FFFFFF); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; color:var(--text,#111); }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { color:var(--text,#111); font-size:48rpx; width:60rpx; }
.title { display:block; font-size:40rpx; font-weight:700; }
.section {
	display:block; color:var(--muted,#666); font-size:22rpx; letter-spacing:1rpx;
	text-transform:uppercase; margin: 28rpx 8rpx 12rpx;
}
.input {
	background:var(--surface,#F8F8F8); border-radius:16rpx; padding:24rpx; margin-bottom:12rpx;
	color:var(--text,#111);
}
.ph { color:#999; }
.btn.ghost {
	border:2rpx solid var(--border,rgba(0,0,0,.08)); border-radius:999rpx; padding:20rpx;
	text-align:center; margin-bottom:8rpx;
}
.card {
	display:flex; justify-content:space-between; align-items:center;
	background:var(--surface,#F8F8F8); border-radius:16rpx; padding:28rpx 24rpx;
}
.val { color:var(--muted,#666); }
.word-row { display:flex; justify-content:space-between; padding:16rpx 8rpx; }
.rm { color:#FF4458; }
</style>
