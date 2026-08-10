import { getRequest, postRequest, putRequest } from '@/utils/http.js'

export function apiRegisterPushToken(data) {
	return postRequest('/push/token/', data, { showLoading: false, errorOutput: false })
}

export function apiPushOpened(data = {}) {
	return postRequest('/push/opened/', data, { showLoading: false, errorOutput: false })
}

export function apiPushPrefsGet() {
	return getRequest('/push/prefs/', {}, { showLoading: false })
}

export function apiPushPrefsUpdate(data) {
	return putRequest('/push/prefs/', data)
}
