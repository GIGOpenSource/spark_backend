<template>
	<view class="page">
		<view class="nav">
			<text class="back" @click="back">‹</text>
			<view class="peer" @click="openProfile">
				<view class="nav-avatar-wrap">
					<image v-if="peer.avatar_url" :src="peer.avatar_url" class="nav-avatar" :class="{ blur: blurPeer }" mode="aspectFill" />
					<view class="online" v-if="peer.is_online && !blurPeer" />
				</view>
				<view>
					<text class="title">{{ peer.nickname || 'Chat' }}</text>
					<text class="status">{{ statusText }}</text>
				</view>
			</view>
			<view class="nav-right">
				<text class="call-btn" @click="goCall" v-if="!matchLocked && !waitingForOpener">📹</text>
				<text class="more" @click="more">⋯</text>
			</view>
		</view>

		<view class="typing-banner" v-if="peerTyping && !matchLocked">
			<text>{{ peer.nickname || 'They' }} is typing…</text>
		</view>

		<view class="expired-banner" v-if="matchLocked || waitingForOpener || showOpenTimer">
			<text>{{ bannerPrimary }}</text>
			<view v-if="canExtend && iAmOpener && !matchLocked" class="rematch-btn" @click="doExtend">
				<text>{{ extendLabel }}</text>
			</view>
			<view
				v-if="!waitingForOpener && matchStatus === 'expired' && peer && peer.id"
				class="rematch-btn"
				@click="likeAgain"
			>
				<text>{{ likeAgainLabel }}</text>
			</view>
		</view>

		<scroll-view scroll-y class="msgs" :scroll-into-view="scrollInto">
			<view v-if="!messages.length && !waitingForOpener" class="match-hero">
				<view class="mh-avatars">
					<image v-if="meAvatar" :src="meAvatar" class="mh-av" mode="aspectFill" />
					<view v-else class="mh-av ph" />
					<image v-if="peer.avatar_url" :src="peer.avatar_url" class="mh-av" mode="aspectFill" />
					<view v-else class="mh-av ph" />
				</view>
				<text class="mh-title">You matched with {{ peer.nickname || 'them' }}</text>
				<text class="mh-sub">{{ peer.is_online ? 'Online now — say something' : 'Start the conversation' }}</text>
			</view>
			<view v-if="!messages.length && !waitingForOpener" class="starters">
				<text class="starters-title">Icebreakers</text>
				<view v-for="(s, i) in starters" :key="i" class="starter" @click="quickSend(s)">
					<text>{{ s }}</text>
				</view>
			</view>
			<view v-if="waitingForOpener && !messages.length" class="starters">
				<text class="starters-title">{{ waitingBannerText }}</text>
			</view>
			<view v-for="row in timeline" :key="row.key" :id="row.idAttr" class="msg" :class="{ mine: row.mine, day: row.type === 'day' }">
				<template v-if="row.type === 'day'">
					<text class="day-label">{{ row.label }}</text>
				</template>
				<template v-else>
				<image
					v-if="row.m.msg_type === 'image' || row.m.msg_type === 'photo' || row.m.msg_type === 'gif' || isGifUrl(row.m.content)"
					:src="row.m.content"
					class="img-bubble"
					mode="widthFix"
					@click="preview(row.m.content)"
					@longpress="saveImage(row.m.content)"
				/>
				<view v-else-if="row.m.msg_type === 'voice' || row.m.msg_type === 'audio'" class="voice-bubble" @click="playVoice(row.m)">
					<text class="voice-ico">{{ playingId === row.m.id ? '❚❚' : '▶' }}</text>
					<text class="voice-dur">{{ formatVoiceDur(row.m) }}</text>
				</view>
				<template v-else>
					<text class="bubble">{{ showOriginal[row.m.id] ? row.m.content : (row.m.translated || row.m.content) }}</text>
					<text
						v-if="row.m.translated && !showOriginal[row.m.id]"
						class="tr-btn"
						@click="toggleOriginal(row.m)"
					>Original</text>
					<text
						v-else-if="row.m.msg_type === 'text' || !row.m.msg_type"
						class="tr-btn"
						@click="translate(row.m)"
					>{{ translating[row.m.id] ? '…' : 'Translate' }}</text>
				</template>
				<text class="time">{{ formatMsgTime(row.m) }}</text>
				<text
					v-if="row.m.sender_id === myId"
					class="receipt"
					:class="{ read: !!(row.m.read_at || row.m.is_read), delivered: !!row.m.delivered_at && !(row.m.read_at || row.m.is_read) }"
				>{{ receiptMark(row.m) }}</text>
				</template>
			</view>
		</scroll-view>

		<view class="composer" v-if="!matchLocked && !waitingForOpener">
			<view class="photo-btn" @click="pickPhoto"><text>＋</text></view>
			<view class="photo-btn" :class="{ rec: recording }" @click="toggleRecord"><text>{{ recording ? '■' : '🎤' }}</text></view>
			<view class="photo-btn" @click="openGif"><text>GIF</text></view>
			<input
				class="input"
				v-model="text"
				:placeholder="composerHint"
				placeholder-class="ph"
				confirm-type="send"
				@confirm="send"
				@input="onTypingInput"
			/>
			<view class="send" @click="send"><text>Send</text></view>
		</view>
		<view class="composer locked" v-else>
			<input class="input" disabled :placeholder="waitingForOpener ? waitingBannerText : 'Chat unavailable'" placeholder-class="ph" />
		</view>

		<view class="gif-mask" v-if="showGif" @click="showGif = false">
			<view class="gif-sheet" @click.stop>
				<text class="gif-title">GIF / sticker</text>
				<input
					class="input gif-search"
					v-model="gifQuery"
					placeholder="Search GIFs"
					placeholder-class="ph"
					confirm-type="search"
					@confirm="searchGifs"
					@input="onGifQueryInput"
				/>
				<scroll-view scroll-y class="gif-grid-wrap" v-if="gifResults.length">
					<view class="gif-grid">
						<image
							v-for="(g, i) in gifResults"
							:key="g.id || i"
							:src="g.preview || g.url"
							class="gif-cell"
							mode="aspectFill"
							@click="sendGifResult(g)"
						/>
					</view>
				</scroll-view>
				<text class="gif-empty" v-else-if="gifSearching">Searching…</text>
				<text class="gif-empty" v-else-if="gifQuery && !gifSearching">No GIFs — paste a URL below</text>
				<input class="input" v-model="gifUrl" placeholder="Paste Tenor/Giphy URL" placeholder-class="ph" />
				<view class="sticker-row">
					<view class="sticker" v-for="s in stickers" :key="s" @click="sendGif(s)"><text>{{ s }}</text></view>
				</view>
				<view class="btn" @click="sendGifUrl"><text>Send GIF URL</text></view>
				<view class="link" @click="showGif = false"><text>Cancel</text></view>
			</view>
		</view>

		<VipSheet v-model:show="showVip" reason="need_platinum" @purchased="onPurchased" />
	</view>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { host } from '@/config/config.js'
