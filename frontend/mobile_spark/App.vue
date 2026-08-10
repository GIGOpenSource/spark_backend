<script setup>
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'
import { apiBootstrap, apiHeartbeat } from '@/api/auth.js'
import { apiAttribution } from '@/api/events.js'
import { track, flushAnalytics, configureAnalyticsFromBootstrap } from '@/utils/analytics.js'
import { APP_ID, PACKAGE_NAME } from '@/config/config.js'
import { registerPushToken, bindPushMessageHandler } from '@/utils/push.js'
import { applyTheme, getThemePref } from '@/utils/theme.js'

function collectLaunchAttribution(options = {}) {
	const q = { ...(options.query || {}) }
	// #ifdef H5
	try {
		if (typeof location !== 'undefined' && location.search) {
			const sp = new URLSearchParams(location.search)
			sp.forEach((v, k) => { if (v && !q[k]) q[k] = v })
			if (location.href) q.deep_link = location.href
		}
	} catch (e) {}
	// #endif
	const keys = [
		'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
		'fbclid', 'gclid', 'campaign_id', 'adset_id', 'ad_id', 'tag', 'click_id',
	]
	const payload = {}
	keys.forEach((k) => {
		if (q[k]) payload[k] = q[k]
	})
	if (q.deep_link) payload.deep_link = q.deep_link
	if (options.path && !payload.deep_link) payload.deep_link = options.path
	if (options.referrerInfo && options.referrerInfo.extraData) {
		const extra = options.referrerInfo.extraData
		Object.keys(extra || {}).forEach((k) => {
			if (extra[k] && !payload[k]) payload[k] = String(extra[k])
		})
	}
	return payload
}

function reportAttribution(options) {
	const payload = collectLaunchAttribution(options || {})
	if (!Object.keys(payload).length) return
	const dedupe = JSON.stringify(payload)
	if (uni.getStorageSync('attribution_last') === dedupe) return
	uni.setStorageSync('attribution_last', dedupe)
	apiAttribution(payload).catch(() => {})
}

function hideNativeTabBar() {
	try {
		uni.hideTabBar({ animation: false, fail: () => {} })
	} catch (e) {}
}

onLaunch(async (options) => {
	bindPushMessageHandler()
	applyTheme(getThemePref())
	hideNativeTabBar()
	reportAttribution(options)
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
		registerPushToken()
		if (uni.getStorageSync('token')) {
			import('@/utils/tabBadges.js').then((m) => m.refreshTabBadges({ force: true })).catch(() => {})
		}
	} catch (e) {}
})

onShow((options) => {
	applyTheme(getThemePref())
	hideNativeTabBar()
	if (options && (options.query || options.referrerInfo)) {
		reportAttribution(options)
	}
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
	background: var(--bg, #FFFFFF);
	color: var(--text, #111111);
	font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif;
}

:root,
page {
	--bg: #FFFFFF;
	--text: #111111;
	--muted: #666666;
	--accent: #FF4458;
	--surface: #F8F8F8;
	--border: rgba(0, 0, 0, 0.06);
}

[data-theme="dark"] {
	--bg: #111111;
	--text: #F5F5F5;
	--muted: #999999;
	--accent: #FF4458;
	--surface: #1A1A1A;
	--border: rgba(255, 255, 255, 0.08);
}

/* H5: pages use SparkTabBar; keep native uni-tabbar from stealing taps */
/* #ifdef H5 */
uni-tabbar {
	display: none !important;
	pointer-events: none !important;
}
uni-page-wrapper,
uni-page-body,
.uni-app--showtabbar {
	/* native bar hidden → reclaim bottom inset */
	--window-bottom: 0px !important;
}
/* #endif */
</style>
