/**
 * Native capability bridges — pass real store/OAuth fields when available,
 * fall back cleanly without inventing fake Apple/Google SDKs.
 */
import { USE_IAP_MOCK, USE_FIREBASE_MOCK } from '@/config/config.js'

export function detectStorePlatform() {
	try {
		const sys = uni.getSystemInfoSync() || {}
		const p = String(sys.platform || '').toLowerCase()
		if (p === 'ios') return 'ios'
		if (p === 'android') return 'android'
		const uniP = String(sys.uniPlatform || '').toLowerCase()
		if (uniP === 'app' || uniP === 'app-plus') {
			return p === 'ios' ? 'ios' : 'android'
		}
	} catch (e) {}
	return 'mock'
}

export function bootstrapFeatures() {
	const boot = uni.getStorageSync('bootstrap') || {}
	return boot.features || {}
}

export function isIapMock() {
	const f = bootstrapFeatures()
	if (typeof f.iap_mock === 'boolean') return f.iap_mock
	return !!USE_IAP_MOCK
}

export function isFirebaseMock() {
	const f = bootstrapFeatures()
	if (typeof f.firebase_mock === 'boolean') return f.firebase_mock
	return !!USE_FIREBASE_MOCK
}

export function isSmsMock() {
	const f = bootstrapFeatures()
	if (typeof f.sms_mock === 'boolean') return f.sms_mock
	return true
}

export function isAppleSignInConfigured() {
	const f = bootstrapFeatures()
	if (typeof f.apple_signin_configured === 'boolean') return f.apple_signin_configured
	return false
}

/**
 * Attempt native IAP. Returns purchase payload fields for POST /vip/purchase/.
 * Does not invent store calls — only uses plus.payment / uni plugins when present.
 */
export function requestNativePurchase(productId) {
	return new Promise((resolve) => {
		const platform = detectStorePlatform()
		if (platform === 'mock' || isIapMock()) {
			resolve({
				ok: true,
				platform: 'mock',
				product_id: productId,
				transaction_id: `mock_${Date.now()}`,
			})
			return
		}

		// #ifdef APP-PLUS
		try {
			if (typeof plus !== 'undefined' && plus.payment) {
				const channelId = platform === 'ios' ? 'appleiap' : 'google-iap'
				plus.payment.getChannels((channels) => {
					const ch = (channels || []).find((c) => c.id === channelId)
					if (!ch) {
						resolve({
							ok: false,
							error: 'store_channel_unavailable',
							platform,
							product_id: productId,
						})
						return
					}
					plus.payment.request(ch, { productid: productId }, (result) => {
						const tid = (result && (result.transactionIdentifier || result.transaction_id)) || ''
						const token = (result && (result.purchaseToken || result.token || result.purchase_token)) || ''
						resolve({
							ok: true,
							platform,
							product_id: productId,
							transaction_id: tid || undefined,
							purchase_token: token || undefined,
							subscription: /_(1|6|12)m$/.test(productId),
							raw: result,
						})
					}, (err) => {
						resolve({
							ok: false,
							error: (err && (err.message || err.code)) || 'purchase_cancelled',
							platform,
							product_id: productId,
						})
					})
				}, () => {
					resolve({
						ok: false,
						error: 'payment_channels_failed',
						platform,
						product_id: productId,
					})
				})
				return
			}
		} catch (e) {
			resolve({
				ok: false,
				error: (e && e.message) || 'native_iap_error',
				platform,
				product_id: productId,
			})
			return
		}
		// #endif

		resolve({
			ok: false,
			error: 'native_iap_unavailable',
			platform,
			product_id: productId,
		})
	})
}

function mapRestoreItem(item, platform) {
	if (!item || typeof item !== 'object') return null
	const productId = item.productid || item.productId || item.product_id || ''
	const tid = item.transactionIdentifier || item.transaction_id || item.orderId || ''
	const token = item.purchaseToken || item.token || item.purchase_token || ''
	if (!productId && !tid && !token) return null
	return {
		product_id: productId,
		transaction_id: tid || undefined,
		purchase_token: token || undefined,
		platform,
	}
}

/**
 * Collect restored receipts from native store if available.
 */