import { isZhUi } from '@/config/i18n.js'
import { uploadFile } from '@/api/upload.js'
import {
	apiMessages, apiSendMessage, apiTranslate, apiSearchGifs,
} from '@/api/chat.js'
import { apiUnmatch, apiExtendMatch } from '@/api/likes.js'
import { apiBlock, apiReport } from '@/api/profile.js'
import { apiSwipe } from '@/api/recommend.js'
import { WS_HOST } from '@/config/config.js'
import VipSheet from '@/components/VipSheet/VipSheet.vue'
import {
	formatExpireCountdown, isWomenFirst, isExtendEnabled,
} from '@/utils/productProfile.js'
import { trackClick } from '@/utils/analytics.js'

const REPORT_REASONS = [
	{ key: 'spam', label: 'Spam' },
	{ key: 'harassment', label: 'Harassment' },
	{ key: 'inappropriate', label: 'Inappropriate' },
	{ key: 'fake', label: 'Fake profile' },
	{ key: 'underage', label: 'Underage' },
	{ key: 'other', label: 'Other' },
]

const cid = ref(null)
const matchId = ref(null)
const MSG_DOM_CAP = 200 // F-07: cap DOM messages to last N
const messages = ref([])
const peer = ref({})
const text = ref('')
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
const canExtend = ref(false)
const countdown = ref('')
const nowTick = ref(Date.now())
let countdownTimer = null
const translating = reactive({})
const showOriginal = reactive({})
const showGif = ref(false)
const gifUrl = ref('')
const gifQuery = ref('')
const gifResults = ref([])
const gifSearching = ref(false)
const peerTyping = ref(false)
const recording = ref(false)
const playingId = ref(null)
const stickers = ['🔥', '😂', '😍', '👋', '☕', '💪', '🌹', '✨']
const starters = [
	'Hey! Loved your photos ✨',
	'Coffee or museum this weekend?',
	'What are you into lately?'
]
let socketTask = null
let recorder = null
let innerAudio = null
let recordStartedAt = 0
let lastTypingSent = 0
let typingStopTimer = null
let peerTypingTimer = null
let gifSearchTimer = null
let h5MediaRecorder = null
let h5Chunks = []
let h5Stream = null

const meAvatar = computed(() => {
	const me = uni.getStorageSync('userInfo') || {}
	if (me.avatar_url) return me.avatar_url
	if (me.photos && me.photos.length) return me.photos[0].url
	return ''
})

