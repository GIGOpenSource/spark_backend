/**
 * Product rules from bootstrap.product_profile (shared backend, per-app isolation).
 */
export function getBootstrap() {
	return uni.getStorageSync('bootstrap') || {}
}

/** Offline defaults aligned with backend default_product_profile(matchup_main). */
export const OFFLINE_PRODUCT_PROFILE = {
	messaging_mode: 'qa_gate',
	match_open_hours: 48,
	extend_enabled: false,
	compliment_enabled: false,
	qa_gate_enabled: true,
	daily_feed_cap: 21,
	daily_feed_vip_bonus: { plus: 5, gold: 10, platinum: 21 },
	feed_same_app_only: true,
	display_tiers: { plus: '会员', gold: '高级会员', platinum: '至尊会员' },
}

export function getProductProfile() {
	const boot = getBootstrap()
	return boot.product_profile || { ...OFFLINE_PRODUCT_PROFILE }
}

export function tierDisplayName(tier) {
	const map = getProductProfile().display_tiers || {}
	if (!tier || tier === 'none') return '免费'
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

/** Remaining fraction 0–1 for expiry ring (uses match_open_hours when created_at unknown). */
export function expireProgress(expireAtIso, nowMs, totalHours) {
	if (!expireAtIso) return 0
	const end = new Date(expireAtIso).getTime()
	const now = nowMs || Date.now()
	const left = end - now
	if (left <= 0) return 0
	const hours = Number(totalHours) || matchOpenHours() || 48
	const totalMs = Math.max(hours, 0.1) * 3600 * 1000
	return Math.max(0, Math.min(1, left / totalMs))
}

export function discoverFeedMeta() {
	const boot = getBootstrap()
	const d = boot.discover || {}
	const profile = getProductProfile()
	return {
		daily_feed_cap: d.daily_feed_cap != null ? d.daily_feed_cap : profile.daily_feed_cap,
		daily_feed_vip_bonus: d.daily_feed_vip_bonus || profile.daily_feed_vip_bonus || {},
	}
}

export function vipFeedBonusLabel(vipTier) {
	const map = discoverFeedMeta().daily_feed_vip_bonus || {}
	const tier = vipTier || (uni.getStorageSync('userInfo') || {}).vip_tier || 'none'
	const n = map[tier]
	if (!n) return ''
	return `VIP加量 +${n}`
}

export function superLikeLabel() {
	if (isComplimentEnabled()) return '赞美'
	return '心动'
}

export function boostLabel() {
	return '曝光'
}
