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
			<text class="call-btn" @click="startCall">📹</text>
			<text class="more" @click="more">⋯</text>
		</view>

		<view class="typing-banner" v-if="peerTyping && !matchLocked">
			<text>{{ peer.nickname || 'They' }} {{ $t('chat.typing') }}</text>
		</view>

		<view class="expired-banner" v-if="matchLocked || waitingForOpener || showOpenTimer">
			<text>{{ bannerPrimary }}</text>
			<view v-if="canExtend && iAmOpener && !matchLocked" class="rematch-btn" @click="doExtend">
				<text>{{ extendLabel }}</text>
			</view>
			<text v-if="canExtend && iAmOpener && !matchLocked" class="extend-hint">{{ extendHint }}</text>
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
				<text class="mh-sub">{{ heroSub }}</text>
			</view>
			<view v-if="!messages.length && !waitingForOpener" class="starters">
				<text class="starters-title">{{ iAmOpener ? 'Move first — say hello' : 'Say something nice' }}</text>
				<view v-for="(s, i) in starters" :key="i" class="starter" @click="quickSend(s)">
					<text>{{ s }}</text>
				</view>
			</view>
			<view v-if="waitingForOpener && !messages.length" class="starters">
				<text class="starters-title">{{ waitingBannerText }}</text>
			</view>
			<view v-for="m in messages" :key="m.id" :id="'m'+m.id" class="msg" :class="{ mine: m.sender_id === myId }">
				<image
					v-if="m.msg_type === 'image' || m.msg_type === 'photo' || m.msg_type === 'gif'"
					:src="m.content"
					class="img-bubble"
					mode="widthFix"
					@click="preview(m.content)"
					@longpress="saveImage(m.content)"
				/>
				<view v-else-if="m.msg_type === 'voice' || m.msg_type === 'audio'" class="voice-bubble" @click="playVoice(m)">
					<text class="voice-ico">{{ playingId === m.id ? '▌▌' : '▶' }}</text>
					<text class="voice-dur">{{ formatDur(m.duration_ms) }}</text>
				</view>
				<template v-else>
					<text class="bubble">{{ showOriginal[m.id] ? m.content : (m.translated || m.content) }}</text>
					<text
						v-if="m.translated && !showOriginal[m.id]"
						class="tr-btn"
						@click="toggleOriginal(m)"
					>Original</text>
					<text
						v-else-if="m.msg_type === 'text' || !m.msg_type"
						class="tr-btn"
						@click="translate(m)"
					>{{ translating[m.id] ? '…' : 'Translate' }}</text>
				</template>
				<text v-if="m.sender_id === myId" class="receipt">{{ receiptMark(m) }}</text>
			</view>
		</scroll-view>

		<view class="composer" v-if="!matchLocked && !waitingForOpener">
			<view class="photo-btn" @click="pickPhoto"><text>＋</text></view>
			<view class="photo-btn" @click="toggleRecord"><text>{{ recording ? '■' : '🎙' }}</text></view>
			<view class="photo-btn" @click="pickGif"><text>GIF</text></view>
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
		<view class="gif-sheet" v-if="showGif">
			<input
				class="gif-input"
				v-model="gifQuery"
				:placeholder="$t('chat.gifSearch')"
				placeholder-class="ph"
				confirm-type="search"
				@confirm="searchGifs"
			/>
			<view class="gif-actions">
				<view class="gif-btn" @click="searchGifs"><text>{{ $t('chat.search') }}</text></view>
				<view class="gif-btn ghost" @click="showGif = false"><text>{{ $t('common.cancel') }}</text></view>
			</view>
			<scroll-view scroll-y class="gif-grid" v-if="gifResults.length">
				<view class="gif-grid-inner">
					<image
						v-for="(g, i) in gifResults"
						:key="g.id || g.url || i"
						:src="g.preview || g.url"
						class="gif-thumb"
						mode="aspectFill"
						@click="sendGifUrl(g.url || g.preview)"
					/>
				</view>
			</scroll-view>
			<input class="gif-input" v-model="gifUrl" placeholder="Paste GIF / Tenor / Giphy URL" placeholder-class="ph" />
			<view class="gif-actions">
				<view class="gif-btn" @click="sendGif"><text>Send GIF</text></view>
			</view>
		</view>
		<VipSheet v-model:show="showVip" :reason="vipReason" @purchased="onPurchased" />
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

