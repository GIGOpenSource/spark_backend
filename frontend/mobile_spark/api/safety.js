import { getRequest, postRequest, putRequest } from '@/utils/http.js'

export function apiSafetyPref() {
	return getRequest('/safety/pref/', {}, { showLoading: false })
}

export function apiSafetyPrefUpdate(data) {
	return putRequest('/safety/pref/', data)
}

export function apiDateShare(data) {
	return postRequest('/safety/date-share/', data)
}

export function apiSos(data = {}) {
	return postRequest('/safety/sos/', data, { showLoading: false })
}
