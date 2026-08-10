<template>
	<view class="page">
		<view class="nav">
			<text class="back" @click="back">‹</text>
			<view class="peer" @click="openProfile">
				<ExpiryRing
					v-if="showNavRing"
					:progress="navRingProgress"
					:size="76"
					:stroke="4"
				>
					<view class="nav-avatar-inner">
						<image v-if="peer.avatar_url" :src="peer.avatar_url" class="nav-avatar" :class="{ blur: blurPeer }" mode="aspectFill" />
						<view class="online" v-if="peer.is_online && !blurPeer" />
					</view>
				</ExpiryRing>
				<view v-else class="nav-avatar-wrap">
					<image v-if="peer.avatar_url" :src="peer.avatar_url" class="nav-avatar" :class="{ blur: blurPeer }" mode="aspectFill" />
					<view class="online" v-if="peer.is_online && !blurPeer" />
				</view>
				<view>
					<text class="title">{{ peer.nickname || '聊天' }}</text>
					<text class="status">{{ statusText }}</text>
				</view>
			</view>
			<view class="nav-actions">
				<text class="call-btn" @click="startCall">☎</text>
				<text class="more" @click="more">⋯</text>
			</view>
		</view>
		<view class="typing-banner" v-if="peerTyping && !qaPending">
			<text>对方正在输入…</text>
		</view>

		<view class="expired-banner" v-if="showSoftBanner">
			<text>{{ bannerPrimary }}</text>
			<view
				v-if="!qaPending && matchStatus === 'expired' && peer && peer.id && !showExpireRitual"
				class="rematch-btn"
				@click="likeAgain"
			>
				<text>{{ likeAgainLabel }}</text>
			</view>
		</view>

		<!-- 缘分到期仪式 -->
		<view class="expire-ritual" v-if="showExpireRitual">
			<view class="ritual-card">
				<text class="ritual-title">缘分到期</text>
				<text class="ritual-sub">问答时限已过，缘分先告一段落</text>
				<view class="ritual-btn" @click="goDiscoverAfterExpire"><text>再去发现</text></view>
			</view>
		</view>

		<!-- 她说：女问男答再审阅 -->
		<view class="qa-panel" v-if="qaPending && !matchLocked">
			<view class="qa-progress">
				<view class="qa-dot" :class="{ on: qaStepIndex >= 1 }" />
				<view class="qa-line" :class="{ on: qaStepIndex >= 2 }" />
				<view class="qa-dot" :class="{ on: qaStepIndex >= 2 }" />
				<view class="qa-line" :class="{ on: qaStepIndex >= 3 }" />
				<view class="qa-dot" :class="{ on: qaStepIndex >= 3 }" />
			</view>
			<text class="qa-step">{{ qaStepLabel }}</text>
			<text class="qa-hint">{{ qaHint }}</text>
			<template v-if="qa.question">
				<view class="qa-bubble ask">
					<text class="qa-label">她的问题</text>
					<text class="qa-body">{{ qa.question }}</text>
				</view>
			</template>
			<template v-if="qa.answer">
				<view class="qa-bubble ans">
					<text class="qa-label">他的回答</text>
					<text class="qa-body">{{ qa.answer }}</text>
				</view>
			</template>
			<view v-if="qaRetryHint" class="qa-retry">
				<text>{{ qaRetryHint }}</text>
			</view>

			<view v-if="qa.can_ask" class="qa-form">
				<scroll-view scroll-x class="tpl-scroll" v-if="qaTemplates.length">
					<view
						v-for="t in qaTemplates"
						:key="t.id || t.text"
						class="tpl-chip"
						:class="{ on: qaDraft === t.text }"
						@click="pickQaTemplate(t)"
					>
						<text>{{ t.text }}</text>
					</view>
				</scroll-view>
				<textarea
					class="qa-input"
					v-model="qaDraft"
					maxlength="200"
					placeholder="写一个有趣的问题，对方回答后你再决定是否开聊"
					placeholder-class="ph"
				/>
				<view class="qa-submit" @click="submitAsk"><text>发出问题</text></view>
			</view>
			<view v-else-if="qa.can_answer" class="qa-form">
				<textarea
					class="qa-input"
					v-model="qaDraft"
					maxlength="500"
					placeholder="认真回答，过关后才能自由聊天"
					placeholder-class="ph"
				/>
				<view class="qa-submit" @click="submitAnswer"><text>提交回答</text></view>
			</view>
			<view v-else-if="qa.can_review" class="qa-review">
				<view class="qa-approve" @click="submitReview(true)"><text>满意，开始聊天</text></view>
				<view class="qa-reject" @click="submitReview(false, true)"><text>不满意，让他重答</text></view>
				<view class="qa-reject end" @click="submitReview(false, false)"><text>直接结束配对</text></view>
			</view>
			<view v-else class="qa-wait">
				<text>{{ qaWaitText }}</text>
			</view>
		</view>

		<scroll-view scroll-y class="msgs" :scroll-into-view="scrollInto" v-if="!qaPending">
			<view v-if="!messages.length && !effectiveWaiting" class="match-hero">
				<view class="mh-avatars">
					<image v-if="meAvatar" :src="meAvatar" class="mh-av" mode="aspectFill" />
					<view v-else class="mh-av ph" />
					<image v-if="peer.avatar_url" :src="peer.avatar_url" class="mh-av" mode="aspectFill" />
					<view v-else class="mh-av ph" />
				</view>
				<text class="mh-title">你和 {{ peer.nickname || '对方' }} 配对成功</text>
				<text class="mh-sub">先打个招呼吧</text>
			</view>
			<view v-if="!messages.length && !effectiveWaiting" class="starters">
				<text class="starters-title">{{ iAmOpener ? '先打个招呼吧' : '说点好听的' }}</text>
				<view v-for="(s, i) in starters" :key="i" class="starter" @click="quickSend(s)">
					<text>{{ s }}</text>
				</view>
			</view>
			<view v-for="m in messages" :key="m.id" :id="'m'+m.id" class="msg" :class="{ mine: m.sender_id === myId }">
				<image
					v-if="m.msg_type === 'image' || m.msg_type === 'photo' || m.msg_type === 'gif'"
					:src="m.content"
					class="img-bubble"
					mode="widthFix"
					@click="preview(m.content)"
				/>
				<view v-else-if="m.msg_type === 'voice' || m.msg_type === 'audio'" class="voice-bubble" @click="playVoice(m)">
					<text class="voice-ico">{{ playingId === m.id ? '❚❚' : '▶' }}</text>
					<text class="voice-dur">{{ formatVoiceDur(m) }}</text>
				</view>
				<template v-else>
					<text class="bubble">{{ showOriginal[m.id] ? m.content : (m.translated || m.content) }}</text>
					<text
						v-if="m.translated && !showOriginal[m.id]"
						class="tr-btn"
						@click="toggleOriginal(m)"
					>原文</text>
					<text
						v-else-if="m.msg_type === 'text' || !m.msg_type"
						class="tr-btn"
						@click="translate(m)"
					>{{ translating[m.id] ? '…' : '翻译' }}</text>
				</template>
				<text v-if="m.sender_id === myId" class="receipt">{{ receiptMark(m) }}</text>
			</view>
		</scroll-view>

		<view class="composer" v-if="!matchLocked && !effectiveWaiting && !qaPending && canSend">
			<view class="photo-btn" @click="pickMedia"><text>＋</text></view>
			<view class="photo-btn" @click="pickGif"><text>GIF</text></view>
			<view class="photo-btn" :class="{ rec: recording }" @click="toggleRecord">
				<text>{{ recording ? '■' : '🎤' }}</text>
			</view>
			<input
				class="input"
				v-model="text"
				:placeholder="composerHint"
				placeholder-class="ph"
				confirm-type="send"
				@confirm="send"
				@input="onTypingInput"
			/>
			<view class="send" @click="send"><text>发送</text></view>
		</view>
		<view class="composer locked" v-else-if="!qaPending">
			<input class="input" disabled :placeholder="matchLocked ? '暂无法聊天' : '暂无法聊天'" placeholder-class="ph" />
		</view>

		<view class="gif-sheet" v-if="showGif">
			<input
				class="gif-input"
				v-model="gifQuery"
				placeholder="搜索 GIF 或粘贴 URL"
				placeholder-class="ph"
				confirm-type="search"
				@confirm="searchGifs"
			/>
			<view class="gif-actions">
				<view class="gif-btn" @click="searchGifs"><text>搜索</text></view>
				<view class="gif-btn" @click="sendGifUrl"><text>发送 URL</text></view>
				<view class="gif-btn ghost" @click="showGif = false"><text>取消</text></view>
			</view>
			<scroll-view scroll-y class="gif-grid" v-if="gifResults.length">
				<view class="gif-row">
					<image
						v-for="(g, i) in gifResults"
						:key="i"
						:src="g.preview_url || g.url"
						class="gif-thumb"
						mode="aspectFill"
						@click="sendGifItem(g)"
					/>
				</view>
			</scroll-view>
			<text class="gif-empty" v-else-if="gifSearched">{{ gifError || '暂无结果，可粘贴 URL' }}</text>
		</view>

		<VipSheet v-model:show="showVip" reason="need_platinum" @purchased="onPurchased" />
	</view>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { host } from '@/config/config.js'