const cid = ref(null)
const matchId = ref(null)
const MSG_DOM_CAP = 200 // F-07: cap DOM messages to last N
const messages = ref([])
const peer = ref({})
const text = ref('')
const myId = ref((uni.getStorageSync('userInfo') || {}).id)
const scrollInto = ref('')
const showVip = ref(false)
const vipReason = ref('need_platinum')
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
const recording = ref(false)
const showGif = ref(false)
const gifUrl = ref('')
const gifQuery = ref('')
const gifResults = ref([])
const peerTyping = ref(false)
const playingId = ref(null)
let countdownTimer = null
let recorder = null
let recordStartedAt = 0
let audioCtx = null
let typingTimer = null
let typingStopTimer = null
let h5MediaRecorder = null
let h5Chunks = []
let peerTypingHideTimer = null
const translating = reactive({})
const showOriginal = reactive({})
const REPORT_REASONS = [
	{ key: 'spam', label: 'Spam' },
	{ key: 'harassment', label: 'Harassment' },
	{ key: 'inappropriate', label: 'Inappropriate' },
	{ key: 'fake', label: 'Fake profile' },
	{ key: 'underage', label: 'Underage' },
	{ key: 'other', label: 'Other' },
]
const starters = computed(() => {
	const life = (peer.value && peer.value.lifestyle) || {}
	const moves = Array.isArray(life.opening_moves) ? life.opening_moves.filter(Boolean) : []
	if (moves.length) return moves.slice(0, 3)
	return [
		'Hey! Loved your photos ✨',
		'Coffee or museum this weekend?',
		'What are you into lately?'
	]
})
let socketTask = null

const meAvatar = computed(() => {
	const me = uni.getStorageSync('userInfo') || {}
	if (me.avatar_url) return me.avatar_url
	if (me.photos && me.photos.length) return me.photos[0].url
	return ''
})

const heroSub = computed(() => {
	if (iAmOpener.value && showOpenTimer.value && countdown.value) {
		return `Move first — you have ${countdown.value}`
	}
	if (peer.value && peer.value.is_online) return 'Online now — say something nice'
	return 'Say something nice'
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
	return left ? `You move first · ${left} left` : 'You move first — 24h window'
})

const bannerPrimary = computed(() => {
	if (matchLocked.value) return lockedBannerText.value
	if (waitingForOpener.value) return waitingBannerText.value
	if (showOpenTimer.value && iAmOpener.value) return openerTimerText.value
	if (showOpenTimer.value) return waitingBannerText.value
	return ''
})

const lockedBannerText = computed(() => {
	if (sayHiExpired.value) return 'This Say Hi has expired'
	if (matchStatus.value === 'expired') return 'Match expired — Extend or Rematch available'
	return 'This match has ended'
})

const extendFreeLeft = ref(1)
const extendPaidLeft = ref(0)
const extendLabel = computed(() => (extendFreeLeft.value > 0 ? 'Free Extend 24h' : 'Extend 24h'))
const extendHint = computed(() => (
	extendFreeLeft.value > 0
		? 'One free Extend — another day to make the first move'
		: (extendPaidLeft.value > 0 ? `${extendPaidLeft.value} paid Extends left` : 'Buy an Extend pack for another 24h')
))
const likeAgainLabel = computed(() => 'Rematch')

const statusText = computed(() => {
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
	return peer.value.is_online ? (zh.value ? '在线' : 'Online') : (zh.value ? '最近活跃' : 'Recently active')
})

