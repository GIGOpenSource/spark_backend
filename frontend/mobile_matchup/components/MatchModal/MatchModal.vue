<template>
	<view class="mask" v-if="show" @click="close">
		<view class="stage" @click.stop>
			<view class="confetti" aria-hidden="true">
				<view v-for="n in 18" :key="n" class="bit" :class="'b' + n" />
			</view>
			<text class="title">匹配成功</text>
			<view class="avatars">
				<view class="avatar-wrap me">
					<image v-if="meAvatar" :src="meAvatar" class="avatar" mode="aspectFill" />
					<view v-else class="avatar placeholder" />
				</view>
				<view class="heart-wrap">
					<text class="heart">♥</text>
				</view>
				<view class="avatar-wrap them">
					<image v-if="user && user.avatar_url" :src="user.avatar_url" class="avatar" mode="aspectFill" />
					<view class="online" v-if="user && user.is_online" />
				</view>
			</view>
			<text class="name">你和 {{ (user && user.nickname) || '' }}</text>
			<text class="sub" v-if="user && user.is_online">对方在线</text>
			<text class="hint" v-if="modeHint">{{ modeHint }}</text>
			<text class="err" v-if="sendError">{{ sendError }}</text>

			<!-- qa_gate: opener asks first; receiver waits -->
			<template v-if="isQaMode">
				<view v-if="canOpenQa" class="btn primary" @click="goAsk">
					<text>去提问开启聊天</text>
				</view>
				<view v-else class="btn" @click="chat">
					<text>查看匹配</text>
				</view>
			</template>

			<!-- women_first: only opener can send first message -->
			<template v-else-if="isWomenFirstMode">
				<template v-if="canSendOpen">
					<view class="starters">
						<view v-for="(s, i) in starters" :key="i" class="starter" @click="pickStarter(s)">
							<text>{{ s }}</text>
						</view>
					</view>
					<view class="composer">
						<input class="input" v-model="draft" placeholder="说点好听的…" placeholder-class="ph" confirm-type="send" @confirm="sendAndChat" />
						<view class="send" :class="{ busy: sending }" @click="sendAndChat"><text>{{ sending ? '…' : '发送' }}</text></view>
					</view>
				</template>
				<view class="btn" @click="chat"><text>打开聊天</text></view>
			</template>

			<!-- any / default -->
			<template v-else>
				<view class="starters">
					<view v-for="(s, i) in starters" :key="i" class="starter" @click="pickStarter(s)">
						<text>{{ s }}</text>
					</view>
				</view>
				<view class="composer">
					<input class="input" v-model="draft" placeholder="说点好听的…" placeholder-class="ph" confirm-type="send" @confirm="sendAndChat" />
					<view class="send" :class="{ busy: sending }" @click="sendAndChat"><text>{{ sending ? '…' : '发送' }}</text></view>
				</view>
				<view class="btn" @click="chat"><text>打开聊天</text></view>
			</template>

			<view class="link" @click="close"><text>继续滑卡</text></view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { apiOpenMessage } from '@/api/likes.js'
import { trackClick } from '@/utils/analytics.js'
import { isQaGate, isWomenFirst } from '@/utils/productProfile.js'

const props = defineProps({
	show: Boolean,
	user: { type: Object, default: null },
	matchId: { type: [Number, String], default: null },
	conversationId: { type: [Number, String], default: null },
	iAmOpener: { type: Boolean, default: null },
	expireAt: { type: String, default: '' },
	messagingMode: { type: String, default: '' },
})
const emit = defineEmits(['update:show', 'chat'])

const draft = ref('')
const sending = ref(false)
const sendError = ref('')
const starters = [
	'你好呀，看到你的资料很心动～',
	'周末一般喜欢做什么？',
	'有机会一起喝杯咖啡吗？',
]

const resolvedMode = computed(() => {
	if (props.messagingMode) return props.messagingMode
	if (isQaGate()) return 'qa_gate'
	if (isWomenFirst()) return 'women_first'
	return 'any'
})

const isQaMode = computed(() => resolvedMode.value === 'qa_gate')
const isWomenFirstMode = computed(() => resolvedMode.value === 'women_first')

