import { getRequest, postRequest } from '@/utils/http.js'

export function apiF2FStart(data) {
	return postRequest('/face-to-face/start/', data)
}

export function apiF2FFeed() {
	return getRequest('/face-to-face/feed/', {}, { showLoading: false })
}

export function apiF2FStop() {
	return postRequest('/face-to-face/stop/', {})
}