import { uploadFile } from '@/api/upload.js'
import {
	apiMessages, apiSendMessage, apiTranslate, apiSearchGifs,
} from '@/api/chat.js'
import { apiUnmatch, apiQaAsk, apiQaAnswer, apiQaReview, apiQaTemplates } from '@/api/likes.js'
import { apiBlock, apiReport } from '@/api/profile.js'
import { apiSwipe } from '@/api/recommend.js'
import { WS_HOST } from '@/config/config.js'
import { trackClick } from '@/utils/analytics.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import ExpiryRing from '@/components/ExpiryRing/ExpiryRing.vue'
import {
	formatExpireCountdown, expireProgress, matchOpenHours, isWomenFirst, isQaGate,
} from '@/utils/productProfile.js'

const REPORT_REASONS = [
	{ key: 'spam', label: '垃圾信息' },
	{ key: 'harassment', label: '骚扰' },
	{ key: 'inappropriate', label: '不当内容' },
	{ key: 'fake', label: '虚假资料' },
	{ key: 'underage', label: '未成年' },
	{ key: 'other', label: '其他' },
]

const cid = ref(null)
const matchId = ref(null)
const MSG_DOM_CAP = 200 // F-07: cap DOM messages to last N
const messages = ref([])
const peer = ref({})
const text = ref('')
const sending = ref(false)
const myId = ref((uni.getStorageSync('userInfo') || {}).id)
const scrollInto = ref('')
const showVip = ref(false)
const blurPeer = ref(false)
const isPrematch = ref(false)
const freeRepliesLeft = ref(null)
const matchStatus = ref('active')
const sayHiExpired = ref(false)
const waitingForOpener = ref(false)
const iAmOpener = ref(false)
const messagingMode = ref('any')
const matchExpireAt = ref(null)
const canSend = ref(true)
const qa = ref({})
const qaDraft = ref('')
const qaAskedRetry = ref(false)
const qaTemplates = ref([])
const countdown = ref('')
const nowTick = ref(Date.now())
const showExpireRitual = ref(false)
const expireRitualShown = ref(false)
const focusQa = ref(false)
const recording = ref(false)
const playingId = ref(null)
let countdownTimer = null
let recordStartedAt = 0
let recorder = null
let innerAudio = null
const translating = reactive({})
const showOriginal = reactive({})
const peerTyping = ref(false)
const showGif = ref(false)
const gifQuery = ref('')
const gifResults = ref([])
const gifSearched = ref(false)
const gifError = ref('')
const starters = [
	'你好呀，看了你的照片觉得很有感觉～',
	'周末有空一起喝咖啡吗？',
	'最近在忙什么呢？'
]
let socketTask = null
let qaSocketTask = null
let qaPollTimer = null
let typingTimer = null
let typingStopTimer = null
let peerTypingTimer = null
let h5MediaRecorder = null
let h5Chunks = []
let h5Stream = null

const qaPending = computed(() => {
	if (messagingMode.value !== 'qa_gate') return false
	const st = (qa.value && qa.value.status) || ''
	return !!st && st !== 'approved' && st !== 'expired' && matchStatus.value === 'active'
})

const matchLocked = computed(() => (
	matchStatus.value === 'ended'
	|| matchStatus.value === 'expired'
	|| sayHiExpired.value
	|| (qa.value && (qa.value.status === 'rejected' || qa.value.status === 'expired'))
))

/** Soft-hide women_first waiting when in qa_gate */
const effectiveWaiting = computed(() => {
	if (messagingMode.value === 'qa_gate') return false
	return waitingForOpener.value
})

const showOpenTimer = computed(() => (
	!matchLocked.value
	&& messagingMode.value === 'qa_gate'
	&& qaPending.value
	&& !!matchExpireAt.value
))

const showSoftBanner = computed(() => {
	if (showExpireRitual.value) return false
	if (qaPending.value || showOpenTimer.value) return true
	if (matchLocked.value && !showExpireRitual.value) return true
	if (effectiveWaiting.value) return true
	return false
})

const showNavRing = computed(() => {
	if (!matchExpireAt.value) return false
	if (matchLocked.value && !qaPending.value) return false
	return qaPending.value || showOpenTimer.value
})

