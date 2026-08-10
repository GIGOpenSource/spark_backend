import { postRequest } from '@/utils/http.js'
import { APP_ID } from '@/config/config.js'

export function apiEventsBatch(events) {
	return postRequest('/events/batch/', { events, app_id: APP_ID }, { showLoading: false, errorOutput: false })
}

export function apiAttribution(data = {}) {
	return postRequest('/events/attribution/', { app_id: APP_ID, ...data }, { showLoading: false, errorOutput: false })
}
