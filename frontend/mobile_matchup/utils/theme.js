const KEY = 'spark_theme_pref' // light | dark | system

const LIGHT = {
	'--bg': '#FFFFFF',
	'--text': '#111111',
	'--muted': '#666666',
	'--accent': '#FF4458',
	'--surface': '#F8F8F8',
	'--border': 'rgba(0,0,0,0.06)',
}

const DARK = {
	'--bg': '#111111',
	'--text': '#F5F5F5',
	'--muted': '#999999',
	'--accent': '#FF4458',
	'--surface': '#1A1A1A',
	'--border': 'rgba(255,255,255,0.08)',
}

export function getThemePref() {
	return uni.getStorageSync(KEY) || 'system'
}

export function resolveTheme(pref) {
	const p = pref || getThemePref()
	if (p === 'light' || p === 'dark') return p
	try {
		const sys = uni.getSystemInfoSync() || {}
		const t = sys.theme || sys.osTheme || sys.hostTheme || 'light'
		return String(t).toLowerCase() === 'dark' ? 'dark' : 'light'
	} catch (e) {
		return 'light'
	}
}

function applyCssVars(mode) {
	const vars = mode === 'dark' ? DARK : LIGHT
	// #ifdef H5
	try {
		if (typeof document !== 'undefined') {
			const root = document.documentElement
			Object.keys(vars).forEach((k) => root.style.setProperty(k, vars[k]))
			root.setAttribute('data-theme', mode)
			document.body.style.background = vars['--bg']
			document.body.style.color = vars['--text']
		}
	} catch (e) {}
	// #endif
	try {
		uni.setStorageSync('spark_theme_vars', vars)
	} catch (e) {}
}

export function applyTheme(pref) {
	const mode = resolveTheme(pref)
	applyCssVars(mode)
	uni.setStorageSync('spark_theme_resolved', mode)
	return mode
}

export function setThemePref(pref) {
	uni.setStorageSync(KEY, pref)
	return applyTheme(pref)
}