const canOpenQa = computed(() => {
	if (!isQaMode.value) return false
	if (props.iAmOpener == null) return true
	return !!props.iAmOpener
})

const canSendOpen = computed(() => {
	if (isQaMode.value) return false
	if (!isWomenFirstMode.value) return true
	if (props.iAmOpener == null) return true
	return !!props.iAmOpener
})

const modeHint = computed(() => {
	if (isQaMode.value) {
		return canOpenQa.value
			? '匹配后需先提问，对方回答后你确认，才能自由聊天'
			: '等待对方提问，你回答后即可继续'
	}
	if (isWomenFirstMode.value && !canSendOpen.value) {
		return '等待对方先开口打招呼'
	}
	return ''
})

const meAvatar = computed(() => {
	const me = uni.getStorageSync('userInfo') || {}
	if (me.avatar_url) return me.avatar_url
	if (me.photos && me.photos.length) return me.photos[0].url
	return ''
})

watch(() => props.show, (v) => {
	if (v) {
		draft.value = ''
		sendError.value = ''
		try {
			uni.vibrateShort({ type: 'medium' })
		} catch (e) {
			try { uni.vibrateLong() } catch (e2) {}
		}
	}
})

function pickStarter(s) {
	draft.value = s
}

function close() {
	trackClick('match_keep_swiping')
	emit('update:show', false)
}
function chat(extra) {
	emit('chat', extra && typeof extra === 'object' ? extra : undefined)
}
function goAsk() {
	trackClick('match_go_ask')
	emit('chat', { focusAsk: true, focus: 'qa' })
}
async function sendAndChat() {
	if (!canSendOpen.value) {
		chat()
		return
	}
	if (sending.value) return
	trackClick('match_send')
	const text = draft.value.trim()
	if (!text) {
		chat()
		return
	}
	if (!props.matchId) {
		uni.setStorageSync('match_draft_message', text)
		chat()
		return
	}
	sending.value = true
	sendError.value = ''
	try {
		await apiOpenMessage(props.matchId, text)
		chat()
	} catch (e) {
		const msg = (e && e.message) || '发送失败'
		sendError.value = msg === 'not_opener' ? '需要对方先开口' : msg
		uni.showToast({ title: sendError.value, icon: 'none' })
	} finally {
		sending.value = false
	}
}
</script>