const navRingProgress = computed(() => {
	if (!showNavRing.value) return 0
	return expireProgress(matchExpireAt.value, nowTick.value, matchOpenHours() || 48)
})

const waitingBannerText = computed(() => {
	const left = countdown.value
	return left ? `等待开聊 · 剩余 ${left}` : '等待开聊…'
})

const openerTimerText = computed(() => {
	const left = countdown.value
	return left ? `请先开口 · 剩余 ${left}` : '请先开口打招呼'
})

const qaStepLabel = computed(() => {
	const st = (qa.value && qa.value.status) || ''
	if (st === 'need_question') return '第一步 · 她提问'
	if (st === 'need_answer') return '第二步 · 他回答'
	if (st === 'need_review') return '第三步 · 她审阅'
	if (st === 'expired') return '缘分到期'
	return '问答开聊'
})

const qaStepIndex = computed(() => {
	const st = (qa.value && qa.value.status) || ''
	if (st === 'need_question') return 1
	if (st === 'need_answer') return 2
	if (st === 'need_review') return 3
	return 0
})

const meAvatar = computed(() => {
	const me = uni.getStorageSync('userInfo') || {}
	if (me.avatar_url) return me.avatar_url
	if (me.photos && me.photos.length) return me.photos[0].url
	return ''
})

const qaHint = computed(() => {
	const left = countdown.value
	const base = left ? `剩余 ${left}` : ''
	if (qa.value.can_ask) return `请出题，对方回答后你再决定是否聊天${base ? ' · ' + base : ''}`
	if (qa.value.can_answer) return `请回答她的问题${base ? ' · ' + base : ''}`
	if (qa.value.can_review) return `审阅回答，满意才开聊${base ? ' · ' + base : ''}`
	return base || '问答进行中'
})

const qaWaitText = computed(() => {
	const st = (qa.value && qa.value.status) || ''
	if (st === 'need_question') return '等待她出题…'
	if (st === 'need_answer') return qaAskedRetry.value ? '已请他重答，等待回复…' : '等待他回答…'
	if (st === 'need_review') return '等待她审阅…'
	return '请稍候…'
})

const qaRetryHint = computed(() => {
	if (!qaPending.value) return ''
	const st = (qa.value && qa.value.status) || ''
	if (st === 'need_answer' && qa.value.can_answer && qaAskedRetry.value) {
		return '她希望你重新回答，请认真写一版'
	}
	if (st === 'need_answer' && !qa.value.can_answer && qaAskedRetry.value) {
		return '已要求重答'
	}
	return ''
})

const bannerPrimary = computed(() => {
	if (matchLocked.value) return lockedBannerText.value
	if (qaPending.value) return qaHint.value
	if (effectiveWaiting.value) return waitingBannerText.value
	if (showOpenTimer.value) return qaHint.value
	return ''
})

const lockedBannerText = computed(() => {
	if (sayHiExpired.value) return '打招呼已过期'
	if (qa.value && qa.value.status === 'rejected') return '对方未通过问答'
	if (qa.value && qa.value.status === 'expired') return '缘分已到期'
	if (matchStatus.value === 'expired') return '匹配已过期'
	return '匹配已结束'
})

const likeAgainLabel = computed(() => '再次喜欢')

const statusText = computed(() => {
	if (qaPending.value) return qaStepLabel.value
	if (effectiveWaiting.value) return waitingBannerText.value
	if (sayHiExpired.value) return '打招呼已过期'
	if (matchStatus.value === 'expired' || (qa.value && qa.value.status === 'expired')) return '缘分到期'
	if (matchStatus.value === 'ended') return '已取消匹配'
	if (isPrematch.value && blurPeer.value) {
		if (freeRepliesLeft.value === null) return '打招呼'
		return `免费回复剩余：${freeRepliesLeft.value}`
	}
	if (isPrematch.value) return '打招呼 · 尚未配对'
	return peer.value.is_online ? '在线' : '最近活跃'
})

const composerHint = computed(() => {
	if (matchLocked.value) return '暂无法聊天'
	if (qaPending.value) return '完成问答后才能聊天'
	if (effectiveWaiting.value) return waitingBannerText.value
	if (blurPeer.value && freeRepliesLeft.value === 0) return '升级会员继续聊'
	return '发消息'
})

function triggerExpireRitual() {
	if (expireRitualShown.value) return
	expireRitualShown.value = true
	showExpireRitual.value = true
}

function applyMessaging(data) {
	const prevSt = (qa.value && qa.value.status) || ''
	waitingForOpener.value = !!data.waiting_for_opener
	iAmOpener.value = !!data.i_am_opener
	messagingMode.value = data.messaging_mode || (isQaGate() ? 'qa_gate' : (isWomenFirst() ? 'women_first' : 'any'))
	matchExpireAt.value = data.expire_at || data.match_expire_at || null
	canSend.value = data.can_send !== false
	qa.value = data.qa || {}
	const nextSt = (qa.value && qa.value.status) || ''
	if (prevSt === 'need_review' && nextSt === 'need_answer') {
		qaAskedRetry.value = true
	}
	if (nextSt === 'approved' || nextSt === 'rejected') {
		qaAskedRetry.value = false
	}
	if (nextSt === 'expired') {
		matchStatus.value = 'expired'
		triggerExpireRitual()
	}
	if (messagingMode.value === 'qa_gate') {
		connectQaWs()
		if (qa.value.can_ask) loadQaTemplates()
	}
}

function tickCountdown() {
	nowTick.value = Date.now()
	countdown.value = formatExpireCountdown(matchExpireAt.value, nowTick.value)
	if (matchExpireAt.value && new Date(matchExpireAt.value).getTime() <= Date.now()) {
		const st = (qa.value && qa.value.status) || ''
		if (messagingMode.value === 'qa_gate' && st && st !== 'approved') {
			qa.value = { ...qa.value, status: 'expired' }
			matchStatus.value = 'expired'
			triggerExpireRitual()
		} else if (messagingMode.value === 'women_first' && !messages.value.length) {
			matchStatus.value = 'expired'
		}
	}
}

watch(() => matchStatus.value, (v) => {
	if (v === 'expired') triggerExpireRitual()
})

watch(() => qa.value && qa.value.status, (st) => {
	if (st === 'expired') triggerExpireRitual()
})

onLoad((q) => {
	cid.value = q.id
	focusQa.value = q.focus === 'qa'
})

onMounted(async () => {
	const draft = uni.getStorageSync('match_draft_message')
	if (draft) {
		text.value = String(draft)
		uni.removeStorageSync('match_draft_message')
	}
	const qaD = uni.getStorageSync('match_qa_draft')
	if (qaD) {
		qaDraft.value = String(qaD)
		uni.removeStorageSync('match_qa_draft')
	}
	await load()
	connectWs()
	connectQaWs()
	countdownTimer = setInterval(tickCountdown, 1000)
})

