/**
 * Upload helper — pages must not call uni.uploadFile directly.
 */
import { host } from '@/config/config.js'

function authHeaders(extra = {}) {
	return {
		token: uni.getStorageSync('token') || '',
		'is-dev': 'true',
		'Accept-Language': uni.getStorageSync('currentLanguage') || 'zh',
		...extra,
	}
}

function parseBody(raw) {
	if (raw == null) return {}
	if (typeof raw === 'object') return raw
	try {
		return JSON.parse(raw)
	} catch (e) {
		return {}
	}
}

/**
 * @param {object} opts
 * @param {string} opts.url path under API host, e.g. '/profile/photos/'
 * @param {string} opts.filePath local temp path
 * @param {string} [opts.name='file']
 * @param {object} [opts.formData]
 * @param {object} [opts.header]
 * @returns {Promise<object>} resolved API body { code, results, message }
 */
export function uploadFile(opts = {}) {
	const {
		url,
		filePath,
		name = 'file',
		formData,
		header,
	} = opts
	if (!url || !filePath) {
		return Promise.reject({ code: 400, message: 'missing url/filePath' })
	}
	const fullUrl = url.startsWith('http') ? url : (host + (url.startsWith('/') ? url : '/' + url))
	return new Promise((resolve, reject) => {
		uni.uploadFile({
			url: fullUrl,
			filePath,
			name,
			formData: formData || {},
			header: authHeaders(header || {}),
			success: (resp) => {
				const body = parseBody(resp.data)
				if (resp.statusCode === 401 || body.code === 401 || body.status === 401) {
					uni.removeStorageSync('token')
					uni.removeStorageSync('userInfo')
					uni.showToast({ title: '身份已过期，请重新登录', icon: 'none' })
					setTimeout(() => uni.reLaunch({ url: '/pages/auth/welcome' }), 400)
					reject(body)
					return
				}
				if (resp.statusCode === 200 || resp.statusCode === 201) {
					if (body.code === 200 || body.code === 201) {
						resolve(body)
						return
					}
					reject(body)
					return
				}
				reject(body && Object.keys(body).length ? body : { code: resp.statusCode, message: 'upload failed' })
			},
			fail: (err) => reject(err || { message: 'network error' }),
		})
	})
}

export function apiUploadPhoto(filePath, formData) {
	return uploadFile({ url: '/profile/photos/', filePath, formData })
}

export function apiUploadChatMedia(filePath, formData) {
	return uploadFile({ url: '/chat/upload/', filePath, formData })
}