<style scoped>
.mask {
	position:fixed; inset:0; z-index:1100;
	background: linear-gradient(165deg, #2A1020 0%, #4A1830 40%, #FF6B9A 140%);
	display:flex; flex-direction:column; align-items:stretch; justify-content:flex-end;
}
.stage {
	position: relative; overflow: hidden;
	width: 100%; min-height: 100%;
	padding: calc(env(safe-area-inset-top) + 80rpx) 40rpx calc(env(safe-area-inset-bottom) + 48rpx);
	box-sizing: border-box;
	text-align:center;
	display:flex; flex-direction:column; justify-content:center;
	animation: stageIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes stageIn {
	0% { opacity: 0; }
	100% { opacity: 1; }
}
.confetti { position:absolute; inset:0; pointer-events:none; overflow:hidden; }
.bit {
	position:absolute; top:42%; left:50%; width:14rpx; height:14rpx; border-radius:3rpx;
	opacity: 0; animation: burst 1.05s ease-out forwards;
}
.b1 { background:#FF6B9A; --dx:-140rpx; --dy:-220rpx; animation-delay:0.02s; }
.b2 { background:#FF8FB3; --dx:130rpx; --dy:-200rpx; animation-delay:0.04s; }
.b3 { background:#FF6036; --dx:-200rpx; --dy:-60rpx; animation-delay:0.06s; }
.b4 { background:#fff; --dx:180rpx; --dy:-50rpx; animation-delay:0.05s; }
.b5 { background:#FFB4C8; --dx:-110rpx; --dy:160rpx; animation-delay:0.08s; }
.b6 { background:#FF8FB3; --dx:120rpx; --dy:170rpx; animation-delay:0.07s; }
.b7 { background:#FF6B9A; --dx:-60rpx; --dy:-280rpx; animation-delay:0.03s; }
.b8 { background:#fff; --dx:40rpx; --dy:-260rpx; animation-delay:0.09s; }
.b9 { background:#FF6036; --dx:-240rpx; --dy:40rpx; animation-delay:0.1s; }
.b10 { background:#FFB4C8; --dx:230rpx; --dy:30rpx; animation-delay:0.11s; }
.b11 { background:#FF6B9A; --dx:-30rpx; --dy:210rpx; animation-delay:0.12s; }
.b12 { background:#fff; --dx:70rpx; --dy:230rpx; animation-delay:0.13s; }
.b13 { background:#FF8FB3; --dx:-170rpx; --dy:-140rpx; animation-delay:0.04s; }
.b14 { background:#FF6036; --dx:160rpx; --dy:-130rpx; animation-delay:0.06s; }
.b15 { background:#FFB4C8; --dx:-90rpx; --dy:90rpx; animation-delay:0.08s; }
.b16 { background:#fff; --dx:100rpx; --dy:100rpx; animation-delay:0.1s; }
.b17 { background:#FF6B9A; --dx:0; --dy:-300rpx; animation-delay:0.01s; }
.b18 { background:#FF8FB3; --dx:-20rpx; --dy:260rpx; animation-delay:0.14s; }
@keyframes burst {
	0% { transform: translate(-50%,-50%) scale(0.4); opacity:0; }
	20% { opacity:1; }
	100% { transform: translate(calc(-50% + var(--dx)), calc(-50% + var(--dy))) scale(1); opacity:0; }
}
.title {
	display:block; color:#fff; font-size:64rpx; font-weight:800; letter-spacing:1rpx;
	margin-bottom:48rpx;
}
.avatars { display:flex; flex-direction:row; align-items:center; justify-content:center; margin-bottom:24rpx; }
.avatars > .avatar-wrap + .avatar-wrap, .avatars > .heart-wrap { margin-left: 8rpx; }
.avatar-wrap { position:relative; }
.avatar { width:180rpx; height:180rpx; border-radius:50%; border:6rpx solid rgba(255,255,255,0.35); }
.avatar.placeholder { background:rgba(255,255,255,0.15); display:block; }
.online {
	position:absolute; right:12rpx; bottom:12rpx; width:28rpx; height:28rpx;
	border-radius:50%; background:#3DDB7F; border:4rpx solid #2A1020;
}
.heart-wrap { width:64rpx; z-index:2; }
.heart { color:#fff; font-size:48rpx; }
.name { display:block; color:#fff; font-size:36rpx; font-weight:700; margin-bottom:8rpx; }
.sub { display:block; color:rgba(255,255,255,0.7); font-size:24rpx; margin-bottom:16rpx; }
.hint { display:block; color:rgba(255,255,255,0.85); font-size:26rpx; line-height:1.5; margin: 8rpx 24rpx 20rpx; }
.err { display:block; color:#FFB4C8; font-size:24rpx; margin-bottom:12rpx; }
.starters { display:flex; flex-direction:column; margin: 24rpx 0 20rpx; }
.starters .starter + .starter { margin-top: 12rpx; }
.starter {
	background:rgba(255,255,255,0.12); border-radius:999rpx; padding:18rpx 28rpx;
}
.starter text { color:#fff; font-size:26rpx; }
.composer {
	display:flex; flex-direction:row; align-items:center; 
	background:rgba(255,255,255,0.12); border-radius:999rpx; padding:8rpx 8rpx 8rpx 28rpx;
	margin-bottom:24rpx;
}
.composer > .send { margin-left: 12rpx; }
.input { flex:1; color:#fff; font-size:28rpx; height:72rpx; }
.ph { color:rgba(255,255,255,0.45); }
.send {
	background:#fff; border-radius:999rpx; padding:0 28rpx; height:72rpx;
	display:flex; align-items:center; justify-content:center;
}
.send.busy { opacity:0.6; }
.send text { color:#FF6B9A; font-size:26rpx; font-weight:700; }
.btn {
	background:rgba(255,255,255,0.18); border-radius:999rpx; height:96rpx;
	display:flex; align-items:center; justify-content:center; margin-bottom:16rpx;
}
.btn.primary { background:#fff; }
.btn text { color:#fff; font-size:30rpx; font-weight:700; }
.btn.primary text { color:#FF6B9A; }
.link text { color:rgba(255,255,255,0.75); font-size:26rpx; }
</style>