onUnmounted(() => {
	if (countdownTimer) clearInterval(countdownTimer)
	countdownTimer = null
	if (qaPollTimer) clearInterval(qaPollTimer)
	qaPollTimer = null
	if (typingTimer) clearTimeout(typingTimer)
	if (typingStopTimer) clearTimeout(typingStopTimer)
	if (peerTypingTimer) clearTimeout(peerTypingTimer)
	try {
		if (socketTask && socketTask.close) socketTask.close()
	} catch (e) {}
	try {
		if (qaSocketTask && qaSocketTask.close) qaSocketTask.close()
	} catch (e) {}
	try {
		if (innerAudio) { innerAudio.stop(); innerAudio.destroy && innerAudio.destroy() }
	} catch (e) {}
	try {
		if (h5Stream) h5Stream.getTracks().forEach((t) => t.stop())
	} catch (e) {}
})

async function loadQaTemplates() {
	try {
		const res = await apiQaTemplates({ locale: 'zh' })
		const list = (res.results && (res.results.list || res.results.templates)) || res.results || []
		qaTemplates.value = Array.isArray(list) ? list : []
	} catch (e) {
		qaTemplates.value = []
	}
}

function pickQaTemplate(t) {
	if (t && t.text) qaDraft.value = t.text
}

async function load() {
	try {
		const res = await apiMessages(cid.value)
		const data = res.results || {}
		messages.value = capMessages(data.list || [])
		peer.value = data.peer || {}
		matchId.value = data.match_id || null
		isPrematch.value = !!data.is_prematch
		blurPeer.value = !!data.blur_peer
		freeRepliesLeft.value = data.free_replies_left
		matchStatus.value = data.match_status || 'active'
		sayHiExpired.value = !!data.say_hi_expired
		applyMessaging(data)
		if (sayHiExpired.value) matchStatus.value = 'expired'
		if (data.match_status === 'expired' || (data.qa && data.qa.status === 'expired')) {
			triggerExpireRitual()
		}
		if (messages.value.length && !qaPending.value) {
			waitingForOpener.value = false
			matchExpireAt.value = null
			scrollInto.value = 'm' + messages.value[messages.value.length - 1].id
		}
		tickCountdown()
		connectQaWs()
	} catch (e) {
		uni.showToast({ title: '加载聊天失败', icon: 'none' })
	}
}

function goDiscoverAfterExpire() {
	showExpireRitual.value = false
	uni.switchTab({ url: '/pages/discover/index' })
}

async function submitAsk() {
	const q = (qaDraft.value || '').trim()
	if (!q || !matchId.value) return
	try {
		const res = await apiQaAsk(matchId.value, q)
		applyMessaging(res.results || {})
		qaDraft.value = ''
		uni.showToast({ title: '已出题', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '出题失败', icon: 'none' })
	}
}

async function submitAnswer() {
	const a = (qaDraft.value || '').trim()
	if (!a || !matchId.value) return
	try {
		const res = await apiQaAnswer(matchId.value, a)
		applyMessaging(res.results || {})
		qaDraft.value = ''
		uni.showToast({ title: '已提交', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '提交失败', icon: 'none' })
	}
}

async function submitReview(approve, allowRetry = true) {
	if (!matchId.value) return
	try {
		const res = await apiQaReview(matchId.value, approve, allowRetry)
		applyMessaging(res.results || {})
		if (approve) {
			qaAskedRetry.value = false
			canSend.value = true
			uni.showToast({ title: '可以聊天了', icon: 'none' })
		} else if (allowRetry) {
			qaAskedRetry.value = true
			uni.showToast({ title: '已请他重新回答', icon: 'none' })
		} else {
			matchStatus.value = 'ended'
			uni.showToast({ title: '已结束配对', icon: 'none' })
		}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
	}
}

function connectWs() {
	try {
		const token = uni.getStorageSync('token') || ''
		socketTask = uni.connectSocket({
			url: `${WS_HOST}/ws/chat/${cid.value}/?token=${encodeURIComponent(token)}`,
			complete() {}
		})
		if (socketTask && typeof socketTask.onMessage === 'function') {
			socketTask.onMessage((evt) => {
				try {
					const payload = JSON.parse(evt.data)
					if (payload.type === 'message' && payload.data) {
						appendMsg(payload.data)
						markDelivered(payload.data)
					} else if (payload.type === 'typing') {
						const from = payload.from_user_id || (payload.data && payload.data.from_user_id)
						const typing = payload.is_typing != null
							? payload.is_typing
							: (payload.data && payload.data.is_typing)
						if (from && from !== myId.value) {
							peerTyping.value = !!typing
							if (peerTypingTimer) clearTimeout(peerTypingTimer)
							if (typing) {
								peerTypingTimer = setTimeout(() => { peerTyping.value = false }, 3000)
							}
						}
					} else if (payload.type === 'read' || payload.type === 'delivered') {
						const mid = payload.message_id || (payload.data && payload.data.message_id)
						const list = messages.value.slice()
						const idx = list.findIndex((m) => m.id === mid)
						if (idx >= 0) {
							if (payload.type === 'read' || (payload.data && payload.data.read_at)) {
								list[idx] = {
									...list[idx],
									read_at: (payload.data && payload.data.read_at) || new Date().toISOString(),
									is_read: true,
								}
							} else {
								list[idx] = {
									...list[idx],
									delivered_at: (payload.data && payload.data.delivered_at) || new Date().toISOString(),
								}
							}
							messages.value = list
						}
					} else if (payload.type === 'call_invite') {
						uni.showToast({ title: '对方发起了视频通话', icon: 'none' })
					} else if (payload.type === 'call_hangup') {
						uni.showToast({ title: '对方已挂断', icon: 'none' })
					}
				} catch (e) {}
			})
		}
		if (socketTask && typeof socketTask.onOpen === 'function') {
			socketTask.onOpen(() => {
				messages.value.forEach((m) => {
					if (m.sender_id !== myId.value) markDelivered(m)
				})
			})
		}
		if (socketTask && typeof socketTask.onClose === 'function') {
			socketTask.onClose(() => { socketTask = null })
		}
	} catch (e) {}
}

function wsSend(obj) {
	try {
		if (socketTask && typeof socketTask.send === 'function') {
			socketTask.send({ data: JSON.stringify(obj) })
		}
	} catch (e) {}
}

function markDelivered(msg) {
	if (!msg || msg.sender_id === myId.value) return
	wsSend({ type: 'delivered', message_id: msg.id })
	wsSend({ type: 'read', message_id: msg.id })
}

