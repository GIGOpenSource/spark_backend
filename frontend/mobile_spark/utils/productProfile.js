/**
 * Product rules from bootstrap.product_profile (shared backend, per-app isolation).
 */
export function getBootstrap() {
	return uni.getStorageSync('bootstrap') || {}
}

/** Offline defaults aligned with backend default_product_profile(spark_main). */
export const OFFLINE_PRODUCT_PROFILE = {
	messaging_mode: 'any',
	match_open_hours: null,
	extend_enabled: false,
	compliment_enabled: false,
	feed_same_app_only: true,
	display_tiers: { plus: 'Plus', gold: 'Gold', platinum: 'Platinum' },
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

export function superLikeLabel() {
	if (isComplimentEnabled()) return 'Compliment'
	return 'Super Like'
}

export function boostLabel() {
	return 'Boost'
}
