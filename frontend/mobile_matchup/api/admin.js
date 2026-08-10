import { getRequest, postRequest, putRequest, deleteRequest } from '@/utils/http.js'

export function adminLogin(data) {
	return postRequest('/admin/login/', data)
}

export function adminDashboard(params = {}) {
	return getRequest('/spark-admin/dashboard/', params)
}

export function adminUsers(params = {}) {
	return getRequest('/spark-admin/users/', params)
}

export function adminFunnel(params = {}) {
	return getRequest('/spark-admin/funnel/', params)
}

export function adminFunnelCreate(data) {
	return postRequest('/spark-admin/funnel/', data)
}

export function adminFunnelUpdate(id, data) {
	return putRequest(`/spark-admin/funnel/${id}/`, data)
}

export function adminFunnelDelete(id) {
	return deleteRequest(`/spark-admin/funnel/${id}/`)
}

export function adminDiscoverParams(params = {}) {
	return getRequest('/spark-admin/discover-params/', params)
}

export function adminDiscoverSave(data) {
	return postRequest('/spark-admin/discover-params/', data)
}

export function adminSkus(params = {}) {
	return getRequest('/spark-admin/skus/', params)
}

export function adminOrders(params = {}) {
	return getRequest('/spark-admin/orders/', params)
}

export function adminAppConfig(params = {}) {
	return getRequest('/spark-admin/app-config/', params)
}

export function adminAppConfigSave(data) {
	return postRequest('/spark-admin/app-config/', data)
}

export function adminReviewMode(params = {}) {
	return getRequest('/spark-admin/review-mode/', params)
}

export function adminReviewSave(data) {
	return postRequest('/spark-admin/review-mode/', data)
}

export function adminSafety(params = {}) {
	return getRequest('/spark-admin/safety/', params)
}

export function adminAdLinks(params = {}) {
	return getRequest('/spark-admin/ad-links/', params)
}

export function adminFirebaseUsers(params = {}) {
	return getRequest('/spark-admin/firebase/users/', params)
}

export function adminFirebaseOrders(params = {}) {
	return getRequest('/spark-admin/firebase/orders/', params)
}

export function adminCountryConfig(params = {}) {
	return getRequest('/spark-admin/country-config/', params)
}