const zh = computed(() => isZhUi())
const sending = ref(false)

const matchLocked = computed(() => (
	matchStatus.value === 'ended'
	|| matchStatus.value === 'expired'
	|| sayHiExpired.value
))

const showOpenTimer = computed(() => (
	!matchLocked.value
	&& messagingMode.value === 'women_first'
	&& !messages.value.length
	&& !!matchExpireAt.value
))

const waitingBannerText = computed(() => {
	const left = countdown.value
	if (zh.value) {
		return left ? `等她先开口 · 剩余 ${left}` : '等她先开口…'
	}
	return left ? `Waiting for her to move first · ${left}` : 'Waiting for her to move first…'
})

const openerTimerText = computed(() => {
	const left = countdown.value
	if (zh.value) return left ? `请先开口 · 剩余 ${left}` : '请先开口打招呼'
	return left ? `You move first · ${left} left` : 'You move first'
})

const bannerPrimary = computed(() => {
	if (matchLocked.value) return lockedBannerText.value
	if (waitingForOpener.value) return waitingBannerText.value
	if (showOpenTimer.value && iAmOpener.value) return openerTimerText.value
	if (showOpenTimer.value) return waitingBannerText.value
	return ''
})

const lockedBannerText = computed(() => {
	if (zh.value) {
		if (sayHiExpired.value) return '打招呼已过期'
		if (matchStatus.value === 'expired') return '匹配已过期'
		return '匹配已结束'
	}
	if (sayHiExpired.value) return 'This Say Hi has expired'
	if (matchStatus.value === 'expired') return 'This match has expired'
	return 'This match has ended'
})

const extendLabel = computed(() => (zh.value ? '延长时限' : 'Extend'))
const likeAgainLabel = computed(() => (zh.value ? '再次喜欢' : 'Like again'))

const statusText = computed(() => {
	if (peerTyping.value) return 'typing…'
	if (waitingForOpener.value) return waitingBannerText.value
	if (sayHiExpired.value) return zh.value ? '打招呼已过期' : 'Say Hi expired'
	if (matchStatus.value === 'expired') return zh.value ? '匹配已过期' : 'Match expired'
	if (matchStatus.value === 'ended') return zh.value ? '已取消匹配' : 'Unmatched'
	if (isPrematch.value && blurPeer.value) {
		if (freeRepliesLeft.value === null) return 'Say Hi'
		return `Free replies left: ${freeRepliesLeft.value}`
	}
	if (isPrematch.value) return 'Say Hi · not matched yet'
	if (iAmOpener.value && messagingMode.value === 'women_first' && !messages.value.length) {
		return openerTimerText.value
	}
	const bucket = peer.value.active_bucket
	if (bucket === 'now' || peer.value.is_online) return zh.value ? '在线' : 'Active now'
	if (bucket === 'today') return zh.value ? '今日活跃' : 'Active today'
	if (bucket === 'week') return zh.value ? '本周活跃' : 'Active this week'
	return zh.value ? '最近活跃' : 'Recently active'
})

const timeline = computed(() => {
	const rows = []
	let lastDay = ''
	;(messages.value || []).forEach((m) => {
		const day = dayKey(m.created_at)
		if (day && day !== lastDay) {
			rows.push({ type: 'day', key: `d-${day}`, label: dayLabel(day), idAttr: `d${day}` })
			lastDay = day
		}
		rows.push({
			type: 'msg',
			key: `m-${m.id}`,
			idAttr: 'm' + m.id,
			mine: m.sender_id === myId,
			m,
		})
	})
	return rows
})

function dayKey(iso) {
	if (!iso) return ''
	const d = new Date(iso)
	if (Number.isNaN(d.getTime())) return ''
	return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
}

function dayLabel(key) {
	const [y, m, d] = key.split('-').map(Number)
	const dt = new Date(y, m - 1, d)
	const today = new Date()
	const yest = new Date()
	yest.setDate(today.getDate() - 1)
	if (dt.toDateString() === today.toDateString()) return zh.value ? '今天' : 'Today'
	if (dt.toDateString() === yest.toDateString()) return zh.value ? '昨天' : 'Yesterday'
	return dt.toLocaleDateString()
}