const composerHint = computed(() => {
	if (matchLocked.value) return zh.value ? '暂无法聊天' : 'Chat unavailable'
	if (waitingForOpener.value) return waitingBannerText.value
	if (blurPeer.value && freeRepliesLeft.value === 0) return 'Upgrade Platinum to keep chatting'
	return zh.value ? '发消息' : 'Message'
})

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
	if (typingTimer) clearTimeout(typingTimer)
	if (typingStopTimer) clearTimeout(typingStopTimer)
	if (peerTypingHideTimer) clearTimeout(peerTypingHideTimer)
	try {
		if (socketTask && socketTask.close) socketTask.close()
	} catch (e) {}
	try {
		if (audioCtx) audioCtx.destroy()
	} catch (e) {}
	try {
		if (h5MediaRecorder && h5MediaRecorder.state !== 'inactive') h5MediaRecorder.stop()
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
		extendFreeLeft.value = data.extend_free_left != null ? Number(data.extend_free_left) : Math.max(0, 1 - Number(data.extend_count || 0))
		extendPaidLeft.value = Number(data.extend_paid_left || 0)
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
		extendFreeLeft.value = data.extend_free_left != null ? Number(data.extend_free_left) : extendFreeLeft.value
		extendPaidLeft.value = Number(data.extend_paid_left || 0)
		tickCountdown()
		uni.showToast({ title: 'Extended +24h', icon: 'none' })
	} catch (e) {
		const msg = (e && e.message) || ''
		if (/need_extend|extend_limit|vip|purchase|extend/.test(msg) || (e && e.results && e.results.need_shop)) {
			vipReason.value = 'need_extend'
			showVip.value = true
		}
		uni.showToast({ title: msg || 'Extend failed', icon: 'none' })
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
					} else if (payload.type === 'typing') {
						if (Number(payload.user_id) !== Number(myId.value)) {
							peerTyping.value = !!payload.is_typing
							if (peerTypingHideTimer) clearTimeout(peerTypingHideTimer)
							if (payload.is_typing) {
								peerTypingHideTimer = setTimeout(() => { peerTyping.value = false }, 3000)
							}
						}
					} else if (payload.type === 'delivered' || payload.type === 'read') {
						const ids = payload.message_ids || payload.ids || []
						messages.value = messages.value.map((m) => {
							if (!ids.length || ids.includes(m.id)) {
								const next = { ...m }
								if (payload.type === 'delivered') {
									next.delivered_at = next.delivered_at || new Date().toISOString()
								}
								if (payload.type === 'read') {
									next.read_at = next.read_at || new Date().toISOString()
									next.is_read = true
								}
								return next
							}
							return m
						})
					} else if (payload.type === 'call_invite' && Number(payload.from_user_id) !== Number(myId.value)) {
						uni.showModal({
							title: 'Incoming call',
							content: `${peer.value.nickname || 'Match'} is calling`,
							success: (m) => {
								if (m.confirm) startCall()
							},
						})
					}
				} catch (e) {}
			})
		}
		if (socketTask && typeof socketTask.onClose === 'function') {
			socketTask.onClose(() => { socketTask = null })
		}
	} catch (e) {}
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
		itemList: ['Save image'],
		success: () => {
			// #ifdef APP-PLUS || MP
			uni.downloadFile({
				url,
				success: (r) => {
					uni.saveImageToPhotosAlbum({
						filePath: r.tempFilePath,
						success: () => uni.showToast({ title: 'Saved', icon: 'none' }),
						fail: () => uni.showToast({ title: 'Save failed', icon: 'none' }),
					})
				},
			})
			// #endif
			// #ifdef H5
			uni.setClipboardData({ data: url })
			uni.showToast({ title: 'URL copied', icon: 'none' })
			// #endif
		},
	})
}

function formatDur(ms) {
	const s = Math.max(1, Math.round((Number(ms) || 0) / 1000))
	const m = Math.floor(s / 60)
	const r = s % 60
	return m > 0 ? `${m}:${String(r).padStart(2, '0')}` : `0:${String(r).padStart(2, '0')}`
}

function receiptMark(m) {
	if (!m) return ''
	if (m.read_at || m.is_read) return '✓✓'
	if (m.delivered_at) return '✓✓'
	return '✓'
}

function sendTyping(isTyping) {
	try {
		if (socketTask && typeof socketTask.send === 'function') {
			socketTask.send({
				data: JSON.stringify({ type: 'typing', is_typing: !!isTyping }),
			})
		}
	} catch (e) {}
}

function onTypingInput() {
	if (typingTimer) return
	sendTyping(true)
	typingTimer = setTimeout(() => { typingTimer = null }, 1200)
	if (typingStopTimer) clearTimeout(typingStopTimer)
	typingStopTimer = setTimeout(() => sendTyping(false), 2500)
}

function startCall() {
	if (!cid.value) return
	trackClick('start_call')
	const name = encodeURIComponent(peer.value.nickname || '')
	const avatar = encodeURIComponent(peer.value.avatar_url || '')
	uni.navigateTo({ url: `/pagesA/chat/call?cid=${cid.value}&name=${name}&avatar=${avatar}` })
}

