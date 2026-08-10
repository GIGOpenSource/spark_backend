import { getRequest, postRequest } from '@/utils/http.js'

export function apiVerifyStart() {
	return postRequest('/verify/start/', {})
}

export function apiVerifyStatus() {
	return getRequest('/verify/status/', {}, { showLoading: false })
}

export function apiVerifySandboxDecide(data = {}) {
	return postRequest('/verify/sandbox/decide/', data)
}
