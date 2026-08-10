<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title display-font">编辑资料</text>
		</view>

		<text class="sec">照片</text>
		<view class="photos">
			<view v-for="(p, i) in photos" :key="p.id || i" class="photo">
				<image :src="p.url" mode="aspectFill" class="img" />
				<view class="pending" v-if="p.audit_status === 'pending'"><text>审核中</text></view>
				<view class="del" @click="removePhoto(p)"><text>×</text></view>
				<view class="order" v-if="photos.length > 1">
					<text class="ord" v-if="i > 0" @click="movePhoto(i, -1)">‹</text>
					<text class="ord" v-if="i < photos.length - 1" @click="movePhoto(i, 1)">›</text>
				</view>
			</view>
			<view class="photo add" @click="addPhoto" v-if="photos.length < 6">
				<text>+</text>
			</view>
		</view>
		<view class="row-btns">
			<view class="mini-btn" @click="smartPhotos"><text>智能排序</text></view>
			<view class="mini-btn ghost" @click="goPreview"><text>预览资料</text></view>
		</view>

		<text class="sec">基本信息</text>
		<input class="input" v-model="form.nickname" placeholder="昵称" placeholder-class="ph" />
		<input class="input" v-model="form.job" placeholder="职业" placeholder-class="ph" />
		<input class="input" v-model="form.height_cm" type="number" placeholder="身高 (cm)" placeholder-class="ph" />
		<input class="input" v-model="form.school" placeholder="学校" placeholder-class="ph" />
		<input class="input" v-model="languagesText" placeholder="语言（逗号分隔，如 中文, English）" placeholder-class="ph" />
		<view class="city-row">
			<input class="input city-input" v-model="form.city" placeholder="城市" placeholder-class="ph" />
			<view class="loc-btn" @click="useCurrentLocation"><text>{{ locating ? '…' : '定位' }}</text></view>
		</view>
		<textarea class="area" v-model="form.bio" placeholder="个人简介" placeholder-class="ph" />

		<text class="sec">标签</text>
		<text class="hint">MBTI</text>
		<view class="chips">
			<view v-for="t in mbtiOptions" :key="t" class="chip" :class="{ on: form.mbti === t }" @click="form.mbti = t">
				<text>{{ t }}</text>
			</view>
		</view>
		<text class="hint">星座</text>
		<view class="chips">
			<view v-for="t in zodiacOptions" :key="t" class="chip" :class="{ on: form.zodiac === t }" @click="form.zodiac = t">
				<text>{{ t }}</text>
			</view>
		</view>
		<text class="hint">感情状态</text>
		<view class="chips">
			<view v-for="t in relationshipOptions" :key="t" class="chip" :class="{ on: form.relationship === t }" @click="form.relationship = t">
				<text>{{ t }}</text>
			</view>
		</view>
		<textarea class="area short" v-model="form.looking_for" placeholder="期望遇见什么样的人" placeholder-class="ph" />

		<text class="sec">灵魂问答</text>
		<text class="hint">最多 3 个问题，展示在个人资料页</text>
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
				class="area short"
				v-model="slot.a"
				:placeholder="'回答：' + slot.q"
				placeholder-class="ph"
			/>
		</view>

		<text class="sec">兴趣</text>
		<view class="chips">
			<view
				v-for="t in interestOptions"
				:key="t"
				class="chip"
				:class="{ on: interests.includes(t) }"
				@click="toggleInterest(t)"
			>
				<text>{{ t }}</text>
			</view>
		</view>

		<text class="sec">生活方式</text>
		<text class="hint">饮酒</text>
		<view class="chips">
			<view v-for="t in drinkOptions" :key="t" class="chip" :class="{ on: lifestyle.drinking === t }" @click="lifestyle.drinking = t">
				<text>{{ t }}</text>
			</view>
		</view>
		<text class="hint">吸烟</text>
		<view class="chips">
			<view v-for="t in smokeOptions" :key="t" class="chip" :class="{ on: lifestyle.smoking === t }" @click="lifestyle.smoking = t">
				<text>{{ t }}</text>
			</view>
		</view>
		<text class="hint">运动</text>
		<view class="chips">
			<view v-for="t in exerciseOptions" :key="t" class="chip" :class="{ on: lifestyle.exercise === t }" @click="lifestyle.exercise = t">
				<text>{{ t }}</text>
			</view>
		</view>
		<text class="hint">宠物</text>
		<view class="chips">
			<view v-for="t in petOptions" :key="t" class="chip" :class="{ on: lifestyle.pets === t }" @click="lifestyle.pets = t">
				<text>{{ t }}</text>
			</view>
		</view>

		<text class="sec" id="sec-social">社交账号</text>
		<input class="input" v-model="social.wechat" placeholder="微信" placeholder-class="ph" />
		<input class="input" v-model="social.douyin" placeholder="抖音" placeholder-class="ph" />
		<input class="input" v-model="social.xiaohongshu" placeholder="小红书" placeholder-class="ph" />
		<input class="input" v-model="social.instagram" placeholder="Instagram 用户名" placeholder-class="ph" />
		<input class="input" v-model="social.spotify" placeholder="Spotify 展示名" placeholder-class="ph" />
		<view class="row-btns">
			<view class="mini-btn" @click="connectOAuth('instagram')"><text>连接 Instagram</text></view>
			<view class="mini-btn" @click="connectOAuth('spotify')"><text>连接 Spotify</text></view>
		</view>

		<view class="btn" @click="save"><text>保存</text></view>
	</view>