async function uploadVoiceBlob(blob, durationMs) {
	uni.showLoading({ title: 'Sending…' })
	try {
		const form = new FormData()
		form.append('file', blob, 'voice.webm')
		form.append('kind', 'voice')
		form.append('duration_ms', String(durationMs))
		const token = uni.getStorageSync('token') || ''
		const resp = await fetch(host + '/chat/upload/?kind=voice', {
			method: 'POST',
			headers: {
				token,
				'is-dev': 'true',
				'Accept-Language': uni.getStorageSync('currentLanguage') || 'zh',
			},
			body: form,
		})
		const body = await resp.json()
		const url = body.results && body.results.url
		if (!url) {
			uni.showToast({ title: 'upload failed', icon: 'none' })
			return
		}
		const msgRes = await apiSendMessage(cid.value, {
			content: url,
			msg_type: 'voice',
			duration_ms: durationMs,
		})
		appendMsg(msgRes.results)
	} catch (e) {
		uni.showToast({ title: 'send failed', icon: 'none' })
	} finally {
		uni.hideLoading()
	}
}

async function toggleRecordH5() {
	// #ifdef H5
	try {
		if (recording.value && h5MediaRecorder) {
			h5MediaRecorder.stop()
			return
		}
		if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
			uni.showToast({ title: 'Mic unavailable', icon: 'none' })
			return false
		}
		const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
		h5Chunks = []
		h5MediaRecorder = new MediaRecorder(stream)
		h5MediaRecorder.ondataavailable = (e) => {
			if (e.data && e.data.size) h5Chunks.push(e.data)
		}
		h5MediaRecorder.onstop = async () => {
			recording.value = false
			stream.getTracks().forEach((t) => t.stop())
			const blob = new Blob(h5Chunks, { type: 'audio/webm' })
			const durationMs = Math.round(Date.now() - recordStartedAt)
			await uploadVoiceBlob(blob, durationMs)
			h5MediaRecorder = null
			h5Chunks = []
		}
		recordStartedAt = Date.now()
		recording.value = true
		h5MediaRecorder.start()
		uni.showToast({ title: 'Recording… tap again to send', icon: 'none' })
		return true
	} catch (e) {
		uni.showToast({ title: 'Mic permission denied', icon: 'none' })
		return false
	}
	// #endif
	return false
}

function ensureRecorder() {
	if (recorder) return recorder
	recorder = uni.getRecorderManager && uni.getRecorderManager()
	if (!recorder) return null
	recorder.onStop(async (res) => {
		recording.value = false
		const path = res && res.tempFilePath
		const durationMs = Math.round((Date.now() - recordStartedAt) || (res.duration || 0))
		if (!path) return
		uni.showLoading({ title: 'Sending…' })
		uploadFile({
			url: '/chat/upload/?kind=voice',
			filePath: path,
			formData: { kind: 'voice', duration_ms: String(durationMs) },
		}).then(async (body) => {
			const url = body.results && body.results.url
			if (!url) {
				uni.showToast({ title: 'upload failed', icon: 'none' })
				return
			}
			const msgRes = await apiSendMessage(cid.value, {
				content: url,
				msg_type: 'voice',
				duration_ms: durationMs,
			})
			appendMsg(msgRes.results)
		}).catch(() => {
			uni.showToast({ title: 'network error', icon: 'none' })
		}).finally(() => uni.hideLoading())
	})
	recorder.onError(() => {
		recording.value = false
		uni.showToast({ title: 'Recorder error', icon: 'none' })
	})
	return recorder
}

async function toggleRecord() {
	// Prefer H5 MediaRecorder when available
	// #ifdef H5
	const handled = await toggleRecordH5()
	if (handled) return
	// #endif
	const r = ensureRecorder()
	if (!r) {
		uni.showToast({ title: 'Voice needs native recorder', icon: 'none' })
		return
	}
	if (recording.value) {
		r.stop()
		return
	}
	recording.value = true
	recordStartedAt = Date.now()
	r.start({ format: 'mp3', duration: 60000 })
	uni.showToast({ title: 'Recording… tap again to send', icon: 'none' })
}