function formatMsgTime(m) {
	const iso = m && m.created_at
	if (!iso) return ''
	const d = new Date(iso)
	if (Number.isNaN(d.getTime())) return ''
	return `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const composerHint = computed(() => {
	if (matchLocked.value) return zh.value ? '暂无法聊天' : 'Chat unavailable'
	if (waitingForOpener.value) return waitingBannerText.value
	if (blurPeer.value && freeRepliesLeft.value === 0) return 'Upgrade Platinum to keep chatting'
	return zh.value ? '发消息' : 'Message'
})

function receiptMark(m) {
	if (!m) return ''
	if (m.read_at || m.is_read) return '✓✓'
	if (m.delivered_at) return '✓✓'
	return '✓'
}

function tickCountdown() {
	nowTick.value = Date.now()
	countdown.value = formatExpireCountdown(matchExpireAt.value, nowTick.value)
	if (matchExpireAt.value && new Date(matchExpireAt.value).getTime() <= Date.now() && !messages.value.length) {
		if (messagingMode.value === 'women_first') {
			matchStatus.value = 'expired'
		}
	}
}

onLoad((q) => {
	cid.value = q.id
})

onMounted(async () => {
	await load()
	const draft = uni.getStorageSync('match_draft_message')
	if (draft && typeof draft === 'string' && draft.trim()) {
		text.value = draft.trim()
		uni.removeStorageSync('match_draft_message')
	}
	connectWs()
	countdownTimer = setInterval(tickCountdown, 1000)
})

onUnmounted(() => {
	if (countdownTimer) clearInterval(countdownTimer)
	countdownTimer = null
	if (typingStopTimer) clearTimeout(typingStopTimer)
	if (peerTypingTimer) clearTimeout(peerTypingTimer)
	if (gifSearchTimer) clearTimeout(gifSearchTimer)
	sendTyping(false)
	stopH5Stream()
	try {
		if (socketTask && socketTask.close) socketTask.close()
	} catch (e) {}
	try {
		if (innerAudio) {
			innerAudio.stop()
			innerAudio.destroy && innerAudio.destroy()
		}
	} catch (e) {}
})

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
		waitingForOpener.value = !!data.waiting_for_opener
		iAmOpener.value = !!data.i_am_opener
		messagingMode.value = data.messaging_mode || (isWomenFirst() ? 'women_first' : 'any')
		matchExpireAt.value = data.expire_at || data.match_expire_at || null
		canExtend.value = !!data.can_extend && isExtendEnabled()
		if (sayHiExpired.value) matchStatus.value = 'expired'
		if (messages.value.length) {
			waitingForOpener.value = false
			matchExpireAt.value = null
			scrollInto.value = 'm' + messages.value[messages.value.length - 1].id
		}
		tickCountdown()
	} catch (e) {
		uni.showToast({ title: zh.value ? '加载聊天失败' : 'Failed to load chat', icon: 'none' })
	}
}

async function doExtend() {
	if (!matchId.value || !canExtend.value) return
	try {
		const res = await apiExtendMatch(matchId.value)
		const data = res.results || {}
		matchExpireAt.value = data.expire_at || matchExpireAt.value
		canExtend.value = !!data.can_extend
		tickCountdown()
		uni.showToast({ title: zh.value ? '已延长' : 'Extended', icon: 'none' })
	} catch (e) {
		uni.showToast({ title: (e && e.message) || (zh.value ? '延长失败' : 'Extend failed'), icon: 'none' })
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
					handleWs(payload)
				} catch (e) {}
			})
		}
		if (socketTask && typeof socketTask.onClose === 'function') {
			socketTask.onClose(() => { socketTask = null })
		}
	} catch (e) {}
}

function handleWs(payload) {
	if (!payload) return
	if (payload.type === 'message' && payload.data) {
		appendMsg(payload.data)
		peerTyping.value = false
		return
	}
	if (payload.type === 'typing') {
		if (payload.user_id && payload.user_id === myId.value) return
		peerTyping.value = !!payload.is_typing
		if (peerTypingTimer) clearTimeout(peerTypingTimer)
		if (peerTyping.value) {
			peerTypingTimer = setTimeout(() => { peerTyping.value = false }, 4000)
		}
		return
	}
	if (payload.type === 'delivered' || payload.type === 'read') {
		const ids = payload.message_ids || []
		if (!ids.length) return
		messages.value = messages.value.map((m) => {
			if (!ids.includes(m.id)) return m
			const next = { ...m }
			if (payload.type === 'delivered') {
				next.delivered_at = next.delivered_at || new Date().toISOString()
			}
			if (payload.type === 'read') {
				next.is_read = true
				next.read_at = next.read_at || new Date().toISOString()
			}
			return next
		})
	}
}

function sendTyping(isTyping) {
	if (!socketTask || typeof socketTask.send !== 'function') return
	try {
		socketTask.send({
			data: JSON.stringify({ type: 'typing', is_typing: !!isTyping }),
		})
	} catch (e) {}
}

function onTypingInput() {
	const now = Date.now()
	if (now - lastTypingSent > 1200) {
		lastTypingSent = now
		sendTyping(true)
	}
	if (typingStopTimer) clearTimeout(typingStopTimer)
	typingStopTimer = setTimeout(() => sendTyping(false), 2000)
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
	if (matchLocked.value || waitingForOpener.value) {
		uni.showToast({ title: waitingForOpener.value ? waitingBannerText.value : 'Chat unavailable', icon: 'none' })
		return
	}
	if (blurPeer.value && freeRepliesLeft.value === 0) {
		showVip.value = true
		return
	}
	const content = text.value
	text.value = ''
	sendTyping(false)
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
		if (e && e.message === 'say_hi_expired') {
			sayHiExpired.value = true
			matchStatus.value = 'expired'
			uni.showToast({ title: 'Say Hi expired', icon: 'none' })
			return
		}
		if (e && (e.message === 'match_ended' || e.message === 'match_expired')) {
			matchStatus.value = e.message === 'match_expired' ? 'expired' : 'ended'
			uni.showToast({ title: e.message === 'match_expired' ? 'Match expired' : 'Match ended', icon: 'none' })
			return
		}
		if (e && e.message === 'content_blocked') {
			uni.showToast({ title: 'Message blocked by word filter', icon: 'none' })
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
			uni.showToast({ title: 'Translate mock (configure API key)', icon: 'none' })
		}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Translate failed', icon: 'none' })
	}
	translating[m.id] = false
}

function toggleOriginal(m) {
	showOriginal[m.id] = !showOriginal[m.id]
}

function pickPhoto() {
	uni.chooseImage({
		count: 1,
		success: async (r) => {
			const path = r.tempFilePaths[0]
			uni.showLoading({ title: 'Sending...' })
			try {
				const body = await uploadFile({ url: '/chat/upload/', filePath: path })
				const url = body.results && body.results.url
				if (!url) {
					uni.showToast({ title: 'upload failed', icon: 'none' })
					return
				}
				const res = await apiSendMessage(cid.value, { content: url, msg_type: 'image' })
				appendMsg(res.results)
			} catch (e) {
				uni.showToast({ title: 'send failed', icon: 'none' })
			} finally {
				uni.hideLoading()
			}
		}
	})
}

function preview(url) {
	uni.previewImage({ urls: [url], current: url })
}

function saveImage(url) {
	uni.showActionSheet({
		itemList: ['Save image', 'Open fullscreen'],
		success: (r) => {
			if (r.tapIndex === 1) {
				preview(url)
				return
			}
			// #ifdef H5
			uni.setClipboardData({ data: url })
			uni.showToast({ title: 'Image URL copied', icon: 'none' })
			// #endif
			// #ifndef H5
			uni.downloadFile({
				url,
				success: (d) => {
					uni.saveImageToPhotosAlbum({
						filePath: d.tempFilePath,
						success: () => uni.showToast({ title: 'Saved', icon: 'none' }),
						fail: () => uni.showToast({ title: 'Save failed', icon: 'none' }),
					})
				},
				fail: () => uni.showToast({ title: 'Download failed', icon: 'none' }),
			})
			// #endif
		}
	})
}

function isGifUrl(url) {
	return typeof url === 'string' && /\.gif(\?|$)/i.test(url)
}

function formatVoiceDur(m) {
	const ms = Number(m.duration_ms || m.duration || 0)
	if (!ms) return 'Voice'
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
			uni.showToast({ title: 'Recorder error', icon: 'none' })
		})
	} catch (e) {
		recorder = null
	}
	return recorder
}

function stopH5Stream() {
	try {
		if (h5MediaRecorder && h5MediaRecorder.state !== 'inactive') {
			h5MediaRecorder.stop()
		}
	} catch (e) {}
	h5MediaRecorder = null
	try {
		if (h5Stream) {
			h5Stream.getTracks().forEach((t) => t.stop())
		}
	} catch (e) {}
	h5Stream = null
	h5Chunks = []
}

async function toggleRecordH5() {
	// #ifdef H5
	try {
		if (recording.value && h5MediaRecorder) {
			h5MediaRecorder.stop()
			return
		}
		if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices) {
			return false
		}
		h5Stream = await navigator.mediaDevices.getUserMedia({ audio: true })
		h5Chunks = []
		h5MediaRecorder = new MediaRecorder(h5Stream)
		h5MediaRecorder.ondataavailable = (e) => {
			if (e.data && e.data.size) h5Chunks.push(e.data)
		}
		h5MediaRecorder.onstop = async () => {
			recording.value = false
			const duration = Math.max(0, Date.now() - recordStartedAt)
			const blob = new Blob(h5Chunks, { type: 'audio/webm' })
			stopH5Stream()
			const file = new File([blob], `voice_${Date.now()}.webm`, { type: 'audio/webm' })
			uploadVoiceBlob(file, duration)
		}
		recordStartedAt = Date.now()
		recording.value = true
		h5MediaRecorder.start()
		return true
	} catch (e) {
		recording.value = false
		stopH5Stream()
		return false
	}
	// #endif
	// #ifndef H5
	return false
	// #endif
}

async function toggleRecord() {
	// Prefer H5 MediaRecorder when available
	// #ifdef H5
	const ok = await toggleRecordH5()
	if (ok || recording.value) return
	// #endif

	const r = ensureRecorder()
	if (!r) {
		uni.showToast({ title: 'Recorder unavailable on this platform', icon: 'none' })
		return
	}
	if (recording.value) {
		r.stop()
		return
	}
	recording.value = true
	recordStartedAt = Date.now()
	r.start({ format: 'mp3', duration: 60000 })
}

function uploadVoiceBlob(file, durationMs) {
	uni.showLoading({ title: 'Sending…' })
	// #ifdef H5
	const fd = new FormData()
	fd.append('file', file)
	fd.append('kind', 'voice')
	fetch(host + '/chat/upload/?kind=voice', {
		method: 'POST',
		headers: {
			token: uni.getStorageSync('token') || '',
			'is-dev': 'true',
			'Accept-Language': uni.getStorageSync('currentLanguage') || 'zh',
		},
		body: fd,
	})
		.then((r) => r.json())
		.then(async (body) => {
			const url = body.results && body.results.url
			if (!url) {
				uni.showToast({ title: 'upload failed', icon: 'none' })
				return
			}
			const res = await apiSendMessage(cid.value, {
				content: url,
				msg_type: 'voice',
				duration_ms: durationMs,
			})
			appendMsg(res.results)
		})
		.catch(() => uni.showToast({ title: 'network error', icon: 'none' }))
		.finally(() => uni.hideLoading())
	// #endif
}

function uploadVoice(path, durationMs) {
	uni.showLoading({ title: 'Sending…' })
	uploadFile({
		url: '/chat/upload/?kind=voice',
		filePath: path,
		formData: { kind: 'voice' },
	}).then(async (body) => {
		const url = body.results && body.results.url
		if (!url) {
			uni.showToast({ title: 'upload failed', icon: 'none' })
			return
		}
		const res = await apiSendMessage(cid.value, {
			content: url,
			msg_type: 'voice',
			duration_ms: durationMs,
		})
		appendMsg(res.results)
	}).catch(() => {
		uni.showToast({ title: 'network error', icon: 'none' })
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
		uni.showToast({ title: 'Playback failed', icon: 'none' })
	}
}

function openGif() {
	showGif.value = true
	if (!gifResults.value.length && !gifQuery.value) {
		gifQuery.value = 'hello'
		searchGifs()
	}
}

function onGifQueryInput() {
	if (gifSearchTimer) clearTimeout(gifSearchTimer)
	gifSearchTimer = setTimeout(searchGifs, 400)
}

async function searchGifs() {
	const q = (gifQuery.value || '').trim()
	if (!q) {
		gifResults.value = []
		return
	}
	gifSearching.value = true
	try {
		const res = await apiSearchGifs(q)
		gifResults.value = (res.results && res.results.list) || []
	} catch (e) {
		gifResults.value = []
		uni.showToast({ title: (e && e.message) || 'GIF search failed', icon: 'none' })
	}
	gifSearching.value = false
}

async function sendGifResult(g) {
	const url = (g && (g.url || g.preview)) || ''
	if (!url) return
	showGif.value = false
	try {
		const res = await apiSendMessage(cid.value, { content: url, msg_type: 'gif' })
		appendMsg(res.results)
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Send failed', icon: 'none' })
	}
}

async function sendGif(sticker) {
	showGif.value = false
	text.value = sticker
	await send()
}

async function sendGifUrl() {
	const url = gifUrl.value.trim()
	if (!url) {
		uni.showToast({ title: 'Paste a GIF URL', icon: 'none' })
		return
	}
	showGif.value = false
	gifUrl.value = ''
	try {
		const res = await apiSendMessage(cid.value, { content: url, msg_type: 'gif' })
		appendMsg(res.results)
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Send failed', icon: 'none' })
	}
}

function goCall() {
	if (!cid.value) return
	trackClick('start_call')
	uni.navigateTo({ url: `/pagesA/chat/call?cid=${cid.value}` })
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
		uni.showToast({ title: 'Liked again', icon: 'none' })
		uni.switchTab({ url: '/pages/discover/index' })
	} catch (e) {
		if (e && (e.message === 'daily_like_limit' || (e.results && e.results.need_vip))) {
			showVip.value = true
		} else {
			uni.showToast({ title: (e && e.message) || 'Like failed', icon: 'none' })
		}
	}
}

function back() {
	uni.navigateBack()
}

function reportUser() {
	uni.showActionSheet({
		itemList: REPORT_REASONS.map((r) => r.label),
		success: async (r) => {
			const reason = REPORT_REASONS[r.tapIndex]
			if (!reason || !peer.value.id) return
			try {
				await apiReport({ user_id: peer.value.id, reason: reason.key })
				uni.showToast({ title: 'Reported', icon: 'none' })
			} catch (e) {
				uni.showToast({ title: (e && e.message) || 'Report failed', icon: 'none' })
			}
		}
	})
}

function more() {
	uni.showActionSheet({
		itemList: ['Unmatch', 'Block', 'Report'],
		success: async (r) => {
			try {
				if (r.tapIndex === 0) {
					if (!matchId.value) {
						uni.showToast({ title: 'No match', icon: 'none' })
						return
					}
					await apiUnmatch(matchId.value)
					uni.showToast({ title: 'Unmatched', icon: 'none' })
					setTimeout(() => uni.navigateBack(), 400)
				} else if (r.tapIndex === 1) {
					uni.showModal({
						title: 'Block',
						content: 'You both will disappear from recommendations and chats.',
						success: async (m) => {
							if (!m.confirm) return
							await apiBlock(peer.value.id)
							uni.showToast({ title: 'Blocked', icon: 'none' })
							setTimeout(() => uni.navigateBack(), 400)
						}
					})
				} else {
					reportUser()
				}
			} catch (e) {
				uni.showToast({ title: (e && e.message) || 'Action failed', icon: 'none' })
			}
		}
	})
}
</script>

<style scoped>
.page { height:100vh; background: var(--bg, #FFFFFF); display:flex; flex-direction:column; }
.nav {
	padding: calc(env(safe-area-inset-top) + 12rpx) 24rpx 16rpx;
	display:flex; flex-direction:row; align-items:center;
	border-bottom: 1px solid rgba(0,0,0,0.06);
}
.back { color:#111; font-size:48rpx; width:60rpx; }
.peer { flex:1; display:flex; flex-direction:row; align-items:center; }
.nav-avatar-wrap { position:relative; margin-right:16rpx; }
.nav-avatar { width:64rpx; height:64rpx; border-radius:50%; }
.nav-avatar.blur { filter: blur(8px); }
.online {
	position:absolute; right:0; bottom:0; width:16rpx; height:16rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #FFFFFF;
}
.title { display:block; color:#111; font-size:30rpx; }
.status { display:block; color:#666; font-size:20rpx; }
.nav-right { display:flex; flex-direction:row; align-items:center; }
.call-btn { color:#111; font-size:36rpx; margin-right:12rpx; padding: 0 8rpx; }
.more { color:#111; font-size:40rpx; width:48rpx; text-align:right; }
.typing-banner {
	background: #FFF5F7; padding: 10rpx 24rpx; text-align:center;
	border-bottom: 1px solid rgba(253,38,122,0.12);
}
.typing-banner text { color:#FD267A; font-size:22rpx; }
.expired-banner {
	background: rgba(255,75,85,0.15);
	border-bottom: 1px solid rgba(255,75,85,0.3);
	padding: 16rpx 24rpx;
	display:flex; flex-direction:row; align-items:center; justify-content:center;
}
.expired-banner text { color:#FF4B55; font-size:24rpx; }
.rematch-btn {
	margin-left: 20rpx; padding: 8rpx 18rpx; border-radius: 12rpx; background: #FF4B55;
}
.rematch-btn text { color:#fff; font-size:22rpx; font-weight:600; }
.msgs { flex:1; padding: 0 24rpx; box-sizing:border-box; }
.match-hero {
	padding: 48rpx 12rpx 12rpx; text-align: center;
}
.mh-avatars {
	display:flex; flex-direction:row; justify-content:center; align-items:center;
	margin-bottom: 18rpx;
}
.mh-av {
	width: 120rpx; height: 120rpx; border-radius: 50%;
	border: 4rpx solid #FFFFFF; margin: 0 -10rpx;
}
.mh-av.ph { background: #F3F0F7; }
.mh-title { display:block; color:#111; font-size:32rpx; font-weight:800; margin-bottom:8rpx; }
.mh-sub { display:block; color:#666; font-size:24rpx; }
.starters { padding: 24rpx 0 40rpx; }
.starters-title { display:block; color:#FF4458; font-size:24rpx; font-weight:700; margin-bottom:16rpx; text-align:center; }
.starter {
	background: #FFF5F7; border-radius:999rpx; padding:18rpx 28rpx; margin-bottom:12rpx; text-align:center;
	border: 1px solid rgba(253,38,122,0.2);
}
.starter text { color:#222; font-size:26rpx; }
.msg { margin-bottom:16rpx; display:flex; flex-direction:column; align-items:flex-start; }
.msg.day { align-items:center; margin: 24rpx 0 8rpx; }
.day-label { color:var(--muted,#999); font-size:22rpx; }
.time { color:var(--muted,#999); font-size:20rpx; margin-top:4rpx; }
.msg.mine { align-items:flex-end; }
.bubble {
	background:#F0F0F0; color:#111; padding:18rpx 24rpx; border-radius:24rpx; max-width:75%; font-size:28rpx;
}
.msg.mine .bubble { background: linear-gradient(90deg, #FD267A, #FF6036); color: #fff; }
.img-bubble {
	max-width: 70%; border-radius: 20rpx; overflow: hidden;
}
.receipt { color:#999; font-size:20rpx; margin-top:4rpx; }
.msg.mine .receipt { color:#FD267A; opacity: 0.55; }
.msg.mine .receipt.delivered { opacity: 0.85; }
.msg.mine .receipt.read { opacity: 1; color:#3B82F6; }
.tr-btn { color:#2563EB; font-size:22rpx; margin-top:4rpx; }
.composer {
	display:flex; flex-direction:row; align-items:center;
	padding:16rpx 24rpx calc(env(safe-area-inset-bottom) + 16rpx);
	background:#FFFFFF;
	border-top: 1px solid rgba(0,0,0,0.08);
}
.composer.locked { opacity: 0.7; }
.photo-btn {
	width:64rpx; height:64rpx; border-radius:50%; background:#F3F0F7;
	display:flex; align-items:center; justify-content:center; margin-right:10rpx;
}
.photo-btn text { color:#666; font-size:28rpx; }
.photo-btn.rec { background: rgba(255,75,85,0.18); }
.photo-btn.rec text { color:#FF4B55; }
.voice-bubble {
	display:flex; flex-direction:row; align-items:center;
	background:#F0F0F0; border-radius:24rpx; padding:18rpx 28rpx; min-width:160rpx;
}
.msg.mine .voice-bubble { background: linear-gradient(90deg, #FD267A, #FF6036); }
.voice-ico { color:#111; font-size:24rpx; margin-right:12rpx; }
.msg.mine .voice-ico { color:#fff; }
.voice-dur { color:#333; font-size:26rpx; }
.msg.mine .voice-dur { color:#fff; }
.gif-mask {
	position:fixed; inset:0; background:rgba(0,0,0,0.45); z-index:1200;
	display:flex; flex-direction:column; justify-content:flex-end;
}
.gif-sheet {
	background:#fff; border-radius:32rpx 32rpx 0 0;
	padding: 32rpx 28rpx calc(env(safe-area-inset-bottom) + 32rpx);
	max-height: 80vh;
}
.gif-title { display:block; color:#111; font-size:32rpx; font-weight:700; margin-bottom:20rpx; }
.gif-search { width:100%; box-sizing:border-box; margin-bottom:16rpx; }
.gif-grid-wrap { max-height: 360rpx; margin-bottom: 16rpx; }
.gif-grid {
	display:flex; flex-direction:row; flex-wrap:wrap;
}
.gif-cell {
	width: 30%; margin: 1.5%; height: 160rpx; border-radius: 12rpx; background:#F3F0F7;
}
.gif-empty { display:block; color:#999; font-size:24rpx; margin-bottom:12rpx; text-align:center; }
.sticker-row { display:flex; flex-direction:row; flex-wrap:wrap; margin: 16rpx 0 24rpx; }
.sticker-row > view + view { margin-left: 12rpx; }
.sticker {
	width: 88rpx; height:88rpx; border-radius:16rpx; background:#FFF5F7;
	display:flex; align-items:center; justify-content:center;
	border: 1px solid rgba(253,38,122,0.15);
}
.sticker text { font-size:40rpx; }
.gif-sheet .btn {
	background: linear-gradient(90deg, #FD267A, #FF6036); border-radius:999rpx; padding:24rpx; text-align:center; margin-bottom:12rpx;
}
.gif-sheet .btn text { color:#fff; font-weight:700; }
.gif-sheet .link { text-align:center; }
.gif-sheet .link text { color:#666; }
.input {
	flex:1; background:#F3F0F7; border-radius:999rpx; padding:18rpx 28rpx; color:#111; margin-right:16rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.ph { color:#999; }
.send {
	background: linear-gradient(90deg, #FD267A, #FF6036); border-radius:999rpx; padding:18rpx 28rpx;
}
.send text { color:#fff; font-weight:700; }
</style>