</template>

<script setup>
import { reactive, ref, onMounted, nextTick } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { uploadFile } from '@/api/upload.js'
import { apiProfileMe, apiProfileUpdate, apiDeletePhoto, apiReorderPhotos, apiSmartPhotos } from '@/api/profile.js'
import { apiOAuthStart } from '@/api/auth.js'
import { locateWithCity } from '@/utils/maps.js'

const interestOptions = [
	'旅行', '艺术', '音乐', '咖啡', '健身', '电影',
	'烹饪', '摄影', '阅读', '游戏', '徒步', '萌宠'
]
const mbtiOptions = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']
const zodiacOptions = ['白羊座', '金牛座', '双子座', '巨蟹座', '狮子座', '处女座', '天秤座', '天蝎座', '射手座', '摩羯座', '水瓶座', '双鱼座']
const relationshipOptions = ['认真恋爱', '轻松社交', '开放关系', '交朋友', '还不确定']
const drinkOptions = ['从不', '社交场合', '经常']
const smokeOptions = ['从不', '社交场合', '经常']
const exerciseOptions = ['从不', '偶尔', '经常']
const petOptions = ['无', '狗', '猫', '其他']
const promptOptions = [
	'我最近的小目标',
	'最让我心动的瞬间',
	'周末我通常会',
	'想和你一起做的事',
	'一个小秘密',
]

const form = reactive({
	nickname: '', job: '', city: '', bio: '', mbti: '', zodiac: '', relationship: '', looking_for: '',
	height_cm: '', school: '',
})
const languagesText = ref('')
const coords = reactive({ lat: null, lng: null })
const locating = ref(false)
const photos = ref([])
const interests = ref([])
const lifestyle = reactive({ drinking: '', smoking: '', exercise: '', pets: '' })
const social = reactive({ wechat: '', douyin: '', xiaohongshu: '', instagram: '', spotify: '' })
const prompts = ref([
	{ q: '', a: '' },
	{ q: '', a: '' },
	{ q: '', a: '' },
])
const focusSocial = ref(false)
let reorderTimer = null

onLoad((q) => {
	focusSocial.value = q && q.focus === 'social'
})

onMounted(async () => {
	try {
		const res = await apiProfileMe()
		const u = res.results || {}
		Object.assign(form, {
			nickname: u.nickname || '',
			job: u.job || '',
			city: u.city || '',
			bio: u.bio || '',
			mbti: u.mbti || '',
			zodiac: u.zodiac || '',
			relationship: u.relationship || '',
			looking_for: u.looking_for || '',
			height_cm: u.height_cm != null ? String(u.height_cm) : '',
			school: u.school || '',
		})
		languagesText.value = Array.isArray(u.languages) ? u.languages.join(', ') : (u.languages || '')
		coords.lat = u.lat != null ? Number(u.lat) : null
		coords.lng = u.lng != null ? Number(u.lng) : null
		photos.value = u.photos || []
		interests.value = [...(u.interests || [])]
		Object.assign(lifestyle, {
			drinking: (u.lifestyle && u.lifestyle.drinking) || '',
			smoking: (u.lifestyle && u.lifestyle.smoking) || '',
			exercise: (u.lifestyle && u.lifestyle.exercise) || '',
			pets: (u.lifestyle && u.lifestyle.pets) || ''
		})
		const prList = (u.lifestyle && u.lifestyle.prompts) || []
		const legacy = (u.lifestyle && u.lifestyle.prompt) || null
		const filled = (prList.length ? prList : (legacy ? [legacy] : [])).slice(0, 3)
		prompts.value = [0, 1, 2].map((i) => ({
			q: (filled[i] && filled[i].q) || '',
			a: (filled[i] && filled[i].a) || '',
		}))
		Object.assign(social, {
			wechat: (u.social_links && u.social_links.wechat) || '',
			douyin: (u.social_links && u.social_links.douyin) || '',
			xiaohongshu: (u.social_links && u.social_links.xiaohongshu) || '',
			instagram: (u.social_links && u.social_links.instagram) || '',
			spotify: (u.social_links && u.social_links.spotify) || '',
		})
		if (focusSocial.value) {
			await nextTick()
			uni.pageScrollTo({ selector: '#sec-social', duration: 280 })
		}
	} catch (e) {
		uni.showToast({ title: '资料加载失败', icon: 'none' })
	}
})