function playVoice(m) {
	if (!m || !m.content) return
	if (!audioCtx) audioCtx = uni.createInnerAudioContext()
	if (playingId.value === m.id) {
		audioCtx.stop()
		playingId.value = null
		return
	}
	audioCtx.src = m.content
	playingId.value = m.id
	audioCtx.onEnded(() => { playingId.value = null })
	audioCtx.play()
}

function pickGif() {
	showGif.value = true
	gifUrl.value = ''
	gifQuery.value = gifQuery.value || 'hello'
	if (!gifResults.value.length) searchGifs()
}

async function searchGifs() {
	const q = (gifQuery.value || '').trim() || 'hello'
	try {
		const res = await apiSearchGifs(q, 24)
		gifResults.value = (res.results && res.results.list) || []
		if (!gifResults.value.length) {
			uni.showToast({ title: 'No GIFs found', icon: 'none' })
		}
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'GIF search failed', icon: 'none' })
	}
}

async function sendGifUrl(url) {
	if (!url) return
	try {
		const res = await apiSendMessage(cid.value, { content: url, msg_type: 'gif' })
		appendMsg(res.results)
		showGif.value = false
	} catch (e) {
		try {
			const res = await apiSendMessage(cid.value, { content: url, msg_type: 'image' })
			appendMsg(res.results)
			showGif.value = false
		} catch (e2) {
			uni.showToast({ title: (e2 && e2.message) || 'GIF failed', icon: 'none' })
		}
	}
}