export function requestNativeRestoreReceipts() {
	return new Promise((resolve) => {
		const platform = detectStorePlatform()
		if (platform === 'mock' || isIapMock()) {
			resolve([])
			return
		}

		// #ifdef APP-PLUS
		try {
			if (typeof plus !== 'undefined' && plus.payment) {
				const channelId = platform === 'ios' ? 'appleiap' : 'google-iap'
				plus.payment.getChannels((channels) => {
					const ch = (channels || []).find((c) => c.id === channelId)
					if (!ch) {
						resolve([])
						return
					}
					const finish = (list) => {
						const mapped = (list || [])
							.map((item) => mapRestoreItem(item, platform))
							.filter(Boolean)
						resolve(mapped)
					}
					try {
						if (typeof ch.restoreComplateRequest === 'function') {
							ch.restoreComplateRequest({}, finish, () => resolve([]))
							return
						}
					} catch (e) {}
					try {
						if (typeof plus.payment.restoreComplateRequest === 'function') {
							plus.payment.restoreComplateRequest(ch, finish, () => resolve([]))
							return
						}
					} catch (e) {}
					try {
						if (platform === 'ios' && typeof ch.restoreCompletedTransactions === 'function') {
							ch.restoreCompletedTransactions({}, finish, () => resolve([]))
							return
						}
					} catch (e) {}
					// Android / channel restore fallback
					try {
						if (typeof ch.restore === 'function') {
							ch.restore(finish, () => resolve([]))
							return
						}
					} catch (e) {}
					resolve([])
				}, () => resolve([]))
				return
			}
		} catch (e) {
			resolve([])
			return
		}
		// #endif

		resolve([])
	})
}

/** Alias used by settings restore flow */
export function requestNativeRestore() {
	return requestNativeRestoreReceipts()
}

/**
 * Try to obtain a Google ID token from a native bridge if one was registered.
 * Register via: uni.$sparkGoogleGetIdToken = () => Promise<string>
 */
export async function getGoogleIdToken() {
	try {
		if (typeof uni !== 'undefined' && typeof uni.$sparkGoogleGetIdToken === 'function') {
			const t = await uni.$sparkGoogleGetIdToken()
			if (t && typeof t === 'string') return t
		}
	} catch (e) {}
	// #ifdef APP-PLUS
	try {
		const token = await new Promise((resolve) => {
			try {
				uni.login({
					provider: 'google',
					success: (res) => {
						const t = (res && (res.id_token || res.authResult && res.authResult.id_token)) || ''
						resolve(typeof t === 'string' ? t : '')
					},
					fail: () => resolve(''),
				})
			} catch (err) {
				resolve('')
			}
		})
		if (token) return token
	} catch (e) {}
	try {
		const g = uni.getStorageSync('google_id_token_cache')
		if (g && typeof g === 'string') return g
	} catch (e) {}
	// #endif
	return ''
}

/**
 * Apple identity token — uni.$sparkAppleGetIdentityToken, then APP-PLUS oauth.
 */
export async function getAppleIdentityToken() {
	try {
		if (typeof uni !== 'undefined' && typeof uni.$sparkAppleGetIdentityToken === 'function') {
			const t = await uni.$sparkAppleGetIdentityToken()
			if (t && typeof t === 'string') return t
		}
	} catch (e) {}
	// #ifdef APP-PLUS
	try {
		const token = await new Promise((resolve) => {
			try {
				uni.login({
					provider: 'apple',
					success: (res) => {
						const t = (res && (
							res.identityToken
							|| res.appleInfo && res.appleInfo.identityToken
							|| res.authResult && res.authResult.identityToken
						)) || ''
						resolve(typeof t === 'string' ? t : '')
					},
					fail: () => resolve(''),
				})
			} catch (err) {
				resolve('')
			}
		})
		if (token) return token
	} catch (e) {}
	try {
		if (typeof plus !== 'undefined' && plus.oauth) {
			const token = await new Promise((resolve) => {
				plus.oauth.getServices((services) => {
					const apple = (services || []).find((s) => s.id === 'apple' || s.id === 'appleid')
					if (!apple) {
						resolve('')
						return
					}
					apple.authorize((e) => {
						const t = (e && (e.appleInfo && e.appleInfo.identityToken || e.identityToken)) || ''
						resolve(typeof t === 'string' ? t : '')
					}, () => resolve(''))
				}, () => resolve(''))
			})
			if (token) return token
		}
	} catch (e) {}
	// #endif
	return ''
}
