import {
	host
} from '@/config/config.js'

// Single-flight logout; never reset after handling starts (avoids duplicate reLaunch).
let expiredHandling = false
// Ref-count loading so concurrent requests don't hide each other's toast.
let loadingCount = 0
let requestRecord = {}

function getToken() {
	return uni.getStorageSync('token') || '';
}

/** Paths that may be called without a user token (bootstrap / login / public telemetry). */
const PUBLIC_API_PREFIXES = [
	'/bootstrap/',
	'/auth/login',
	'/auth/register',
	'/auth/sms/',
	'/auth/facebook',
	'/auth/google',
	'/auth/apple',
	'/auth/wechat',
	'/auth/oauth/',
	'/auth/password/',
	'/auth/invite/',
	'/events/attribution',
	'/events/batch',
	'/maps/',
]

function isPublicApi(url) {
	const path = String(url || '').split('?')[0]
	const bare = path.startsWith('/api') ? path.slice(4) : path
	return PUBLIC_API_PREFIXES.some((p) => bare.startsWith(p) || path.startsWith(p) || path.startsWith('/api' + p))
}

const MODULE_PREFIXES = [
	['/recommend/', 'recommend'],
	['/likes/', 'likes'],
	['/profile/', 'profile'],
	['/match/', 'match'],
	['/chat/', 'chat'],
	['/vip/', 'vip'],
	['/translate/', 'translate'],
	['/events/', 'events'],
	['/push/', 'push'],
	['/verify/', 'verify'],
	['/safety/', 'safety'],
]

function resolveModuleKey(url) {
	const path = String(url || '').split('?')[0]
	for (let i = 0; i < MODULE_PREFIXES.length; i++) {
		const prefix = MODULE_PREFIXES[i][0]
		const key = MODULE_PREFIXES[i][1]
		if (path.startsWith(prefix) || path.startsWith('/api' + prefix)) {
			return key
		}
	}
	return null
}

function isModuleEnabled(moduleKey) {
	if (!moduleKey) return true
	const boot = uni.getStorageSync('bootstrap') || {}
	const modules = boot.enabled_modules || (boot.features && boot.features.enabled_modules)
	// bootstrap 尚未写入时放行，避免冷启动被拦
	if (!Array.isArray(modules)) return true
	return modules.indexOf(moduleKey) !== -1
}

let httpConfig = {
	header: {
		'Content-Type': "application/json",
		'is-dev': 'true'
	},
	method: 'POST',
	showLoading: true,
	loadingText: '请求中...',
	loadingTime: 800,
	loadingMask: false,
	stopRepeat: false,
	timeout: 1500000,
	errorOutput: true
}

function bumpLoading(show, text, mask) {
	if (!show) return
	if (loadingCount === 0) {
		uni.showLoading({ title: text, mask: mask })
	}
	loadingCount += 1
}

function dropLoading() {
	if (loadingCount <= 0) return
	loadingCount -= 1
	if (loadingCount === 0) {
		try { uni.hideLoading() } catch (e) {}
	}
}

function handleExpired(respData, errorOutput) {
	if (expiredHandling) return
	expiredHandling = true
	uni.removeStorageSync('token');
	uni.removeStorageSync('userInfo');
	if (errorOutput) {
		uni.showToast({
			title: '身份已过期，请重新登录',
			icon: 'none'
		});
	}
	setTimeout(() => {
		uni.reLaunch({ url: '/pages/auth/welcome' })
	}, 400);
}

function request(url, params, other) {
	other = {
		...httpConfig,
		...other,
		header: {
			...httpConfig.header,
			...(other && other.header ? other.header : {})
		}
	};
	const token = getToken();
	other.header['token'] = token;
	other.header['Accept-Language'] = uni.getStorageSync('currentLanguage') || 'zh'
	return new Promise((resolve, reject) => {
		const moduleKey = resolveModuleKey(url)
		if (!isModuleEnabled(moduleKey)) {
			const body = { code: 403, message: '该 APP 未开通此功能', results: { module: moduleKey } }
			if (other.errorOutput !== false && httpConfig.errorOutput) {
				uni.showToast({ title: body.message, icon: 'none' })
			}
			reject(body)
			return
		}
		// No token → do not hit auth-required APIs (avoids console 401 spam + false logout).
		if (!token && !isPublicApi(url)) {
			reject({ code: 401, message: 'not_logged_in' })
			return
		}
		if (other.stopRepeat) {
			if (requestRecord[url] === true) {
				reject();
				return;
			}
			requestRecord[url] = true;
		}
		// Per-request loading timer (do not share global timer across concurrent calls).
		let loadingArmed = false
		let reqTimer = null
		if (other.showLoading) {
			reqTimer = setTimeout(() => {
				reqTimer = null
				loadingArmed = true
				bumpLoading(true, other.loadingText, other.loadingMask)
			}, other.loadingTime);
		}
		uni.request({
			url: host + url,
			data: params,
			header: other.header,
			method: other.method,
			timeout: other.timeout,
			complete: data => {
				if (reqTimer) {
					clearTimeout(reqTimer)
					reqTimer = null
				} else if (loadingArmed) {
					dropLoading()
					loadingArmed = false
				}

				const respData = data.data || {};
				const isUnauthorized =
					data.statusCode === 401 ||
					respData.code === 401 ||
					respData.status === 401;

				if (isUnauthorized) {
					if (token) handleExpired(respData, httpConfig.errorOutput)
					reject(respData);
					if (other.stopRepeat) requestRecord[url] = false;
					return;
				}
				if (data.statusCode == 200 || data.statusCode == 201) {
					const body = data.data || {}
					if (body.code == 200 || body.code == 201) {
						resolve(body);
					} else {
						// business errors (403 need_vip / need_platinum etc.) — do NOT logout
						if (other.errorOutput !== false && httpConfig.errorOutput) {
							uni.showToast({
								title: body.msg || body.message || '请求失败',
								icon: 'none'
							})
						}
						reject(body);
					}
				} else {
					if (httpConfig.errorOutput) {
						uni.showToast({
							title: '请求失败',
							icon: 'none'
						})
					}
					reject(data)
				}
				if (other.stopRepeat) {
					requestRecord[url] = false;
				}
			}
		});
	})
}

function getRequest(url, params = {}, other = {}) {
	return request(url, params, {
		...other,
		method: 'GET'
	})
}

function postRequest(url, params = {}, other = {}) {
	return request(url, params, {
		...other,
		method: 'POST'
	})
}
function putRequest(url, params = {}, other = {}) {
	return request(url, params, {
		...other,
		method: 'PUT'
	})
}
function patchRequest(url, params = {}, other = {}) {
	return request(url, params, {
		...other,
		method: 'PATCH'
	})
}
function deleteRequest(url, params = {}, other = {}) {
	return request(url, params, {
		...other,
		method: 'DELETE'
	})
}
function getImg(url) {
	return `/static/${url}.png`
}

export {
	request,
	getRequest,
	postRequest,
	putRequest,
	patchRequest,
	deleteRequest,
	getImg
}