function toggleInterest(t) {
	if (interests.value.includes(t)) {
		interests.value = interests.value.filter((x) => x !== t)
	} else if (interests.value.length < 8) {
		interests.value = [...interests.value, t]
	}
}

async function useCurrentLocation() {
	if (locating.value) return
	locating.value = true
	try {
		const pos = await locateWithCity()
		coords.lat = pos.lat
		coords.lng = pos.lng
		if (pos.city) form.city = pos.city
		uni.showToast({ title: pos.city || '定位已更新', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: '无法获取定位', icon: 'none' })
	} finally {
		locating.value = false
	}
}

function addPhoto() {
	uni.chooseImage({
		count: 1,
		success: async (r) => {
			const path = r.tempFilePaths[0]
			uni.showLoading({ title: 'Uploading...' })
			try {
				const body = await uploadFile({ url: '/profile/photos/', filePath: path })
				photos.value = [...photos.value, body.results]
				uni.showToast({ title: 'Uploaded', icon: 'none' })
			} catch (e) {
				uni.showToast({ title: (e && e.message) || 'upload failed', icon: 'none' })
			} finally {
				uni.hideLoading()
			}
		}
	})
}

async function removePhoto(p) {
	if (!p.id) return
	try {
		await apiDeletePhoto(p.id)
		photos.value = photos.value.filter((x) => x.id !== p.id)
	} catch (e) {
		uni.showToast({ title: 'Delete failed', icon: 'none' })
	}
}

function movePhoto(index, delta) {
	const next = index + delta
	if (next < 0 || next >= photos.value.length) return
	const list = photos.value.slice()
	const tmp = list[index]
	list[index] = list[next]
	list[next] = tmp
	photos.value = list
	if (reorderTimer) clearTimeout(reorderTimer)
	reorderTimer = setTimeout(persistOrder, 280)
}

async function persistOrder() {
	const ids = photos.value.map((p) => p.id).filter(Boolean)
	if (!ids.length) return
	try {
		const res = await apiReorderPhotos(ids)
		if (res.results && res.results.photos) {
			photos.value = res.results.photos
		}
	} catch (e) {
		uni.showToast({ title: 'Reorder failed', icon: 'none' })
	}
}

async function smartPhotos() {
	try {
		const res = await apiSmartPhotos({ apply: true })
		const data = res.results || {}
		if (data.photos && data.photos.length) {
			photos.value = data.photos
		} else if (data.photo_ids && data.photo_ids.length) {
			const map = {}
			photos.value.forEach((p) => { map[p.id] = p })
			photos.value = data.photo_ids.map((id) => map[id]).filter(Boolean)
		}
		uni.showToast({ title: '已按智能建议排序', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '智能排序失败', icon: 'none' })
	}
}

function goPreview() {
	uni.navigateTo({ url: '/pagesA/me/preview' })
}

async function connectOAuth(provider) {
	try {
		const res = await apiOAuthStart(provider)
		const url = (res.results && (res.results.authorize_url || res.results.url)) || ''
		if (!url) {
			uni.showToast({ title: 'OAuth 未配置', icon: 'none' })
			return
		}
		// #ifdef H5
		window.open(url, '_blank')
		// #endif
		// #ifndef H5
		// #ifdef APP-PLUS
		try {
			plus.runtime.openURL(url)
		} catch (e) {
			uni.setClipboardData({ data: url })
			uni.showToast({ title: '授权链接已复制', icon: 'none' })
		}
		// #endif
		// #ifndef APP-PLUS
		uni.setClipboardData({ data: url })
		uni.showToast({ title: '授权链接已复制', icon: 'none' })
		// #endif
		// #endif
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '连接失败', icon: 'none' })
	}
}

async function save() {
	const life = {}
	Object.keys(lifestyle).forEach((k) => {
		if (lifestyle[k]) life[k] = lifestyle[k]
	})
	const filledPrompts = prompts.value
		.filter((p) => p.q && p.a && String(p.a).trim())
		.map((p) => ({ q: p.q, a: String(p.a).trim() }))
	if (filledPrompts.length) {
		life.prompts = filledPrompts
		life.prompt = filledPrompts[0]
	}
	const links = {}
	Object.keys(social).forEach((k) => {
		if (social[k]) links[k] = social[k]
	})
	const langs = languagesText.value
		.split(/[,，]/)
		.map((s) => s.trim())
		.filter(Boolean)
	try {
		const payload = {
			...form,
			height_cm: form.height_cm ? Number(form.height_cm) : null,
			languages: langs,
			interests: interests.value,
			lifestyle: life,
			social_links: links
		}
		if (coords.lat != null && coords.lng != null) {
			payload.lat = coords.lat
			payload.lng = coords.lng
		}
		const res = await apiProfileUpdate(payload)
		uni.setStorageSync('userInfo', res.results || {})
		uni.showToast({ title: '已保存', icon: 'none' })
		uni.navigateBack()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '保存失败', icon: 'none' })
	}
}

