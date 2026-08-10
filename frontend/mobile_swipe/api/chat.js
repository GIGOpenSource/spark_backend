import { getRequest, postRequest } from '@/utils/http.js'

export function apiConversations() {
	return getRequest('/chat/conversations/', {}, { showLoading: false })
}

export function apiMessages(cid) {
	return getRequest(`/chat/conversations/${cid}/messages/`, {}, { showLoading: false })
}

export function apiSendMessage(cid, data) {
	return postRequest(`/chat/conversations/${cid}/send/`, data, { showLoading: false })
}

export function apiTranslate(data) {
	return postRequest('/translate/text/', data)
}

export function apiSearchGifs(q, limit = 24) {
	return getRequest('/chat/gifs/search/', { q: q || '', limit }, { showLoading: false })
}

export function apiCallToken(conversationId) {
	return postRequest('/chat/call/token/', { conversation_id: conversationId })
}

export function apiCallHangup(conversationId) {
	return postRequest('/chat/call/hangup/', { conversation_id: conversationId }, { showLoading: false })
}