function onTypingInput() {
	if (typingTimer) return
	wsSend({ type: 'typing', is_typing: true })
	typingTimer = setTimeout(() => { typingTimer = null }, 1200)
	if (typingStopTimer) clearTimeout(typingStopTimer)
	typingStopTimer = setTimeout(() => {
		wsSend({ type: 'typing', is_typing: false })
	}, 2000)
}

function receiptMark(m) {
	if (!m) return ''
	if (m.read_at || m.is_read) return '✓✓'
	if (m.delivered_at) return '✓✓'
	return '✓'
}

function startCall() {
	if (!cid.value) return
	trackClick('start_call')
	uni.navigateTo({ url: `/pagesA/chat/call?cid=${cid.value}` })
}

function pickGif() {
	showGif.value = true
	gifQuery.value = ''
	gifResults.value = []
	gifSearched.value = false
	gifError.value = ''
}

async function searchGifs() {
	const q = (gifQuery.value || '').trim()
	if (!q) {
		uni.showToast({ title: '输入关键词或粘贴 URL', icon: 'none' })
		return
	}
	if (/^https?:\/\//i.test(q)) {
		await sendGifUrl()
		return
	}
	gifSearched.value = true
	gifError.value = ''
	try {
		const res = await apiSearchGifs(q)
		gifResults.value = (res.results && res.results.list) || []
		if (!gifResults.value.length) gifError.value = '暂无结果'
	} catch (e) {
		gifResults.value = []
		gifError.value = (e && e.message) || 'GIF 搜索不可用'
		uni.showToast({ title: gifError.value, icon: 'none' })
	}
}

async function sendGifUrl() {
	const url = (gifQuery.value || '').trim()
	if (!url) {
		uni.showToast({ title: '请粘贴 GIF 链接', icon: 'none' })
		return
	}
	try {
		const res = await apiSendMessage(cid.value, { content: url, msg_type: 'gif' })
		appendMsg(res.results)
		showGif.value = false
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '发送失败', icon: 'none' })
	}
}

async function sendGifItem(g) {
	const url = (g && (g.url || g.preview_url)) || ''
	if (!url) return
	try {
		const res = await apiSendMessage(cid.value, { content: url, msg_type: 'gif' })
		appendMsg(res.results)
		showGif.value = false
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '发送失败', icon: 'none' })
	}
}

function connectQaWs() {
	if (!matchId.value || messagingMode.value !== 'qa_gate') {
		stopQaPoll()
		return
	}
	if (qaSocketTask) return
	try {
		const token = uni.getStorageSync('token') || ''
		qaSocketTask = uni.connectSocket({
			url: `${WS_HOST}/ws/match/${matchId.value}/qa/?token=${encodeURIComponent(token)}`,
			complete() {}
		})
		if (qaSocketTask && typeof qaSocketTask.onMessage === 'function') {
			qaSocketTask.onMessage((evt) => {
				try {
					const payload = JSON.parse(evt.data)
					if (payload.type === 'qa' && payload.data) {
						applyMessaging(payload.data)
						stopQaPoll()
					}
				} catch (e) {}
			})
		}
		if (qaSocketTask && typeof qaSocketTask.onOpen === 'function') {
			qaSocketTask.onOpen(() => { stopQaPoll() })
		}
		if (qaSocketTask && typeof qaSocketTask.onClose === 'function') {
			qaSocketTask.onClose(() => {
				qaSocketTask = null
				if (qaPending.value) startQaPoll()
			})
		}
		if (qaSocketTask && typeof qaSocketTask.onError === 'function') {
			qaSocketTask.onError(() => {
				qaSocketTask = null
				if (qaPending.value) startQaPoll()
			})
		}
	} catch (e) {
		if (qaPending.value) startQaPoll()
	}
}

function startQaPoll() {
	if (qaPollTimer || !qaPending.value) return
	qaPollTimer = setInterval(async () => {
		if (!qaPending.value || !cid.value) {
			stopQaPoll()
			return
		}
		try {
			const res = await apiMessages(cid.value)
			applyMessaging(res.results || {})
			if (!qaPending.value) stopQaPoll()
		} catch (e) {}
	}, 12000)
}

function stopQaPoll() {
	if (qaPollTimer) clearInterval(qaPollTimer)
	qaPollTimer = null
}

function onPurchased() {
	showVip.value = false
	load()
}

function capMessages(list) {
	const arr = Array.isArray(list) ? list : []
	return arr.length > MSG_DOM_CAP ? arr.slice(-MSG_DOM_CAP) : arr
}

function appendMsg(msg) {
	if (msg && !messages.value.find((m) => m.id === msg.id)) {
		messages.value = capMessages([...messages.value, msg])
		scrollInto.value = 'm' + msg.id
	}
}

async function send() {
	if (!text.value.trim() || sending.value) return
	trackClick('send_message')
	if (matchLocked.value || effectiveWaiting.value || qaPending.value) {
		uni.showToast({
			title: qaPending.value ? '请先完成问答' : (effectiveWaiting.value ? waitingBannerText.value : '暂无法聊天'),
			icon: 'none',
		})
		return
	}
	if (blurPeer.value && freeRepliesLeft.value === 0) {
		showVip.value = true
		return
	}
	const content = text.value
	text.value = ''
	sending.value = true
	try {
		const res = await apiSendMessage(cid.value, { content, msg_type: 'text' })
		appendMsg(res.results)
		waitingForOpener.value = false
		if (typeof freeRepliesLeft.value === 'number' && freeRepliesLeft.value > 0) {
			freeRepliesLeft.value -= 1
		}
	} catch (e) {
		text.value = content
		if (e && e.message === 'waiting_for_opener') {
			waitingForOpener.value = true
			uni.showToast({ title: waitingBannerText.value, icon: 'none' })
			return
		}
		if (e && e.message === 'qa_gate_pending') {
			if (e.results) applyMessaging(e.results)
			uni.showToast({ title: '请先完成问答', icon: 'none' })
			return
		}
		if (e && e.message === 'say_hi_expired') {
			sayHiExpired.value = true
			matchStatus.value = 'expired'
			uni.showToast({ title: '打招呼已过期', icon: 'none' })
			return
		}
		if (e && (e.message === 'match_ended' || e.message === 'match_expired')) {
			matchStatus.value = e.message === 'match_expired' ? 'expired' : 'ended'
			uni.showToast({ title: e.message === 'match_expired' ? '匹配已过期' : '匹配已结束', icon: 'none' })
			return
		}
		if (e && e.message === 'content_blocked') {
			uni.showToast({ title: '消息含敏感词', icon: 'none' })
			return
		}
		if (e && (e.message === 'need_platinum' || (e.results && e.results.need_vip))) {
			showVip.value = true
		}
	} finally {
		sending.value = false
	}
}

function quickSend(s) {
	text.value = s
	send()
}

