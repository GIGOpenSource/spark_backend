import { getRequest, postRequest } from '@/utils/http.js'

export function apiSelectApply(note = '') {
	return postRequest('/select/apply/', { note })
}

export function apiSelectStatus() {
	return getRequest('/select/status/', {}, { showLoading: false })
}

export function apiSelectFeed() {
	return getRequest('/select/feed/', {}, { showLoading: false })
}
