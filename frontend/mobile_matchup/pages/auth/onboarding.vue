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
			<text class="title display-font">关于你</text>
			<input class="input" v-model="nickname" placeholder="昵称" placeholder-class="ph" />
			<text class="label">生日</text>
			<picker mode="date" :value="birthday" :end="maxBirthday" @change="onBirthday">
				<view class="input picker">{{ birthday || '选择日期' }}</view>
			</picker>
			<text class="label">我是</text>
			<view class="chips">
				<view class="chip" :class="{ on: gender === 'female' }" @click="gender = 'female'"><text>女生</text></view>
				<view class="chip" :class="{ on: gender === 'male' }" @click="gender = 'male'"><text>男生</text></view>
				<view class="chip" :class="{ on: gender === 'other' }" @click="gender = 'other'"><text>其他</text></view>
			</view>
			<view class="btn" @click="next1"><text>继续</text></view>
		</template>

		<template v-else-if="step === 2">
			<text class="title display-font">添加照片</text>
			<text class="sub">多几张照片，配对成功率更高</text>
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
			<view class="btn" @click="next2"><text>{{ photos.filter(Boolean).length ? '继续' : '暂时跳过' }}</text></view>
		</template>

		<template v-else-if="step === 3">
			<text class="title display-font">写一句自我介绍</text>
			<text class="sub">真诚一点，更容易被选中</text>
			<textarea class="textarea" v-model="bio" maxlength="300" placeholder="我喜欢咖啡、电影，还有认真聊天…" placeholder-class="ph" />
			<text class="count">{{ bio.length }}/300</text>
			<view class="btn" @click="next3"><text>{{ bio.trim() ? '继续' : '暂时跳过' }}</text></view>
		</template>

		<template v-else-if="step === 4">
			<text class="title display-font">个性问答</text>
			<text class="sub">最多添加 3 个，会展示在个人资料</text>
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
					:placeholder="'回答：' + slot.q"
					placeholder-class="ph"
					maxlength="200"
				/>
			</view>
			<view class="btn" @click="next4"><text>{{ hasPrompts ? '继续' : '暂时跳过' }}</text></view>
		</template>

		<template v-else>
			<text class="title display-font">想认识</text>
			<view class="chips">
				<view class="chip" :class="{ on: looking === 'female' }" @click="looking = 'female'"><text>女生</text></view>
				<view class="chip" :class="{ on: looking === 'male' }" @click="looking = 'male'"><text>男生</text></view>
				<view class="chip" :class="{ on: looking === '' }" @click="looking = ''"><text>不限</text></view>
			</view>
			<text class="sub tip">匹配后由女生提问，男生回答，女生审阅通过后才能聊天</text>
			<view class="btn" @click="submit"><text>开始遇见</text></view>
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
	'我的人生目标',
	'让我疯狂的是',
	'我的简单快乐',
	'赢得我的方式是',
	'两个真相和一个谎言',
]

const step = ref(1)
const nickname = ref('')
const birthday = ref('1999-01-01')
const gender = ref('female')
const looking = ref('male')
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
		uni.showToast({ title: '请填写昵称', icon: 'none' })
		return
	}
	if (!birthday.value) {
		uni.showToast({ title: '请选择生日', icon: 'none' })
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
			uni.showLoading({ title: '上传中...' })
			try {
				const body = await uploadFile({ url: '/profile/photos/', filePath: path })
				if (body.results && body.results.url) {
					const next = photos.value.slice()
					next[i] = body.results.url
					photos.value = next
				} else {
					uni.showToast({ title: body.message || '上传失败', icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: (e && e.message) || '上传失败', icon: 'none' })
			} finally {
				uni.hideLoading()
			}
		}
	})
}

async function submit() {
	if (!birthday.value) {
		uni.showToast({ title: '请选择生日', icon: 'none' })
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
		uni.showToast({ title: '须年满 18 岁', icon: 'none' })
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
		if (filledPrompts.length) {
			const pr = await apiProfileUpdate({
				lifestyle: { prompts: filledPrompts, prompt: filledPrompts[0] }
			})
			userInfo = pr.results || userInfo
		}
		uni.setStorageSync('userInfo', userInfo)
		track('onboarding_done')
		uni.switchTab({ url: '/pages/discover/index' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '完善资料失败', icon: 'none' })
	}
}
</script>

<style scoped>
.page {
	min-height: 100vh;
	background: #FFF7FA;
	padding: 100rpx 48rpx 80rpx;
	box-sizing: border-box;
}
.steps { display:flex; flex-direction:row; margin-bottom: 40rpx; }
.dot {
	width: 48rpx; height: 8rpx; border-radius: 999rpx; background: #FFE0EA; margin-right: 12rpx;
}
.dot.on { background: #FF6B9A; }
.title {
	display: block;
	color: #222;
	font-size: 56rpx;
	font-weight: 800;
	margin-bottom: 24rpx;
}
.sub { display:block; color:#888; font-size:26rpx; margin-bottom:32rpx; }
.sub.tip { color:#FF6B9A; margin-top: 8rpx; margin-bottom: 28rpx; }
.display-font { font-family: 'PingFang SC', 'Hiragino Sans GB', sans-serif; }
.label { display:block; color:#666; font-size:24rpx; margin: 8rpx 0 12rpx; }
.input {
	background: #fff;
	border-radius: 20rpx;
	padding: 28rpx;
	color: #222;
	margin-bottom: 20rpx;
	font-size: 28rpx;
	border: 1px solid rgba(255,107,154,0.25);
}
.textarea {
	width: 100%; min-height: 200rpx; box-sizing: border-box;
	background: #fff; border-radius: 20rpx; padding: 28rpx;
	color: #222; font-size: 28rpx; margin-bottom: 8rpx;
	border: 1px solid rgba(255,107,154,0.25);
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
	background: #fff; border: 1px solid rgba(255,107,154,0.2);
}
.chip text { color:#333; font-size:26rpx; }
.chip.on { background: #FF6B9A; border-color: #FF6B9A; }
.chip.on text { color:#fff; font-weight:700; }
.photo-grid {
	display: flex; flex-direction: row; flex-wrap: wrap;
	margin-bottom: 24rpx;
}
.photo-slot {
	position: relative;
	width: 30%; margin-right: 5%; margin-bottom: 16rpx;
	height: 220rpx;
	border-radius: 20rpx; background:#fff;
	border: 1px dashed rgba(255,107,154,0.45); display:flex; align-items:center; justify-content:center;
	overflow:hidden;
}
.photo-slot:nth-child(3n) { margin-right: 0; }
.photo-slot.filled { border-style: solid; border-color: #FF6B9A; }
.photo { width:100%; height:100%; }
.plus { color:#FF6B9A; font-size:48rpx; }
.rm {
	position: absolute; top: 8rpx; right: 8rpx;
	width: 40rpx; height: 40rpx; border-radius: 50%; background: rgba(0,0,0,0.45);
	display:flex; align-items:center; justify-content:center;
}
.rm text { color:#fff; font-size:28rpx; }
.btn {
	margin-top: 20rpx;
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3);
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
}
.btn text { color: #fff; font-weight: 800; }
</style>
