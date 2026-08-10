<script setup>
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'
import { apiBootstrap, apiHeartbeat } from '@/api/auth.js'
import { apiAttribution } from '@/api/events.js'
import { track, flushAnalytics, configureAnalyticsFromBootstrap } from '@/utils/analytics.js'
import { APP_ID, PACKAGE_NAME } from '@/config/config.js'
import { registerPushToken, bindPushMessageHandler } from '@/utils/push.js'
import { applyTheme, getThemePref } from '@/utils/theme.js'

function collectAttribution() {
	const payload = {}
	try {
		const launch = uni.getLaunchOptionsSync && uni.getLaunchOptionsSync()
		const q = (launch && launch.query) || {}
		;['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'fbclid', 'gclid', 'campaign_id'].forEach((k) => {
			if (q[k]) payload[k] = String(q[k])
		})
		if (launch && launch.path) payload.landing_path = launch.path
	} catch (e) {}
	try {
		// #ifdef H5
		if (typeof location !== 'undefined') {
			const sp = new URLSearchParams(location.search || '')
			;['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'fbclid', 'gclid', 'campaign_id'].forEach((k) => {
				const v = sp.get(k)
				if (v) payload[k] = v
			})
		}
		// #endif
	} catch (e) {}
	const cached = uni.getStorageSync('attribution_pending')
	if (cached && typeof cached === 'object') Object.assign(payload, cached)
	return payload
}

onLaunch(async () => {
	bindPushMessageHandler()
	try {
		applyTheme(getThemePref())
	} catch (e) {}
	try {
		const sys = uni.getSystemInfoSync()
		const platform = sys.uniPlatform === 'app' || sys.uniPlatform === 'app-plus'
			? (sys.platform === 'ios' ? 'ios' : 'android')
			: 'h5'
		const res = await apiBootstrap({
			app_id: APP_ID,
			platform,
			package_name: PACKAGE_NAME,
			app_version: '1.0.0'
		})
		const boot = res.results || {}
		uni.setStorageSync('bootstrap', boot)
		configureAnalyticsFromBootstrap(boot)
		track('app_launch', { platform, review_mode: !!boot.review_mode })
		const attr = collectAttribution()
		if (Object.keys(attr).length) {
			apiAttribution(attr).then(() => {
				uni.removeStorageSync('attribution_pending')
			}).catch(() => {})
		}
		registerPushToken()
		if (uni.getStorageSync('token')) {
			import('@/utils/tabBadges.js').then((m) => m.refreshTabBadges({ force: true })).catch(() => {})
		}
	} catch (e) {}
})

onShow(() => {
	try { applyTheme(getThemePref()) } catch (e) {}
	const token = uni.getStorageSync('token')
	if (token) {
		apiHeartbeat().catch(() => {})
		import('@/utils/tabBadges.js').then((m) => m.refreshTabBadges()).catch(() => {})
		registerPushToken()
		import('@/utils/maps.js').then((m) => m.reportLocation({ updateCity: false })).catch(() => {})
	}
})

onHide(() => {
	flushAnalytics()
})
</script>

<style lang="scss">
/* theme 已在 uni.scss 注入；$u-* 变量对 index.scss 可用 */
@import "uview-plus/index.scss";

page {
	background: var(--bg, #FFF7FA);
	color: var(--text, #222);
	font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', sans-serif;
}

[data-theme="dark"] page,
html[data-theme="dark"] page {
	background: var(--bg, #141014);
	color: var(--text, #F5F0F2);
}
</style>
