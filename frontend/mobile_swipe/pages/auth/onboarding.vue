<template>
	<view class="page">
		<view class="steps">
			<view class="dot" :class="{ on: step >= 1 }" />
			<view class="dot" :class="{ on: step >= 2 }" />
			<view class="dot" :class="{ on: step >= 3 }" />
			<view class="dot" :class="{ on: step >= 4 }" />
			<view class="dot" :class="{ on: step >= 5 }" />
		</view>

		<template v-if="step === 1">
			<text class="title display-font">About you</text>
			<input class="input" v-model="nickname" placeholder="First name" placeholder-class="ph" />
			<text class="label">Birthday</text>
			<picker mode="date" :value="birthday" :end="maxBirthday" @change="onBirthday">
				<view class="input picker">{{ birthday || 'Select date' }}</view>
			</picker>
			<text class="label">I am a</text>
			<view class="chips">
				<view class="chip" :class="{ on: gender === 'female' }" @click="gender = 'female'"><text>Woman</text></view>
				<view class="chip" :class="{ on: gender === 'male' }" @click="gender = 'male'"><text>Man</text></view>
				<view class="chip" :class="{ on: gender === 'other' }" @click="gender = 'other'"><text>Non-binary</text></view>
			</view>
			<template v-if="gender === 'other'">
				<text class="label">Women-first messaging</text>
				<text class="sub">On bee, women (and women-identifying) move first. Choose your role:</text>
				<view class="chips">
					<view class="chip" :class="{ on: womenFirstRole === 'woman' }" @click="womenFirstRole = 'woman'"><text>I move first</text></view>
					<view class="chip" :class="{ on: womenFirstRole === 'man' }" @click="womenFirstRole = 'man'"><text>They move first</text></view>
				</view>
			</template>
			<view class="btn" @click="next1"><text>Continue</text></view>
		</template>

		<template v-else-if="step === 2">
			<text class="title display-font">Add photos</text>
			<text class="sub">Show your best self — add up to 6</text>
			<view class="photo-grid">
				<view
					v-for="(slot, i) in 6"
					:key="i"
					class="photo-slot"
					:class="{ filled: !!photos[i] }"
					@click="pickPhoto(i)"
				>
					<image v-if="photos[i]" :src="photos[i]" class="photo" mode="aspectFill" />
					<text v-else class="plus">+</text>
					<view v-if="photos[i]" class="rm" @click.stop="removePhoto(i)"><text>×</text></view>
				</view>
			</view>
			<view class="btn" @click="next2"><text>{{ photos.filter(Boolean).length ? 'Continue' : 'Skip for now' }}</text></view>
		</template>

		<template v-else-if="step === 3">
			<text class="title display-font">Your bio</text>
			<text class="sub">A few words go a long way</text>
			<textarea class="textarea" v-model="bio" maxlength="300" placeholder="I’m into brunch, beaches, and bad karaoke…" placeholder-class="ph" />
			<text class="count">{{ bio.length }}/300</text>
			<view class="btn" @click="next3"><text>{{ bio.trim() ? 'Continue' : 'Skip for now' }}</text></view>
		</template>

		<template v-else-if="step === 4">
			<text class="title display-font">Prompts</text>
			<text class="sub">Add up to 3 — they show on your profile</text>
			<view v-for="(slot, si) in prompts" :key="si" class="prompt-slot">
				<view class="prompt-pick">
					<view
						v-for="p in promptOptions"
						:key="p + si"
						class="chip"
						:class="{ on: slot.q === p }"
						@click="slot.q = p"
					>
						<text>{{ p }}</text>
					</view>
				</view>
				<textarea
					v-if="slot.q"
					class="textarea short"
					v-model="slot.a"
					:placeholder="'Answer: ' + slot.q"
					placeholder-class="ph"
					maxlength="200"
				/>
			</view>
			<view class="btn" @click="next4"><text>{{ hasPrompts ? 'Continue' : 'Skip for now' }}</text></view>
		</template>

		<template v-else>
			<text class="title display-font">Interested in</text>
			<view class="chips">
				<view class="chip" :class="{ on: looking === 'female' }" @click="looking = 'female'"><text>Women</text></view>
				<view class="chip" :class="{ on: looking === 'male' }" @click="looking = 'male'"><text>Men</text></view>
				<view class="chip" :class="{ on: looking === '' }" @click="looking = ''"><text>Everyone</text></view>
			</view>
			<view class="btn" @click="submit"><text>Start matching</text></view>
		</template>
	</view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { uploadFile } from '@/api/upload.js'
import { apiOnboarding } from '@/api/auth.js'
import { apiProfileUpdate } from '@/api/profile.js'
import { track } from '@/utils/analytics.js'

const promptOptions = [
	'A life goal of mine',
	'I go crazy for',
	'My simple pleasures',
	'The way to win me over is',
	'Two truths and a lie',
]

const step = ref(1)
const nickname = ref('')
const birthday = ref('1999-01-01')
const gender = ref('female')
const womenFirstRole = ref('woman')
const looking = ref('female')
const photos = ref(['', '', '', '', '', ''])
const bio = ref('')
const prompts = ref([
	{ q: '', a: '' },
	{ q: '', a: '' },
	{ q: '', a: '' },
])
const hasPrompts = computed(() =>
	prompts.value.some((p) => p.q && p.a && String(p.a).trim())
)
const maxBirthday = (() => {
	const d = new Date()
	d.setFullYear(d.getFullYear() - 18)
	return d.toISOString().slice(0, 10)
})()

function onBirthday(e) {
	birthday.value = e.detail.value
}

