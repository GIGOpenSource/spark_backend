import { getRequest } from '@/utils/http.js'

export function apiMapsGeocode(q) {
	return getRequest('/maps/geocode/', { q }, { showLoading: false })
}

export function apiMapsRegeo(lat, lng) {
	return getRequest('/maps/regeo/', { lat, lng }, { showLoading: false })
}
