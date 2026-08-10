/**
 * Global page PV mixin — call trackPage on every page onShow.
 * Registered via app.mixin in main.js (Vue3).
 */
import { trackPage } from '@/utils/analytics.js'

export const pageAnalyticsMixin = {
	onShow() {
		try {
			const pages = getCurrentPages()
			const cur = pages && pages.length ? pages[pages.length - 1] : null
			const route = cur ? String(cur.route || '').replace(/^\//, '') : ''
			if (route) trackPage(route)
		} catch (e) {}
	},
}

export default pageAnalyticsMixin
