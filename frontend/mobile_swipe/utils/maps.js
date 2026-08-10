/**
 * Maps + location helpers.
 * Provider comes from bootstrap.maps (CN mainland → amap, else google).
 */
import { apiProfileUpdate } from '@/api/profile.js'
import { apiMapsRegeo } from '@/api/maps.js'

const REPORT_TTL_MS = 10 * 60 * 1000
let reporting = false

export function getMapsBootstrap() {
	const boot = uni.getStorageSync('bootstrap') || {}
	return boot.maps || {}
}

export function getMapProvider() {
	const maps = getMapsBootstrap()
	return maps.provider === 'amap' ? 'amap' : 'google'
}

export function getCoordType() {
	const maps = getMapsBootstrap()
	if (maps.coord_type === 'gcj02' || maps.coord_type === 'wgs84') return maps.coord_type
	return getMapProvider() === 'amap' ? 'gcj02' : 'wgs84'
}

export function getCurrentPosition() {
	const type = getCoordType()
	return new Promise((resolve, reject) => {
		uni.getLocation({
			type,
			isHighAccuracy: true,
			success: (res) => resolve({
				lat: res.latitude,
				lng: res.longitude,
				type,
			}),
			fail: (err) => reject(err),
		})
	})
}

/**
 * Capture device location and upload lat/lng (optionally city via reverse geocode).
 * Silent on permission denial / network errors.
 */
export async function reportLocation(options = {}) {
	const { force = false, updateCity = false } = options
	const token = uni.getStorageSync('token')
	if (!token) return null
	const last = Number(uni.getStorageSync('maps_last_report_at') || 0)
	if (!force && last && Date.now() - last < REPORT_TTL_MS) return null
	if (reporting) return null
	reporting = true
	try {
		const pos = await getCurrentPosition()
		const payload = { lat: pos.lat, lng: pos.lng }
		if (updateCity) {
			try {
				const re = await apiMapsRegeo(pos.lat, pos.lng)
				const city = re && re.results && re.results.city
				if (city) payload.city = city
			} catch (_) { /* ignore regeo failures */ }
		}
		await apiProfileUpdate(payload)
		uni.setStorageSync('maps_last_report_at', Date.now())
		uni.setStorageSync('maps_last_coords', { lat: pos.lat, lng: pos.lng })
		return { ...pos, city: payload.city || '' }
	} catch (_) {
		return null
	} finally {
		reporting = false
	}
}

/** For edit profile: locate + reverse geocode without requiring silent TTL skip only. */
export async function locateWithCity() {
	const pos = await getCurrentPosition()
	let city = ''
	try {
		const re = await apiMapsRegeo(pos.lat, pos.lng)
		city = (re && re.results && re.results.city) || ''
	} catch (_) { /* keep empty city */ }
	return { ...pos, city }
}
