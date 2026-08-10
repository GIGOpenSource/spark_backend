import { getRequest, postRequest } from '@/utils/http.js'
import {
	detectStorePlatform,
	isIapMock,
	requestNativePurchase,
	requestNativeRestoreReceipts,
} from '@/utils/capabilities.js'

export function apiProducts() {
	return getRequest('/vip/products/', {})
}

export function apiEntitlements() {
	return getRequest('/vip/entitlements/', {}, { showLoading: false })
}

export async function apiPurchase(productId, extra = {}) {
	const storePlatform = detectStorePlatform()
	const mock = isIapMock()

	if (mock || storePlatform === 'mock') {
		if (!mock && storePlatform === 'mock') {
			uni.showToast({ title: 'IAP requires a native build', icon: 'none' })
			return Promise.reject({ message: 'native_iap_required' })
		}
		return postRequest('/vip/purchase/', {
			product_id: productId,
			platform: 'mock',
			transaction_id: `mock_${Date.now()}`,
			...extra,
		})
	}

	const native = await requestNativePurchase(productId)
	if (!native.ok) {
		uni.showToast({
			title: native.error === 'purchase_cancelled' ? 'Cancelled' : 'Store SDK not linked',
			icon: 'none',
		})
		return Promise.reject({ message: native.error || 'purchase_failed' })
	}

	return postRequest('/vip/purchase/', {
		product_id: native.product_id || productId,
		platform: native.platform || storePlatform,
		transaction_id: native.transaction_id,
		purchase_token: native.purchase_token,
		subscription: native.subscription,
		...extra,
	})
}

export async function apiRestorePurchases(extra = {}) {
	const storePlatform = detectStorePlatform()
	const mock = isIapMock()
	const receipts = extra.receipts || (await requestNativeRestoreReceipts())
	return postRequest('/vip/restore/', {
		platform: mock || storePlatform === 'mock' ? 'mock' : storePlatform,
		receipts: Array.isArray(receipts) ? receipts : [],
		...extra,
	})
}

export function apiBoost() {
	return postRequest('/vip/boost/', {})
}

export function apiBoostReport() {
	return getRequest('/vip/boost/report/', {}, { showLoading: false })
}