function next1() {
	if (!nickname.value.trim()) {
		uni.showToast({ title: 'Name required', icon: 'none' })
		return
	}
	if (!birthday.value) {
		uni.showToast({ title: 'Birthday required', icon: 'none' })
		return
	}
	step.value = 2
}

function next2() { step.value = 3 }
function next3() { step.value = 4 }
function next4() { step.value = 5 }

function removePhoto(i) {
	const next = photos.value.slice()
	next[i] = ''
	photos.value = next
}

function pickPhoto(i) {
	uni.chooseImage({
		count: 1,
		success: async (r) => {
			const path = r.tempFilePaths[0]
			uni.showLoading({ title: 'Uploading...' })
			try {
				const body = await uploadFile({ url: '/profile/photos/', filePath: path })
				if (body.results && body.results.url) {
					const next = photos.value.slice()
					next[i] = body.results.url
					photos.value = next
				} else {
					uni.showToast({ title: body.message || 'upload failed', icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: (e && e.message) || 'upload failed', icon: 'none' })
			} finally {
				uni.hideLoading()
			}
		}
	})
}

async function submit() {
	if (!birthday.value) {
		uni.showToast({ title: 'Birthday required', icon: 'none' })
		return
	}
	const age = (() => {
		const b = new Date(birthday.value)
		const now = new Date()
		let a = now.getFullYear() - b.getFullYear()
		const m = now.getMonth() - b.getMonth()
		if (m < 0 || (m === 0 && now.getDate() < b.getDate())) a -= 1
		return a
	})()
	if (age < 18) {
		uni.showToast({ title: 'You must be 18+', icon: 'none' })
		return
	}
	const urls = photos.value.filter(Boolean)
	try {
		const res = await apiOnboarding({
			nickname: nickname.value,
			birthday: birthday.value,
			gender: gender.value,
			avatar_url: urls[0] || undefined,
			photo_urls: urls.length ? urls : undefined,
			bio: bio.value.trim() || undefined,
			looking_for_gender: looking.value || undefined
		})
		let userInfo = res.results || {}
		const filledPrompts = prompts.value
			.filter((p) => p.q && p.a && String(p.a).trim())
			.map((p) => ({ q: p.q, a: String(p.a).trim() }))
		const life = {
			dating_mode: 'date',
		}
		if (filledPrompts.length) {
			life.prompts = filledPrompts
			life.prompt = filledPrompts[0]
		}
		if (gender.value === 'other') {
			life.women_first_role = womenFirstRole.value || 'woman'
		}
		const pr = await apiProfileUpdate({ lifestyle: life })
		userInfo = pr.results || userInfo
		uni.setStorageSync('userInfo', userInfo)
		uni.setStorageSync('dating_mode', 'date')
		track('onboarding_done')
		uni.switchTab({ url: '/pages/discover/index' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Could not finish setup', icon: 'none' })
	}
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: #FFFFFF;
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.steps { display:flex; flex-direction:row; margin-bottom: 40rpx; }
.dot {
	width: 48rpx; height: 8rpx; border-radius: 999rpx; background: #F0F0F0; margin-right: 12rpx;
}
.dot.on { background: #FFC629; }
.title {
	display: block;
	color: #111;
	font-size: 56rpx;
	font-weight: 800;
	margin-bottom: 24rpx;
}
.sub { display:block; color:#666; font-size:26rpx; margin-bottom:32rpx; }
.display-font { font-family: 'Montserrat', 'Helvetica Neue', sans-serif; }
.label { display:block; color:#666; font-size:24rpx; margin: 8rpx 0 12rpx; }
.input {
	background: #FFF8E1;
	border-radius: 20rpx;
	padding: 28rpx;
	color: #111;
	margin-bottom: 20rpx;
	font-size: 28rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.textarea {
	width: 100%; min-height: 200rpx; box-sizing: border-box;
	background: #FFF8E1; border-radius: 20rpx; padding: 28rpx;
	color: #111; font-size: 28rpx; margin-bottom: 8rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.textarea.short { min-height: 120rpx; }
.prompt-slot { margin-bottom: 16rpx; }
.prompt-pick { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:8rpx; }
.count { display:block; text-align:right; color:#999; font-size:22rpx; margin-bottom: 24rpx; }
.picker { box-sizing: border-box; }
.ph { color: #999; }
.chips { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom: 24rpx; }
.chip {
	border-radius: 999rpx; padding: 18rpx 32rpx; margin-right: 12rpx; margin-bottom: 12rpx;
	background: #F5F5F5; border: 1px solid transparent;
}
.chip text { color:#333; font-size:26rpx; }
.chip.on { background: #FFC629; border-color: #FFC629; }
.chip.on text { color:#111; font-weight:700; }
.photo-grid {
	display: flex; flex-direction: row; flex-wrap: wrap;
	margin-bottom: 24rpx;
}
.photo-slot {
	position: relative;
	width: 30%; margin-right: 5%; margin-bottom: 16rpx;
	height: 220rpx;
	border-radius: 20rpx; background:#FFF8E1;
	border: 1px dashed rgba(255,198,41,0.7); display:flex; align-items:center; justify-content:center;
	overflow:hidden;
}
.photo-slot:nth-child(3n) { margin-right: 0; }
.photo-slot.filled { border-style: solid; border-color: #FFC629; }
.photo { width:100%; height:100%; }
.plus { color:#B8860B; font-size:48rpx; }
.rm {
	position: absolute; top: 8rpx; right: 8rpx;
	width: 40rpx; height: 40rpx; border-radius: 50%; background: rgba(0,0,0,0.45);
	display:flex; align-items:center; justify-content:center;
}
.rm text { color:#fff; font-size:28rpx; }
.btn {
	margin-top: 20rpx;
	background: #FFC629;
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.btn text { color: #111; font-weight: 800; }
</style>
