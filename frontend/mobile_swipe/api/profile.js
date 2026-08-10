import { getRequest, postRequest, putRequest, deleteRequest } from '@/utils/http.js'

export function apiProfileMe() {
	return getRequest('/profile/me/', {}, { showLoading: false })
}

export function apiProfileUpdate(data) {
	return putRequest('/profile/me/update/', data)
}

export function apiProfileDetail(userId) {
	return getRequest('/profile/detail/', { user_id: userId }, { showLoading: false })
}

export function apiProfilePreview() {
	return getRequest('/profile/preview/', {}, { showLoading: false })
}

export function apiSmartPhotos(data = {}) {
	return postRequest('/profile/photos/smart/', data)
}

export function apiFiltersGet() {
	return getRequest('/profile/filters/', {})
}

export function apiFiltersSave(data) {
	return postRequest('/profile/filters/', data)
}

export function apiBlock(userId) {
	return postRequest('/profile/block/', { user_id: userId })
}

export function apiBlocks() {
	return getRequest('/profile/blocks/', {}, { showLoading: false })
}

export function apiUnblock(userId) {
	return postRequest('/profile/unblock/', { user_id: userId })
}

export function apiReport(data) {
	return postRequest('/profile/report/', data)
}

export function apiUploadPhoto(data) {
	return postRequest('/profile/photos/', data)
}

export function apiDeletePhoto(photoId) {
	return deleteRequest(`/profile/photos/${photoId}/`)
}

export function apiReorderPhotos(photoIds) {
	return postRequest('/profile/photos/reorder/', { photo_ids: photoIds })
}

export function apiInterestVote(targetId, interest) {
	return postRequest('/profile/interest-vote/', { target_id: targetId, interest })
}

