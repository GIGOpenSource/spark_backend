import { getRequest, postRequest } from '@/utils/http.js'

export function apiFeed(params = {}) {
	return getRequest('/recommend/feed/', params, { showLoading: false })
}

/** @deprecated use apiFeed */
export function apiRecommendFeed(params = {}) {
	return apiFeed(params)
}

export function apiSwipe(data) {
	return postRequest('/recommend/swipe/', data, { showLoading: false })
}

export function apiRewind() {
	return postRequest('/recommend/rewind/', {})
}
