/**
 * Shell locale helpers — prefer i18n / shell default, never guess via app_id.includes('matchup').
 */
import { APP_ID } from '@/config/config.js'

/** Per-shell default (MatchUp CN-first; Spark/Swipe EN-first). */
export const SHELL_DEFAULT_LOCALE =
	APP_ID === 'matchup_main' ? 'zh' : 'en'

export function getStoredLocale() {
	try {
		const saved = uni.getStorageSync('currentLanguage')
		if (saved) return saved
	} catch (e) {}
	return SHELL_DEFAULT_LOCALE
}

/** True when UI should use Chinese copy. */
export function isZhUi() {
	const loc = String(getStoredLocale() || SHELL_DEFAULT_LOCALE).toLowerCase()
	return loc === 'zh' || loc.startsWith('zh')
}
