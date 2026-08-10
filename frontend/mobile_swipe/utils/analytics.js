/**
 * Unified analytics SDK — batch to self-built /api/events/ + server-side GA4 forward.
 */
import { apiEventsBatch } from '@/api/events.js'
import { labelZhForEvent } from '@/utils/eventDict.js'

const QUEUE_MAX = 50
const FLUSH_MS = 400
const APP_VERSION = '1.0.0'

let queue = []
let timer = null
let lastPageKey = ''
let lastPageAt = 0

function analyticsEnabled() {
	try {
		const boot = uni.getStorageSync('bootstrap') || {}
		const feats = boot.features || {}
		const analytics = feats.analytics || {}
		if (analytics.self_enabled === false) return false
		const modules = feats.enabled_modules || boot.enabled_modules
		if (Array.isArray(modules) && modules.length && !modules.includes('events')) return false
		return true
	} catch (e) {
		return true
	}
}

function ensureDeviceId() {
	let id = uni.getStorageSync('analytics_device_id')
	if (!id) {
		id = `d_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`
		uni.setStorageSync('analytics_device_id', id)
	}
	return id
}

function ensureSessionId() {
	let id = uni.getStorageSync('analytics_session_id')
	const started = Number(uni.getStorageSync('analytics_session_at') || 0)
	const now = Date.now()
	// refresh session after 30 min idle
	if (!id || !started || now - started > 30 * 60 * 1000) {
		id = `s_${now.toString(36)}_${Math.random().toString(36).slice(2, 8)}`
		uni.setStorageSync('analytics_session_id', id)
	}
	uni.setStorageSync('analytics_session_at', now)
	return id
}

function deviceLocale() {
	try {
		const sys = uni.getSystemInfoSync()
		return sys.language || sys.locale || ''
	} catch (e) {
		return ''
	}
}

export function currentPageRoute() {
	try {
		const pages = getCurrentPages()
		const cur = pages && pages.length ? pages[pages.length - 1] : null
		if (!cur) return ''
		return String(cur.route || cur.$page?.fullPath || '').replace(/^\//, '')
	} catch (e) {
		return ''
	}
}

function flush() {
	if (!queue.length) return
	if (!analyticsEnabled()) {
		queue = []
		return
	}
	const batch = queue.splice(0, QUEUE_MAX)
	apiEventsBatch(batch).catch(() => {})
	if (queue.length) scheduleFlush()
}

function scheduleFlush() {
	clearTimeout(timer)
	timer = setTimeout(flush, FLUSH_MS)
}

/**
 * @param {string} name English event name
 * @param {object} props
 */
export function track(name, props = {}) {
	if (!name || !analyticsEnabled()) return
	const payloadProps = {
		device_id: ensureDeviceId(),
		session_id: ensureSessionId(),
		...props,
	}
	if (!payloadProps.event_zh) {
		payloadProps.event_zh = labelZhForEvent(name, payloadProps)
	}
	if (!payloadProps.page && name !== 'page_view') {
		const page = currentPageRoute()
		if (page) payloadProps.page = page
	}
	queue.push({
		name: String(name),
		ts: Date.now(),
		props: payloadProps,
		app_version: APP_VERSION,
		device_locale: deviceLocale(),
	})
	if (queue.length >= QUEUE_MAX) {
		flush()
	} else {
		scheduleFlush()
	}
}

export function trackPage(page, extra = {}) {
	const route = String(page || currentPageRoute() || '').replace(/^\//, '')
	if (!route) return
	const now = Date.now()
	// dedupe rapid duplicate onShow (tab flicker)
	if (route === lastPageKey && now - lastPageAt < 800) return
	lastPageKey = route
	lastPageAt = now
	track('page_view', { page: route, page_zh: labelZhForEvent('page_view', { page: route }), ...extra })
}

export function trackClick(btn, extra = {}) {
	if (!btn) return
	track('btn_click', {
		btn: String(btn),
		btn_zh: labelZhForEvent('btn_click', { btn }),
		page: currentPageRoute(),
		...extra,
	})
}

/** Force flush (e.g. before navigate away / app hide). */
export function flushAnalytics() {
	clearTimeout(timer)
	flush()
}

export function configureAnalyticsFromBootstrap(boot = {}) {
	// bootstrap already stored; this is a no-op hook for App.vue clarity
	if (boot && typeof boot === 'object') {
		uni.setStorageSync('bootstrap', { ...(uni.getStorageSync('bootstrap') || {}), ...boot })
	}
}