async function translate(m) {
	if (!m || !m.content) return
	translating[m.id] = true
	try {
		const res = await apiTranslate({
			text: m.content,
			target: uni.getStorageSync('currentLanguage') || 'zh',
			message_id: m.id,
		})
		const data = (res && res.results) || {}
		m.translated = data.translated || ''
		showOriginal[m.id] = false
		if (data.mock) {
			uni.showToast({ title: '翻译未配置（mock）', icon: 'none' })
		}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '翻译失败', icon: 'none' })
	}
	translating[m.id] = false
}

function toggleOriginal(m) {
	showOriginal[m.id] = !showOriginal[m.id]
}

function pickMedia() {
	uni.showActionSheet({
		itemList: ['发送图片', '发送动图/GIF', '发送语音'],
		success: (r) => {
			if (r.tapIndex === 2) {
				toggleRecord()
				return
			}
			const asGif = r.tapIndex === 1
			uni.chooseImage({
				count: 1,
				success: (res) => uploadAndSendImage(res.tempFilePaths[0], asGif ? 'gif' : 'image'),
			})
		},
	})
}

function formatVoiceDur(m) {
	const ms = Number(m.duration_ms || m.duration || 0)
	if (!ms) return '语音'
	const s = Math.max(1, Math.round(ms / 1000))
	return `${s}"`
}

function ensureRecorder() {
	if (recorder) return recorder
	try {
		recorder = uni.getRecorderManager()
		recorder.onStop((res) => {
			recording.value = false
			const path = res && res.tempFilePath
			const duration = (res && res.duration) || Math.max(0, Date.now() - recordStartedAt)
			if (path) uploadVoice(path, duration)
		})
		recorder.onError(() => {
			recording.value = false
			uni.showToast({ title: '录音失败', icon: 'none' })
		})
	} catch (e) {
		recorder = null
	}
	return recorder
}

function toggleRecord() {
	// #ifdef H5
	if (typeof MediaRecorder !== 'undefined' && navigator.mediaDevices) {
		toggleH5Record()
		return
	}
	// #endif
	const r = ensureRecorder()
	if (!r) {
		uni.showToast({ title: '当前平台不支持录音', icon: 'none' })
		return
	}
	if (recording.value) {
		r.stop()
		return
	}
	recording.value = true
	recordStartedAt = Date.now()
	r.start({ format: 'mp3', duration: 60000 })
	uni.showToast({ title: '正在录音…再点结束', icon: 'none' })
}

async function toggleH5Record() {
	if (recording.value && h5MediaRecorder) {
		try { h5MediaRecorder.stop() } catch (e) {}
		return
	}
	try {
		h5Stream = await navigator.mediaDevices.getUserMedia({ audio: true })
		h5Chunks = []
		h5MediaRecorder = new MediaRecorder(h5Stream)
		h5MediaRecorder.ondataavailable = (e) => {
			if (e.data && e.data.size) h5Chunks.push(e.data)
		}
		h5MediaRecorder.onstop = async () => {
			recording.value = false
			const blob = new Blob(h5Chunks, { type: 'audio/webm' })
			const durationMs = Math.max(0, Date.now() - recordStartedAt)
			try {
				if (h5Stream) h5Stream.getTracks().forEach((t) => t.stop())
			} catch (e) {}
			h5Stream = null
			h5MediaRecorder = null
			const file = new File([blob], `voice_${Date.now()}.webm`, { type: 'audio/webm' })
			await uploadVoiceBlob(file, durationMs)
		}
		recordStartedAt = Date.now()
		recording.value = true
		h5MediaRecorder.start()
		uni.showToast({ title: '正在录音…再点结束', icon: 'none' })
	} catch (e) {
		recording.value = false
		uni.showToast({ title: '无法访问麦克风', icon: 'none' })
	}
}

function uploadVoiceBlob(file, durationMs) {
	return new Promise((resolve) => {
		uni.showLoading({ title: '发送中…' })
		const form = new FormData()
		form.append('file', file)
		form.append('kind', 'voice')
		form.append('duration_ms', String(durationMs))
		const token = uni.getStorageSync('token') || ''
		fetch(host + '/chat/upload/?kind=voice', {
			method: 'POST',
			headers: {
				token,
				'is-dev': 'true',
				'Accept-Language': uni.getStorageSync('currentLanguage') || 'zh',
			},
			body: form,
		}).then(async (resp) => {
			const body = await resp.json()
			const url = body.results && body.results.url
			if (!url) {
				uni.showToast({ title: '上传失败', icon: 'none' })
				return
			}
			const res = await apiSendMessage(cid.value, {
				content: url,
				msg_type: 'voice',
				duration_ms: durationMs,
			})
			appendMsg(res.results)
		}).catch(() => {
			uni.showToast({ title: '网络错误', icon: 'none' })
		}).finally(() => {
			uni.hideLoading()
			resolve()
		})
	})
}

function uploadVoice(path, durationMs) {
	uni.showLoading({ title: '发送中…' })
	uploadFile({
		url: '/chat/upload/?kind=voice',
		filePath: path,
		formData: { kind: 'voice' },
	}).then(async (body) => {
		const url = body.results && body.results.url
		if (!url) {
			uni.showToast({ title: '上传失败', icon: 'none' })
			return
		}
		const res = await apiSendMessage(cid.value, {
			content: url,
			msg_type: 'voice',
			duration_ms: durationMs,
		})
		appendMsg(res.results)
	}).catch(() => {
		uni.showToast({ title: '网络错误', icon: 'none' })
	}).finally(() => uni.hideLoading())
}

function playVoice(m) {
	if (!m || !m.content) return
	try {
		if (!innerAudio) {
			innerAudio = uni.createInnerAudioContext()
			innerAudio.onEnded(() => { playingId.value = null })
			innerAudio.onStop(() => { playingId.value = null })
		}
		if (playingId.value === m.id) {
			innerAudio.stop()
			playingId.value = null
			return
		}
		innerAudio.src = m.content
		innerAudio.play()
		playingId.value = m.id
	} catch (e) {
		uni.showToast({ title: '播放失败', icon: 'none' })
	}
}

function pickPhoto() {
	uni.chooseImage({
		count: 1,
		success: (r) => uploadAndSendImage(r.tempFilePaths[0], 'image'),
	})
}

function uploadAndSendImage(path, msgType = 'image') {
	uni.showLoading({ title: '发送中...' })
	uploadFile({ url: '/chat/upload/', filePath: path })
		.then(async (body) => {
			const url = body.results && body.results.url
			if (!url) {
				uni.showToast({ title: '上传失败', icon: 'none' })
				return
			}
			const res = await apiSendMessage(cid.value, { content: url, msg_type: msgType })
			appendMsg(res.results)
		})
		.catch(() => uni.showToast({ title: '网络错误', icon: 'none' }))
		.finally(() => uni.hideLoading())
}

