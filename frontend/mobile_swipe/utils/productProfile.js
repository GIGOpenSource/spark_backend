/**
 * Product rules from bootstrap.product_profile (shared backend, per-app isolation).
 */
export function getBootstrap() {
	return uni.getStorageSync('bootstrap') || {}
}

/** Offline defaults aligned with backend default_product_profile(swipe_main). */
export const OFFLINE_PRODUCT_PROFILE = {
	messaging_mode: 'women_first',
	match_open_hours: 24,
	extend_enabled: true,
	compliment_enabled: true,
	feed_same_app_only: true,
	display_tiers: {
		plus: 'Premium',
		gold: 'Premium+',
		platinum: 'Premium+ Spotlight',
	},
}

export function getProductProfile() {
	const boot = getBootstrap()
	return boot.product_profile || { ...OFFLINE_PRODUCT_PROFILE }
}

export function tierDisplayName(tier) {
	const map = getProductProfile().display_tiers || {}
	if (!tier || tier === 'none') return 'Free'
	return map[tier] || tier
}

export function isWomenFirst() {
	return getProductProfile().messaging_mode === 'women_first'
}

export function isQaGate() {
	return getProductProfile().messaging_mode === 'qa_gate'
}

export function isExtendEnabled() {
	return !!getProductProfile().extend_enabled
}

export function isComplimentEnabled() {
	return !!getProductProfile().compliment_enabled
}

export function matchOpenHours() {
	const h = getProductProfile().match_open_hours
	return h == null ? null : Number(h)
}

/** Remaining ratio 0..1 until ISO expire_at. */
export function expireProgress(expireAtIso, nowMs, totalHours) {
	if (!expireAtIso) return 0
	const end = new Date(expireAtIso).getTime()
	const now = nowMs || Date.now()
	const left = end - now
	if (left <= 0) return 0
	const hours = Number(totalHours || matchOpenHours() || 24)
	const totalMs = Math.max(hours, 1) * 3600 * 1000
	return Math.min(1, Math.max(0, left / totalMs))
}

/** Format remaining time until ISO expire_at. Returns '' if none. */
export function formatExpireCountdown(expireAtIso, nowMs) {
	if (!expireAtIso) return ''
	const end = new Date(expireAtIso).getTime()
	const now = nowMs || Date.now()
	const diff = end - now
	if (diff <= 0) return '0:00'
	const totalSec = Math.floor(diff / 1000)
	const h = Math.floor(totalSec / 3600)
	const m = Math.floor((totalSec % 3600) / 60)
	const s = totalSec % 60
	if (h > 0) {
		return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
	}
	return `${m}:${String(s).padStart(2, '0')}`
}

export function formatBoostCountdown(endAtIso, nowMs) {
	return formatExpireCountdown(endAtIso, nowMs)
}

export function superLikeLabel() {
	if (isComplimentEnabled()) return 'Compliment'
	return 'Super Like'
}

export function boostLabel() {
	return 'Spotlight'
}

export const DATING_MODES = [
	{ id: 'date', label: 'Date', hint: 'Dating' },
	{ id: 'bff', label: 'BFF', hint: 'Friends' },
	{ id: 'bizz', label: 'Bizz', hint: 'Networking' },
]

export function getDatingMode() {
	const stored = uni.getStorageSync('dating_mode')
	if (stored && ['date', 'bff', 'bizz'].includes(stored)) return stored
	const me = uni.getStorageSync('userInfo') || {}
	const mode = (me.lifestyle && me.lifestyle.dating_mode) || 'date'
	return ['date', 'bff', 'bizz'].includes(mode) ? mode : 'date'
}

export function setDatingMode(mode) {
	const m = ['date', 'bff', 'bizz'].includes(mode) ? mode : 'date'
	uni.setStorageSync('dating_mode', m)
	return m
}

/** Built-in badge catalog (separate from Interests). */
export const BADGE_CATALOG = [
	{ id: 'verified', label: 'Verified', auto: true },
	{ id: 'active', label: 'Recently active', auto: true },
	{ id: 'traveler', label: 'Traveler', auto: false },
	{ id: 'foodie', label: 'Foodie', auto: false },
	{ id: 'night_owl', label: 'Night owl', auto: false },
	{ id: 'early_bird', label: 'Early bird', auto: false },
	{ id: 'pet_parent', label: 'Pet parent', auto: false },
	{ id: 'fitness', label: 'Fitness', auto: false },
	{ id: 'creative', label: 'Creative', auto: false },
	{ id: 'ambitious', label: 'Ambitious', auto: false },
]

export function resolveBadges(user) {
	if (!user) return []
	const life = user.lifestyle || {}
	const chosen = Array.isArray(life.badges) ? life.badges : []
	const out = []
	if (user.is_verified) out.push({ id: 'verified', label: 'Verified' })
	if (user.is_online) out.push({ id: 'active', label: 'Recently active' })
	chosen.forEach((id) => {
		const hit = BADGE_CATALOG.find((b) => b.id === id)
		if (hit && !out.some((x) => x.id === hit.id)) out.push({ id: hit.id, label: hit.label })
	})
	return out
}