async function sendGif() {
	const url = (gifUrl.value || '').trim()
	if (!url) {
		uni.showToast({ title: 'Paste a GIF URL', icon: 'none' })
		return
	}
	await sendGifUrl(url)
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
		uni.showToast({ title: 'Rematch sent', icon: 'none' })
		uni.switchTab({ url: '/pages/discover/index' })
	} catch (e) {
		const msg = (e && e.message) || ''
		if (/need_rematch|rematch/.test(msg)) {
			vipReason.value = 'need_rematch'
			showVip.value = true
			return
		}
		if (e && (e.message === 'daily_like_limit' || (e.results && e.results.need_vip))) {
			vipReason.value = msg || 'need_vip'
			showVip.value = true
		} else {
			uni.showToast({ title: msg || 'Rematch failed', icon: 'none' })
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
			if (!reason) return
			try {
				await apiReport({ user_id: peer.value.id, reason: reason.key })
				uni.showToast({ title: 'Reported', icon: 'none' })
			} catch (e) {
				uni.showToast({ title: (e && e.message) || 'Report failed', icon: 'none' })
			}
		},
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
.page { height:100vh; background:#FFFDF6; display:flex; flex-direction:column; }
.nav {
	padding: calc(env(safe-area-inset-top) + 12rpx) 24rpx 16rpx;
	display:flex; flex-direction:row; align-items:center;
	background:#fff;
	border-bottom: 1px solid rgba(255,198,41,0.25);
}
.back { color:#111; font-size:48rpx; width:60rpx; }
.peer { flex:1; display:flex; flex-direction:row; align-items:center; }
.nav-avatar-wrap { position:relative; margin-right:16rpx; }
.nav-avatar { width:64rpx; height:64rpx; border-radius:50%; }
.nav-avatar.blur { filter: blur(8px); }
.online {
	position:absolute; right:0; bottom:0; width:16rpx; height:16rpx;
	border-radius:50%; background:#22C55E; border:3rpx solid #fff;
}
.title { display:block; color:#111; font-size:30rpx; font-weight:700; }
.status { display:block; color:#888; font-size:20rpx; }
.more { color:#111; font-size:40rpx; width:60rpx; text-align:right; }
.call-btn { color:#111; font-size:32rpx; width:56rpx; text-align:center; margin-right:4rpx; }
.typing-banner {
	background: rgba(255,198,41,0.12);
	padding: 10rpx 24rpx;
}
.typing-banner text { color:#8A6D00; font-size:22rpx; }
.receipt { color:#999; font-size:18rpx; margin-top:4rpx; }
.msg.mine .receipt { color:#B8860B; }
.gif-grid { max-height: 360rpx; margin-bottom: 12rpx; }
.gif-grid-inner { display:flex; flex-direction:row; flex-wrap:wrap; }
.gif-thumb {
	width: 31%; margin: 1%; height: 160rpx; border-radius: 12rpx; background:#eee;
}
.expired-banner {
	background: rgba(255,198,41,0.2);
	border-bottom: 1px solid rgba(255,198,41,0.45);
	padding: 16rpx 24rpx;
	display:flex; flex-direction:column; align-items:center; justify-content:center;
}
.expired-banner text { color:#8A6D00; font-size:24rpx; }
.extend-hint { display:block; color:#B8860B; font-size:20rpx; margin-top:8rpx; }
.rematch-btn {
	margin-top: 12rpx; width: 100%; box-sizing: border-box;
	padding: 14rpx 18rpx; border-radius: 999rpx; background: #FFC629; text-align: center;
}
.rematch-btn text { color:#111; font-size:24rpx; font-weight:700; }
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
	border: 4rpx solid #FFFDF6; margin: 0 -10rpx;
}
.mh-av.ph { background: #FFF8E1; }
.mh-title { display:block; color:#111; font-size:32rpx; font-weight:800; margin-bottom:8rpx; }
.mh-sub { display:block; color:#8A6D00; font-size:24rpx; }
.starters { padding: 24rpx 0 40rpx; }
.starters-title { display:block; color:#B8860B; font-size:24rpx; font-weight:700; margin-bottom:16rpx; text-align:center; }
.starter {
	background:#FFF8E1; border-radius:999rpx; padding:18rpx 28rpx; margin-bottom:12rpx; text-align:center;
	border: 1px solid rgba(255,198,41,0.35);
}
.starter text { color:#333; font-size:26rpx; }
.msg { margin-bottom:16rpx; display:flex; flex-direction:column; align-items:flex-start; }
.msg.mine { align-items:flex-end; }
.bubble {
	background:#fff; color:#111; padding:18rpx 24rpx; border-radius:24rpx; max-width:75%; font-size:28rpx;
	border: 1px solid rgba(0,0,0,0.06);
}
.msg.mine .bubble { background:#FFC629; border-color:#FFC629; }
.img-bubble {
	max-width: 70%; border-radius: 20rpx; overflow: hidden;
}
.voice-bubble {
	display:flex; flex-direction:row; align-items:center;
	background:#fff; border-radius:999rpx; padding:16rpx 24rpx;
	border: 1px solid rgba(255,198,41,0.45); min-width: 180rpx;
}
.msg.mine .voice-bubble { background:#FFC629; border-color:#FFC629; }
.voice-ico { color:#111; font-size:24rpx; margin-right:12rpx; }
.voice-dur { color:#111; font-size:24rpx; font-weight:600; }
.tr-btn { color:#6ea8fe; font-size:22rpx; margin-top:4rpx; }
.composer {
	display:flex; flex-direction:row; align-items:center;
	padding:16rpx 24rpx calc(env(safe-area-inset-bottom) + 16rpx);
	background:#fff;
	border-top: 1px solid rgba(255,198,41,0.2);
}
.composer.locked { opacity: 0.7; }
.photo-btn {
	width:64rpx; height:64rpx; border-radius:50%; background:#FFF8E1;
	display:flex; align-items:center; justify-content:center; margin-right:10rpx;
}
.photo-btn text { color:#B8860B; font-size:22rpx; font-weight:700; }
.input {
	flex:1; background:#FFF8E1; border-radius:999rpx; padding:18rpx 28rpx; color:#111; margin-right:16rpx;
	border: 1px solid rgba(255,198,41,0.35);
}
.ph { color:#999; }
.send {
	background:#FFC629; border-radius:999rpx; padding:18rpx 28rpx;
}
.send text { color:#111; font-weight:800; }
.gif-sheet {
	position: fixed; left:0; right:0; bottom:0; z-index: 50;
	background:#fff; padding: 24rpx 24rpx calc(env(safe-area-inset-bottom) + 24rpx);
	border-top: 1px solid rgba(255,198,41,0.35);
}
.gif-input {
	background:#FFF8E1; border-radius:16rpx; padding:20rpx; margin-bottom:16rpx;
	border: 1px solid rgba(255,198,41,0.35); color:#111;
}
.gif-actions { display:flex; flex-direction:row; }
.gif-btn {
	flex:1; background:#FFC629; border-radius:999rpx; padding:20rpx; text-align:center; margin-right:12rpx;
}
.gif-btn.ghost { background:#FFF8E1; margin-right:0; }
.gif-btn text { color:#111; font-weight:700; }
</style>