function preview(url) {
	uni.previewImage({ urls: [url], current: url })
}

function openProfile() {
	if (blurPeer.value) {
		showVip.value = true
		return
	}
	if (peer.value && peer.value.id) {
		uni.navigateTo({ url: `/pagesA/profile/detail?user_id=${peer.value.id}` })
	}
}

async function likeAgain() {
	if (!peer.value || !peer.value.id) return
	try {
		await apiSwipe({ target_id: peer.value.id, action: 'like' })
		uni.showToast({ title: '已再次喜欢', icon: 'none' })
		uni.switchTab({ url: '/pages/discover/index' })
	} catch (e) {
		if (e && (e.message === 'daily_like_limit' || (e.results && e.results.need_vip))) {
			showVip.value = true
		} else {
			uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
		}
	}
}

function back() {
	uni.navigateBack()
}

function more() {
	uni.showActionSheet({
		itemList: ['取消匹配', '拉黑', '举报'],
		success: async (r) => {
			try {
				if (r.tapIndex === 0) {
					if (!matchId.value) {
						uni.showToast({ title: '无匹配', icon: 'none' })
						return
					}
					await apiUnmatch(matchId.value)
					uni.showToast({ title: '已取消匹配', icon: 'none' })
					setTimeout(() => uni.navigateBack(), 400)
				} else if (r.tapIndex === 1) {
					uni.showModal({
						title: '拉黑',
						content: '双方将从推荐和聊天中消失。',
						success: async (m) => {
							if (!m.confirm) return
							await apiBlock(peer.value.id)
							uni.showToast({ title: '已拉黑', icon: 'none' })
							setTimeout(() => uni.navigateBack(), 400)
						}
					})
				} else {
					uni.showActionSheet({
						itemList: REPORT_REASONS.map((x) => x.label),
						success: async (rr) => {
							const reason = REPORT_REASONS[rr.tapIndex] || REPORT_REASONS[REPORT_REASONS.length - 1]
							try {
								await apiReport({ user_id: peer.value.id, reason: reason.key })
								uni.showToast({ title: '已举报', icon: 'none' })
							} catch (e) {
								uni.showToast({ title: (e && e.message) || '举报失败', icon: 'none' })
							}
						},
					})
				}
			} catch (e) {
				uni.showToast({ title: (e && e.message) || '操作失败', icon: 'none' })
			}
		}
	})
}
</script>

