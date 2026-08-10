<script setup>
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'
import { apiBootstrap, apiHeartbeat } from '@/api/auth.js'
import { track, flushAnalytics, configureAnalyticsFromBootstrap } from '@/utils/analytics.js'
import { APP_ID, PACKAGE_NAME } from '@/config/config.js'
import { registerPushToken, bindPushMessageHandler } from '@/utils/push.js'
import { reportLaunchAttribution } from '@/utils/attribution.js'
import { applyTheme, getThemePref } from '@/utils/theme.js'

onLaunch(async (options) => {
	bindPushMessageHandler()
	reportLaunchAttribution(options || {})
	applyTheme(getThemePref())
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
	if (options) reportLaunchAttribution(options)
	applyTheme(getThemePref())
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
@import "uview-plus/index.scss";

:root,
page {
	--bg: #FFFFFF;
	--text: #111111;
	--muted: #888888;
	--accent: #FFC629;
	--card: #F7F7F7;
	--border: rgba(255, 198, 41, 0.35);
}

[data-theme="dark"],
page[data-theme="dark"] {
	--bg: #111111;
	--text: #F5F5F5;
	--muted: #A0A0A0;
	--accent: #FFC629;
	--card: #1C1C1C;
	--border: rgba(255, 198, 41, 0.28);
}

page {
	background: var(--bg);
	color: var(--text);
	font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
}

.display-font {
	font-family: 'Montserrat', 'Helvetica Neue', sans-serif;
	font-weight: 800;
}
</style>
