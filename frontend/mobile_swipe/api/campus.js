import { getRequest, postRequest } from '@/utils/http.js'

export function apiCampusBind(data) {
	return postRequest('/campus/bind/', data)
}

export function apiCampusVerifyStub() {
	return postRequest('/campus/verify-stub/', {})
}

export function apiCampusFeed() {
	return getRequest('/campus/feed/', {}, { showLoading: false })
}