<style scoped>
.page { height:100vh; background:#FFF7FA; display:flex; flex-direction:column; }
.nav {
	padding: calc(env(safe-area-inset-top) + 12rpx) 24rpx 16rpx;
	display:flex; flex-direction:row; align-items:center;
	background:#fff;
	border-bottom: 1px solid rgba(255,107,154,0.12);
}
.back { color:#222; font-size:48rpx; width:60rpx; }
.peer { flex:1; display:flex; flex-direction:row; align-items:center; }
.nav-avatar-wrap { position:relative; margin-right:16rpx; }
.nav-avatar-inner { position:relative; width:64rpx; height:64rpx; }
.peer :deep(.expiry-ring) { margin-right: 12rpx; }
.nav-avatar { width:64rpx; height:64rpx; border-radius:50%; }
.nav-avatar.blur { filter: blur(8px); }
.online {
	position:absolute; right:0; bottom:0; width:16rpx; height:16rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #fff;
}
.title { display:block; color:#222; font-size:30rpx; font-weight:600; }
.status { display:block; color:#888; font-size:20rpx; }
.nav-actions { display:flex; flex-direction:row; align-items:center; }
.call-btn { color:#FF6B9A; font-size:36rpx; margin-right:12rpx; padding: 0 8rpx; }
.more { color:#222; font-size:40rpx; width:60rpx; text-align:right; }
.typing-banner {
	padding: 8rpx 24rpx; background: rgba(255,107,154,0.08);
}
.typing-banner text { color:#FF6B9A; font-size:22rpx; }
.receipt { color:#999; font-size:18rpx; margin-top:4rpx; }
.msg.mine .receipt { color: rgba(255,107,154,0.85); }
.gif-sheet {
	position: fixed; left: 0; right: 0; bottom: 0; z-index: 1100;
	background: #FFF7FA; border-radius: 28rpx 28rpx 0 0;
	padding: 24rpx 24rpx calc(env(safe-area-inset-bottom) + 24rpx);
	border-top: 1px solid rgba(255,107,154,0.2);
	max-height: 70vh;
}
.gif-input {
	background:#fff; border-radius:16rpx; padding:20rpx; color:#222; margin-bottom:16rpx;
	border: 1px solid rgba(255,107,154,0.25);
}
.gif-actions { display:flex; flex-direction:row; margin-bottom: 12rpx; }
.gif-btn {
	flex:1; background:#FF6B9A; border-radius:999rpx; padding:18rpx; text-align:center; margin-right:12rpx;
}
.gif-btn.ghost { background:#FFF0F5; margin-right:0; }
.gif-btn text { color:#fff; font-weight:700; font-size:24rpx; }
.gif-btn.ghost text { color:#FF6B9A; }
.gif-grid { max-height: 40vh; }
.gif-row { display:flex; flex-direction:row; flex-wrap:wrap; }
.gif-thumb {
	width: 30%; height: 180rpx; margin: 1.5%; border-radius: 12rpx; background:#FFE0EA;
}
.gif-empty { display:block; text-align:center; color:#999; font-size:24rpx; padding: 24rpx; }
.expired-banner {
	background: rgba(255,107,154,0.12);
	border-bottom: 1px solid rgba(255,107,154,0.25);
	padding: 16rpx 24rpx;
	display:flex; flex-direction:row; align-items:center; justify-content:center;
}
.expired-banner text { color:#FF6B9A; font-size:24rpx; }
.rematch-btn {
	margin-left: 20rpx; padding: 8rpx 18rpx; border-radius: 12rpx; background: #FF6B9A;
}
.rematch-btn text { color:#fff; font-size:22rpx; font-weight:600; }
.expire-ritual {
	position: fixed; inset: 0; z-index: 1200;
	background: rgba(40, 10, 24, 0.82);
	display: flex; align-items: center; justify-content: center;
	padding: 48rpx;
}
.ritual-card {
	width: 100%; max-width: 620rpx; background: #FFF7FA; border-radius: 28rpx;
	padding: 56rpx 40rpx; text-align: center;
	border: 1px solid rgba(255,107,154,0.25);
}
.ritual-title { display:block; color:#FF6B9A; font-size:48rpx; font-weight:800; margin-bottom:16rpx; }
.ritual-sub { display:block; color:#666; font-size:28rpx; margin-bottom:40rpx; line-height:1.45; }
.ritual-btn {
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3); border-radius:999rpx; padding:24rpx;
}
.ritual-btn text { color:#fff; font-weight:700; font-size:30rpx; }
.tpl-scroll { white-space: nowrap; margin-bottom: 14rpx; width: 100%; }
.tpl-chip {
	display: inline-block; max-width: 480rpx; margin-right: 12rpx; vertical-align: top;
	background: #FFF0F5; border-radius: 16rpx; padding: 12rpx 16rpx;
	border: 1px solid rgba(255,107,154,0.25); white-space: normal;
}
.tpl-chip.on { border-color: #FF6B9A; background: rgba(255,107,154,0.14); }
.tpl-chip text { color:#333; font-size:22rpx; line-height:1.35; }
.voice-bubble {
	display:flex; flex-direction:row; align-items:center;
	background:#fff; border-radius:24rpx; padding:18rpx 28rpx; min-width:160rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.msg.mine .voice-bubble { background:#FF6B9A; border:none; }
.voice-ico { color:#111; font-size:24rpx; margin-right:12rpx; }
.msg.mine .voice-ico { color:#fff; }
.voice-dur { color:#333; font-size:26rpx; }
.msg.mine .voice-dur { color:#fff; }
.photo-btn.rec { background:#FF6B9A; }
.photo-btn.rec text { color:#fff; }
.qa-panel {
	margin: 20rpx 24rpx; padding: 28rpx; background:#fff; border-radius: 24rpx;
	border: 1px solid rgba(255,107,154,0.2);
}
.qa-progress {
	display:flex; flex-direction:row; align-items:center; justify-content:center;
	margin-bottom: 20rpx;
}
.qa-dot {
	width: 18rpx; height: 18rpx; border-radius: 50%;
	background: #FFE0EA; border: 2rpx solid rgba(255,107,154,0.35);
}
.qa-dot.on { background: #FF6B9A; border-color: #FF6B9A; }
.qa-line {
	width: 64rpx; height: 4rpx; background: #FFE0EA; margin: 0 8rpx;
}
.qa-line.on { background: #FF6B9A; }
.qa-step { display:block; color:#FF6B9A; font-size:28rpx; font-weight:700; margin-bottom:8rpx; }
.qa-hint { display:block; color:#888; font-size:22rpx; margin-bottom:20rpx; }
.qa-bubble {
	background:#FFF0F5; border-radius: 16rpx; padding: 18rpx 20rpx; margin-bottom: 14rpx;
}
.qa-bubble.ans { background:#F5F5F7; }
.qa-label { display:block; color:#999; font-size:20rpx; margin-bottom:6rpx; }
.qa-body { display:block; color:#222; font-size:28rpx; line-height:1.45; }
.qa-form { margin-top: 8rpx; }
.qa-input {
	width:100%; min-height: 160rpx; box-sizing:border-box;
	background:#FFF7FA; border-radius:16rpx; padding:18rpx; color:#222; font-size:28rpx;
	border: 1px solid rgba(255,107,154,0.2);
}
.qa-submit {
	margin-top: 16rpx; background: linear-gradient(90deg,#FF6B9A,#FF8FB3);
	border-radius:999rpx; padding: 20rpx; text-align:center;
}
.qa-submit text { color:#fff; font-weight:700; font-size:28rpx; }
.qa-review { display:flex; flex-direction:column; margin-top: 12rpx; }
.qa-review > view + view { margin-top: 12rpx; }
.qa-approve {
	background: linear-gradient(90deg,#FF6B9A,#FF8FB3); border-radius:999rpx; padding:20rpx; text-align:center;
}
.qa-approve text { color:#fff; font-weight:700; }
.qa-reject {
	border: 1px solid rgba(0,0,0,0.12); border-radius:999rpx; padding:18rpx; text-align:center;
}
.qa-reject.end { border-color: rgba(255,107,154,0.35); }
.qa-reject text { color:#666; }
.qa-reject.end text { color:#FF6B9A; }
.qa-retry {
	margin: 8rpx 0 12rpx; padding: 14rpx 16rpx; border-radius: 12rpx;
	background: rgba(255,198,41,0.18);
}
.qa-retry text { color:#B8860B; font-size:22rpx; }
.qa-wait { padding: 24rpx 0; text-align:center; }
.qa-wait text { color:#888; font-size:26rpx; }
.msgs { flex:1; padding: 0 24rpx; box-sizing:border-box; }
.starters { padding: 24rpx 0 40rpx; }
.starters-title { display:block; color:#FF6B9A; font-size:24rpx; font-weight:700; margin-bottom:16rpx; text-align:center; }
.match-hero {
	padding: 48rpx 12rpx 12rpx; text-align: center;
}
.mh-avatars {
	display:flex; flex-direction:row; justify-content:center; align-items:center;
	margin-bottom: 18rpx;
}
.mh-av {
	width: 120rpx; height: 120rpx; border-radius: 50%;
	border: 4rpx solid #FFF7FA; margin: 0 -10rpx;
}
.mh-av.ph { background: #FFE0EA; }
.mh-title { display:block; color:#222; font-size:32rpx; font-weight:800; margin-bottom:8rpx; }
.mh-sub { display:block; color:#FF6B9A; font-size:24rpx; }
.starter {
	background:#fff; border-radius:999rpx; padding:18rpx 28rpx; margin-bottom:12rpx; text-align:center;
	border: 1px solid rgba(255,107,154,0.2);
}
.starter text { color:#222; font-size:26rpx; }
.msg { margin-bottom:16rpx; display:flex; flex-direction:column; align-items:flex-start; }
.msg.mine { align-items:flex-end; }
.bubble {
	background:#fff; color:#222; padding:18rpx 24rpx; border-radius:24rpx; max-width:75%; font-size:28rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.msg.mine .bubble { background:#FF6B9A; color:#fff; border:none; }
.img-bubble {
	max-width: 70%; border-radius: 20rpx; overflow: hidden;
}
.tr-btn { color:#FF6B9A; font-size:22rpx; margin-top:4rpx; }
.composer {
	display:flex; flex-direction:row; align-items:center;
	padding:16rpx 24rpx calc(env(safe-area-inset-bottom) + 16rpx);
	background:#fff;
	border-top: 1px solid rgba(255,107,154,0.12);
}
.composer.locked { opacity: 0.7; }
.photo-btn {
	width:64rpx; height:64rpx; border-radius:50%; background:#FFF0F5;
	display:flex; align-items:center; justify-content:center; margin-right:12rpx;
}
.photo-btn text { color:#FF6B9A; font-size:36rpx; }
.input {
	flex:1; background:#FFF7FA; border-radius:999rpx; padding:18rpx 28rpx; color:#222; margin-right:16rpx;
}
.ph { color:#999; }
.send {
	background:#FF6B9A; border-radius:999rpx; padding:18rpx 28rpx;
}
.send text { color:#fff; font-weight:600; }
</style>
