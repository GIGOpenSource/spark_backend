/**
 * Tab badges for Likes (index 1) and Chat (index 2).
 * Storage key unified across shells: spark_tab_badges
 * (legacy `tab_badges` is migrated on read).
 *
 * All Spark shells use custom tabBar (SparkTabBar) — native
 * setTabBarBadge / removeTabBarBadge are skipped; UI listens to
 * `tab_badges_updated` / storage.
 */
import { apiBadges } from '@/api/auth.js'

export const STORAGE_KEY = 'spark_tab_badges'
const LEGACY_KEY = 'tab_badges'
const THROTTLE_MS = 60 * 1000

let lastFetchAt = 0
let inFlight = null

export function getStoredTabBadges() {
	try {
		const cur = uni.getStorageSync(STORAGE_KEY)
		if (cur && typeof cur === 'object') {
			return { likes: Number(cur.likes) || 0, chat: Number(cur.chat) || 0 }
		}
		const legacy = uni.getStorageSync(LEGACY_KEY)
		if (legacy && typeof legacy === 'object') {
			const payload = { likes: Number(legacy.likes) || 0, chat: Number(legacy.chat) || 0 }
			try { uni.setStorageSync(STORAGE_KEY, payload) } catch (e) {}
			return payload
		}
	} catch (e) {}
	return { likes: 0, chat: 0 }
}

function persistBadges(likes, chat) {
	const payload = { likes: Number(likes) || 0, chat: Number(chat) || 0 }
	try {
		uni.setStorageSync(STORAGE_KEY, payload)
		uni.setStorageSync(LEGACY_KEY, payload) // keep legacy readers working during migrate
	} catch (e) {}
	try {
		uni.$emit && uni.$emit('tab_badges_updated', payload)
	} catch (e) {}
	return payload
}

function applyNativeBadges(/* likes, chat */) {
	// Custom tabBar: native APIs throw "not TabBar page" / uncaught promise rejects.
	// SparkTabBar consumes persistBadges → tab_badges_updated instead.
}

/**
 * @param {{ force?: boolean }} [opts] force=true bypasses ≥60s throttle (e.g. cold launch)
 */
export async function refreshTabBadges(opts = {}) {
	const force = !!(opts && opts.force)
	const now = Date.now()
	if (!force && lastFetchAt && now - lastFetchAt < THROTTLE_MS) {
		return getStoredTabBadges()
	}
	const token = uni.getStorageSync('token')
	if (!token) {
		lastFetchAt = now
		persistBadges(0, 0)
		applyNativeBadges(0, 0)
		return { likes: 0, chat: 0 }
	}
	if (inFlight) return inFlight
	lastFetchAt = now
	inFlight = (async () => {
		try {
			const res = await apiBadges()
			const data = (res && res.results) || {}
			const likes = Number(data.likes) || 0
			const chat = Number(data.chat_unread) || 0
			persistBadges(likes, chat)
			applyNativeBadges(likes, chat)
			return { likes, chat }
		} catch (e) {
			return getStoredTabBadges()
		} finally {
			inFlight = null
		}
	})()
	return inFlight
}
