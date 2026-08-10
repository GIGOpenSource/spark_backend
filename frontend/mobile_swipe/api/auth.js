import { getRequest, postRequest } from '@/utils/http.js'
import { APP_ID } from '@/config/config.js'
import { getGoogleIdToken, getAppleIdentityToken, isFirebaseMock } from '@/utils/capabilities.js'

export function apiBootstrap(params = {}) {
	return getRequest('/bootstrap/config/', params, { showLoading: false })
}

export function apiRegister(data) {
	return postRequest('/auth/register/', data)
}

export function apiLogin(data) {
	return postRequest('/auth/login/', data)
}

export async function apiGoogleLogin(data = {}) {
	const payload = { remember: true, app_id: APP_ID, ...data }
	if (!payload.id_token) {
		const token = await getGoogleIdToken()
		if (token) payload.id_token = token
	}
	if (payload.id_token) {
		delete payload.email
		delete payload.nickname
		delete payload.avatar_url
	} else if (!isFirebaseMock()) {
		return Promise.reject({ message: 'id_token required — link Google native SDK' })
	}
	return postRequest('/auth/google/', payload)
}

export async function apiGoogleBind(data = {}) {
	const payload = { app_id: APP_ID, ...data }
	if (!payload.id_token) {
		const token = await getGoogleIdToken()
		if (token) payload.id_token = token
	}
	if (payload.id_token) {
		delete payload.email
	} else if (!isFirebaseMock()) {
		return Promise.reject({ message: 'id_token required — link Google native SDK' })
	}
	return postRequest('/auth/google/bind/', payload)
}

export function apiGoogleUnbind() {
	return postRequest('/auth/google/unbind/', {})
}

export async function apiAppleLogin(data = {}) {
	const payload = { remember: true, app_id: APP_ID, ...data }
	if (!payload.identity_token && !payload.id_token) {
		const token = await getAppleIdentityToken()
		if (token) payload.identity_token = token
	}
	if (payload.id_token && !payload.identity_token) {
		payload.identity_token = payload.id_token
		delete payload.id_token
	}
	if (payload.identity_token) {
		delete payload.email
		delete payload.nickname
	} else if (!isFirebaseMock()) {
		return Promise.reject({ message: 'identity_token required — link Apple Sign In' })
	}
	return postRequest('/auth/apple/', payload)
}

export async function apiAppleBind(data = {}) {
	const payload = { app_id: APP_ID, ...data }
	if (!payload.identity_token && !payload.id_token) {
		const token = await getAppleIdentityToken()
		if (token) payload.identity_token = token
	}
	if (payload.id_token && !payload.identity_token) {
		payload.identity_token = payload.id_token
		delete payload.id_token
	}
	if (!payload.identity_token && !isFirebaseMock()) {
		return Promise.reject({ message: 'identity_token required — link Apple Sign In' })
	}
	return postRequest('/auth/apple/bind/', payload)
}

export function apiAppleUnbind() {
	return postRequest('/auth/apple/unbind/', {})
}

export function apiSmsSend(data = {}) {
	return postRequest('/auth/sms/send/', { app_id: APP_ID, ...data }, { showLoading: false })
}

export function apiSmsVerify(data = {}) {
	return postRequest('/auth/sms/verify/', { remember: true, app_id: APP_ID, ...data })
}

export function apiOAuthStart(provider) {
	return getRequest(`/auth/oauth/${provider}/start/`, {}, { showLoading: true })
}

export function apiInviteTrack(data = {}) {
	return postRequest('/auth/invite/track/', data, { showLoading: false, errorOutput: false })
}

export function apiPasswordForgot(data) {
	return postRequest('/auth/password/forgot/', { app_id: APP_ID, ...data })
}

export function apiPasswordReset(data) {
	return postRequest('/auth/password/reset/', { app_id: APP_ID, ...data })
}

export function apiDeleteAccount(data = {}) {
	return postRequest('/auth/account/delete/', { confirm: 'delete', ...data })
}

export function apiExportData() {
	return getRequest('/auth/account/export/', {}, { showLoading: true })
}

export function apiMe() {
	return getRequest('/auth/me/', {}, { showLoading: false })
}

export function apiOnboarding(data) {
	return postRequest('/auth/onboarding/', data)
}

export function apiLogout() {
	return postRequest('/auth/logout/', {})
}

export function apiHeartbeat() {
	return postRequest('/auth/heartbeat/', {}, { showLoading: false, errorOutput: false })
}

export function apiBadges() {
	return getRequest('/auth/badges/', {}, { showLoading: false, errorOutput: false })
}

export function apiFacebookLogin(data = {}) {
	return postRequest('/auth/facebook/', { remember: true, app_id: APP_ID, ...data })
}

