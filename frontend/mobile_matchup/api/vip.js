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
	const platform = detectStorePlatform()
	let payload = {
		product_id: productId,
		platform: isIapMock() || platform === 'mock' ? 'mock' : platform,
		...extra,
	}

	if (!isIapMock() && platform !== 'mock') {
		const native = await requestNativePurchase(productId)
		if (native.ok) {
			payload = {
				product_id: native.product_id || productId,
				platform: native.platform || platform,
				transaction_id: native.transaction_id,
				purchase_token: native.purchase_token,
				subscription: native.subscription,
			}
		} else if (native.error === 'native_iap_unavailable' || native.error === 'store_channel_unavailable') {
			// No store bridge — still post with platform so backend can mock-fallback when credentials missing
			payload = {
				product_id: productId,
				platform,
				transaction_id: platform === 'ios' ? undefined : undefined,
				purchase_token: undefined,
				warning: native.error,
			}
			uni.showToast({
				title: 'Store SDK not linked — configure IAP plugin',
				icon: 'none',
			})
			return Promise.reject({ message: native.error || 'native_iap_unavailable' })
		} else {
			return Promise.reject({ message: native.error || 'purchase_failed' })
		}
	}

	return postRequest('/vip/purchase/', payload)
}

export async function apiRestorePurchases(extra = {}) {
	const platform = detectStorePlatform()
	const receipts = extra.receipts || (await requestNativeRestoreReceipts())
	return postRequest('/vip/restore/', {
		platform: isIapMock() || platform === 'mock' ? 'mock' : platform,
		receipts: Array.isArray(receipts) ? receipts : [],
		...extra,
	})
}

export function apiBoost() {
	return postRequest('/vip/boost/', {})
}

/** CN pay channels (WeChat / Alipay) — stub until native bridge ships */
export function apiVipCnPay(data = {}) {
	return postRequest('/vip/cn-pay/', {
		product_id: data.product_id,
		channel: data.channel || 'wechat', // wechat | alipay
		...data,
	})
}

export function apiBoostReport() {
	return getRequest('/vip/boost/report/', {}, { showLoading: false })
}

