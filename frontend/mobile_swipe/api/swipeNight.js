import { getRequest, postRequest } from '@/utils/http.js'

export function apiSwipeNightCurrent() {
	return getRequest('/swipe-night/current/', {}, { showLoading: false })
}

export function apiSwipeNightCandidates() {
	return getRequest('/swipe-night/candidates/', {}, { showLoading: false })
}

export function apiSwipeNightPick(targetId) {
	return postRequest('/swipe-night/pick/', { target_id: targetId })
}

export function apiSwipeNightSettle() {
	return postRequest('/swipe-night/settle/', {})
}
