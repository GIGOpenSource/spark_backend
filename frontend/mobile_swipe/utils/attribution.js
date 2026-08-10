import { apiAttribution } from '@/api/events.js'
import { APP_ID, PACKAGE_NAME } from '@/config/config.js'

function pickQuery(obj) {
	if (!obj || typeof obj !== 'object') return {}
	const keys = [
		'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
		'fbclid', 'gclid', 'ttclid', 'appsflyer_id', 'adjust_id',
		'campaign_id', 'ad_id', 'adset_id', 'deep_link', 'dl',
	]
	const out = {}
	keys.forEach((k) => {
		if (obj[k] != null && String(obj[k]).trim()) out[k] = String(obj[k]).trim()
	})
	return out
}

export function collectLaunchAttribution(options = {}) {
	const q = pickQuery(options.query || options)
	let deepLink = options.path || options.referrer || ''
	// #ifdef H5
	try {
		if (typeof window !== 'undefined' && window.location) {
			const sp = new URLSearchParams(window.location.search || '')
			sp.forEach((v, k) => {
				if (v && !q[k]) q[k] = v
			})
			deepLink = deepLink || window.location.href
		}
	} catch (e) {}
	// #endif
	return { ...q, deep_link: deepLink || q.deep_link || '' }
}

export function reportLaunchAttribution(launchOptions = {}) {
	const payload = collectLaunchAttribution(launchOptions)
	const has = Object.keys(payload).some((k) => k !== 'deep_link' && payload[k])
	if (!has && !payload.deep_link) return Promise.resolve()
	return apiAttribution({
		...payload,
		app_id: APP_ID,
		package_name: PACKAGE_NAME,
		event: 'install_open',
		ts: Date.now(),
	}).catch(() => {})
}
