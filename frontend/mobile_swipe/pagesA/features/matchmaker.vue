<template>
	<view class="page">
		<view class="header"><text class="back" @click="back">‹</text><text class="title">Matchmaker</text></view>
		<text class="sub">Introduce two friends — both must accept</text>
		<input class="input" v-model="userA" type="number" placeholder="User A id" />
		<input class="input" v-model="userB" type="number" placeholder="User B id" />
		<input class="input" v-model="message" placeholder="Optional note" />
		<view class="btn" @click="invite"><text>Send invite</text></view>
		<text class="sec">Inbox</text>
		<view v-for="row in inbox" :key="row.id" class="row">
			<text class="body">#{{ row.id }} · {{ row.message || 'Invite' }}</text>
			<view class="actions">
				<text class="ok" @click="respond(row, true)">Accept</text>
				<text class="no" @click="respond(row, false)">Decline</text>
			</view>
		</view>
		<view v-if="!inbox.length" class="empty"><text>No invites yet</text></view>
	</view>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { apiMatchmakerInvite, apiMatchmakerInbox, apiMatchmakerRespond } from '@/api/matchmaker.js'
const userA = ref('')
const userB = ref('')
const message = ref('')
const inbox = ref([])
function back() { uni.navigateBack() }
async function load() {
	try {
		const res = await apiMatchmakerInbox()
		inbox.value = (res.results && res.results.list) || []
	} catch (e) { inbox.value = [] }
}
async function invite() {
	try {
		await apiMatchmakerInvite({ user_a_id: Number(userA.value), user_b_id: Number(userB.value), message: message.value })
		uni.showToast({ title: 'Sent', icon: 'none' })
		load()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' })
	}
}
async function respond(row, accept) {
	try {
		await apiMatchmakerRespond(row.id, accept)
		uni.showToast({ title: accept ? 'Accepted' : 'Declined', icon: 'none' })
		load()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Failed', icon: 'none' })
	}
}
onMounted(load)
</script>
<style scoped>
.page { min-height:100vh; background:var(--bg,#fff); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; }
.header { display:flex; align-items:center; margin-bottom:12rpx; }
.back { font-size:48rpx; width:60rpx; }
.title { font-size:40rpx; font-weight:700; }
.sub,.sec { display:block; color:var(--muted,#666); margin: 16rpx 0; }
.input { background:var(--surface,#f8f8f8); padding:20rpx; border-radius:12rpx; margin-bottom:12rpx; }
.btn { background:#FF4458; padding:24rpx; border-radius:999rpx; text-align:center; margin: 12rpx 0 24rpx; }
.btn text { color:#fff; font-weight:700; }
.row { padding:20rpx 0; border-bottom:1px solid var(--border,rgba(0,0,0,.06)); }
.actions { display:flex; margin-top:8rpx; }
.actions > view + view, .actions > button + button { margin-left: 24rpx; }
.ok { color:#3DDB7F; } .no { color:#FF4458; }
.empty { color:var(--muted,#666); }
</style>
