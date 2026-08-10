import { getRequest, postRequest } from '@/utils/http.js'

export function apiMatchmakerInvite(data) {
	return postRequest('/matchmaker/invite/', data)
}

export function apiMatchmakerInbox() {
	return getRequest('/matchmaker/inbox/', {}, { showLoading: false })
}

export function apiMatchmakerRespond(inviteId, accept) {
	return postRequest('/matchmaker/respond/', { invite_id: inviteId, accept: !!accept })
}
