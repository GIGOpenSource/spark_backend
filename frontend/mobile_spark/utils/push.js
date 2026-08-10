/**
 * Register uni-push clientId and handle click → deep link.
 */
import { apiRegisterPushToken, apiPushOpened } from '@/api/push.js'

function resolvePlatform() {
	try {
		const sys = uni.getSystemInfoSync()
		if (sys.uniPlatform === 'app' || sys.uniPlatform === 'app-plus') {
			return sys.platform === 'ios' ? 'ios' : 'android'
		}
	} catch (e) {}
	return 'h5'
}

export function registerPushToken() {
	const token = uni.getStorageSync('token')
	if (!token) return
	const platform = resolvePlatform()
	if (platform === 'h5') return
	try {
		if (typeof uni.getPushClientId !== 'function') return
		uni.getPushClientId({
			success: (res) => {
				const clientId = (res && (res.cid || res.clientid || res.clientId)) || ''
				if (!clientId) return
				apiRegisterPushToken({ client_id: clientId, platform, enabled: true }).catch(() => {})
			},
			fail: () => {}
		})
	} catch (e) {}
}

function navigateDeepLink(payload) {
	const link = (payload && (payload.deep_link || payload.deepLink)) || ''
	const eventType = payload && payload.event_type
	if (eventType === 'silent_recall') {
		apiPushOpened({ event_type: eventType, recall_day: payload.recall_day }).catch(() => {})
	}
	let url = link
	if (!url) {
		if (eventType === 'new_like') url = '/pages/likes/index'
		else if (eventType === 'new_match' || eventType === 'new_message') url = '/pages/chat/index'
		else url = '/pages/discover/index'
	}
	if (payload && payload.conversation_id && url.indexOf('chat') >= 0) {
		url = `/pagesA/chat/room?id=${payload.conversation_id}`
	}
	try {
		uni.navigateTo({
			url,
			fail: () => {
				uni.switchTab({ url: url.split('?')[0], fail: () => {} })
			}
		})
	} catch (e) {}
}

export function bindPushMessageHandler() {
	try {
		if (typeof uni.onPushMessage !== 'function') return
		uni.onPushMessage((res) => {
			const raw = (res && res.data) || res || {}
			const payload = raw.payload || raw.data || raw
			const type = (res && res.type) || raw.type
			if (type === 'click' || raw.type === 'click' || !type) {
				navigateDeepLink(typeof payload === 'string' ? { deep_link: payload } : payload)
			}
		})
	} catch (e) {}
}
