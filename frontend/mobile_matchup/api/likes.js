import { getRequest, postRequest } from '@/utils/http.js'

export function apiLikesReceived(sort = 'all') {
	return getRequest('/likes/received/', { sort }, { showLoading: false })
}

export function apiLikesSent() {
	return getRequest('/likes/sent/', {}, { showLoading: false })
}

export function apiLikesUnlock(swipeId) {
	return postRequest('/likes/unlock/', { swipe_id: swipeId })
}

export function apiSayHi(data) {
	return postRequest('/likes/say-hi/', data)
}

export function apiCompliment(data) {
	return postRequest('/likes/compliment/', data)
}

export function apiMatches() {
	return getRequest('/match/list/', {}, { showLoading: false })
}

export function apiUnmatch(matchId) {
	return postRequest('/match/unmatch/', { match_id: matchId })
}

export function apiExtendMatch(matchId) {
	return postRequest('/match/extend/', { match_id: matchId })
}

export function apiOpenMessage(matchId, content) {
	return postRequest('/match/open-message/', { match_id: matchId, content })
}

/** Match QA gate — /api/match/qa/* (MatchUp) */
export function apiQaTemplates({ locale = 'zh' } = {}) {
	return getRequest('/match/qa/templates/', { locale }, { showLoading: false })
}

export function apiQaAsk(matchId, question) {
	return postRequest('/match/qa/ask/', { match_id: matchId, question })
}

export function apiQaAnswer(matchId, answer) {
	return postRequest('/match/qa/answer/', { match_id: matchId, answer })
}

export function apiQaReview(matchId, approve, allowRetry = true) {
	return postRequest('/match/qa/review/', {
		match_id: matchId,
		approve: !!approve,
		allow_retry: allowRetry,
	})
}