function back() {
	uni.navigateBack()
}
</script>

<style scoped>
.page { min-height:100vh; background:#FFFFFF; padding: calc(env(safe-area-inset-top) + 24rpx) 32rpx 80rpx; }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:20rpx; }
.back { color:#111; font-size:48rpx; width:60rpx; }
.title { color:#111; font-size:40rpx; font-weight:700; }
.display-font { font-family: 'Playfair Display', 'Times New Roman', serif; }
.sec {
	display:block; color:#FF4B55; font-size:24rpx; font-weight:600;
	margin: 20rpx 0 12rpx; letter-spacing: 1rpx; text-transform: uppercase;
}
.hint { display:block; color:#666; font-size:22rpx; margin: 4rpx 0 10rpx; }
.prompt-slot { margin-bottom: 16rpx; }
.prompt-pick { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:8rpx; }
.photos { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:8rpx; }
.photo {
	width: 210rpx; height: 280rpx; border-radius: 20rpx; overflow:hidden;
	margin-right: 16rpx; margin-bottom: 16rpx; position:relative; background:#F3F0F7;
	border: 1px solid rgba(253,38,122,0.2);
}
.img { width:100%; height:100%; }
.pending {
	position:absolute; left:8rpx; top:8rpx; background:rgba(255,75,85,0.9);
	border-radius:8rpx; padding:4rpx 10rpx;
}
.pending text { color:#fff; font-size:18rpx; }
.del {
	position:absolute; right:8rpx; top:8rpx; width:40rpx; height:40rpx; border-radius:50%;
	background:rgba(0,0,0,.55); display:flex; align-items:center; justify-content:center;
}
.del text { color:#fff; }
.order {
	position:absolute; left:8rpx; bottom:8rpx;
	display:flex; flex-direction:row;
}
.ord {
	width:44rpx; height:44rpx; border-radius:50%; background:rgba(0,0,0,.55);
	color:#fff; text-align:center; line-height:44rpx; margin-right:8rpx; font-size:28rpx;
}
.add { display:flex; align-items:center; justify-content:center; border:1px dashed rgba(253,38,122,0.4); }
.add text { color:#FD267A; font-size:48rpx; }
.row-btns { display:flex; flex-direction:row; margin-bottom: 16rpx; }
.mini-btn {
	flex:1; text-align:center; padding:18rpx; border-radius:999rpx; margin-right:12rpx;
	background: rgba(255,107,154,0.12); border: 1px solid rgba(255,107,154,0.3);
}
.mini-btn:last-child { margin-right: 0; }
.mini-btn text { color:#FF6B9A; font-size:24rpx; font-weight:600; }
.mini-btn.ghost { background:#fff; }
.input, .area {
	background:#FFF0F5; border-radius:16rpx; padding:24rpx; color:#222; margin-bottom:16rpx; width:100%; box-sizing:border-box;
	border: 1px solid rgba(255,107,154,0.18);
}
.city-row {
	display:flex; flex-direction:row; align-items:center; margin-bottom:16rpx;
}
.city-input { flex:1; margin-bottom:0; margin-right:12rpx; }
.loc-btn {
	flex-shrink:0; padding:24rpx 28rpx; border-radius:16rpx;
	background: rgba(255,107,154,0.12); border: 1px solid rgba(255,107,154,0.25);
}
.loc-btn text { color:#FF6B9A; font-size:24rpx; font-weight:600; }
.area { min-height:180rpx; }
.area.short { min-height:120rpx; }
.ph { color:#999; }
.chips { display:flex; flex-direction:row; flex-wrap:wrap; margin-bottom:8rpx; }
.chip {
	border-radius:999rpx; padding:14rpx 24rpx; margin-right:12rpx; margin-bottom:12rpx;
	background:#F3F0F7; border:1px solid rgba(0,0,0,0.06);
}
.chip text { color:#222; font-size:24rpx; }
.chip.on { background:rgba(253,38,122,0.12); border-color:#FD267A; }
.chip.on text { color:#FD267A; }
.btn { background: linear-gradient(90deg, #FD267A, #FF6036); border-radius:999rpx; padding:26rpx; text-align:center; margin-top:20rpx; }
.btn text { color:#fff; font-weight:600; }
</style>
