/** Page-level workspace (App / Region). */

export const APP_ALL = '*'

/** Fallback labels when AppConfig API not yet loaded. */
export const APP_OPTIONS_FALLBACK = [
  { label: 'Spark', value: 'spark_main' },
  { label: 'bee', value: 'swipe_main' },
  { label: 'Ember', value: 'ember_main' },
  { label: 'MatchUp', value: 'matchup_main' },
  { label: 'Flick', value: 'flick_main' }
]

/** Mutable app list — prefer API/AppConfig via setAppOptions / refreshAppOptions. */
let _appOptions = [...APP_OPTIONS_FALLBACK]

export function getAppOptions() {
  return _appOptions.length ? _appOptions : APP_OPTIONS_FALLBACK
}

/** @deprecated Use getAppOptions(); kept for existing imports. */
export const APP_OPTIONS = APP_OPTIONS_FALLBACK

export function setAppOptions(list) {
  if (!Array.isArray(list) || !list.length) return getAppOptions()
  _appOptions = list.map((a) => ({
    label: a.label || a.name || a.app_id || a.value,
    value: a.value || a.app_id
  })).filter((o) => o.value)
  try {
    localStorage.setItem('admin_app_options', JSON.stringify(_appOptions))
  } catch (e) {
    /* ignore */
  }
  return _appOptions
}

export function hydrateAppOptionsFromCache() {
  try {
    const raw = JSON.parse(localStorage.getItem('admin_app_options') || '[]')
    if (Array.isArray(raw) && raw.length) {
      _appOptions = raw
    }
  } catch (e) {
    /* ignore */
  }
  return getAppOptions()
}

hydrateAppOptionsFromCache()

/** Filter options include「全部」; use getAppOptions() when binding specific apps. */
export const APP_FILTER_OPTIONS = [
  { label: 'All', value: APP_ALL },
  ...APP_OPTIONS_FALLBACK
]

export const REGION_ALL = '*'

/** 地区：全部 + 指定市场（展示文案走 i18n regions.*） */
export const COUNTRY_OPTIONS = [
  { value: REGION_ALL },
  { value: 'JP' },
  { value: 'IN' },
  { value: 'KR' },
  { value: 'US' },
  { value: 'CA' },
  { value: 'BR' },
  { value: 'CN' },
  { value: 'RU' },
  { value: 'EU' },
  { value: 'AF' }
]

export const LOCALE_ALL = '*'

/** 语言：全部 + 常用语种（展示文案走 i18n locales.*） */
export const LOCALE_OPTIONS = [
  { value: LOCALE_ALL },
  { value: 'en' },
  { value: 'zh' },
  { value: 'ja' },
  { value: 'ko' },
  { value: 'hi' },
  { value: 'pt' },
  { value: 'ru' },
  { value: 'es' },
  { value: 'fr' },
  { value: 'de' },
  { value: 'ar' }
]

export const PLATFORM_OPTIONS = [
  { label: 'iOS', value: 'ios' },
  { label: 'Android', value: 'android' }
]

export function getAccessibleAppIds() {
  try {
    const raw = JSON.parse(localStorage.getItem('admin_app_ids') || '[]')
    if (Array.isArray(raw) && raw.length) return raw
  } catch (e) {
    /* ignore */
  }
  return getAppOptions().map((o) => o.value)
}

/** App filter dropdown: optional「全部」 + accessible apps */
export function accessibleAppOptions({ includeAll = true } = {}) {
  const ids = new Set(getAccessibleAppIds())
  const opts = getAppOptions()
  const list = opts.filter((o) => ids.has(o.value))
  const apps = list.length ? list : opts
  return includeAll ? [{ label: 'All', value: APP_ALL }, ...apps] : apps
}

export function countryLabel(code) {
  const hit = COUNTRY_OPTIONS.find((o) => o.value === (code || REGION_ALL))
  return hit ? hit.value : (code || REGION_ALL)
}

export function localeLabel(code) {
  const hit = LOCALE_OPTIONS.find((o) => o.value === (code || LOCALE_ALL))
  return hit ? hit.value : (code || LOCALE_ALL)
}

export function getWorkspace() {
  const apps = getAccessibleAppIds()
  let app_id = localStorage.getItem('admin_app_id') || APP_ALL
  // allow 全部; otherwise must be accessible
  if (app_id !== APP_ALL && apps.length && !apps.includes(app_id)) {
    app_id = APP_ALL
    localStorage.setItem('admin_app_id', app_id)
  }
  let country = localStorage.getItem('admin_country') || REGION_ALL
  const validRegions = new Set(COUNTRY_OPTIONS.map((o) => o.value))
  if (!validRegions.has(country)) {
    country = REGION_ALL
    localStorage.setItem('admin_country', country)
  }
  return { app_id, country }
}

export function workspaceAppId() {
  return getWorkspace().app_id
}

export function workspaceCountry() {
  return getWorkspace().country
}

/**
 * Concrete app for write APIs. Returns null when workspace is「全部」
 * (no silent remap to first app — caller must refuse or force pick).
 */
export function workspaceAppIdOrDefault(fallback = null) {
  const id = workspaceAppId()
  if (id === APP_ALL || !id) return fallback || null
  return id
}

/** Require a concrete App for writes; returns null and optionally warns. */
export function requireConcreteAppId(notify) {
  const id = workspaceAppId()
  if (!id || id === APP_ALL) {
    if (typeof notify === 'function') notify()
    return null
  }
  return id
}

export function setWorkspace({ app_id, country } = {}) {
  if (app_id != null) localStorage.setItem('admin_app_id', app_id)
  if (country != null) localStorage.setItem('admin_country', country)
  const detail = getWorkspace()
  window.dispatchEvent(new CustomEvent('admin-workspace-change', { detail }))
  return detail
}

export function setAccessibleApps(appIds) {
  const ids = Array.isArray(appIds) && appIds.length
    ? appIds
    : getAppOptions().map((o) => o.value)
  localStorage.setItem('admin_app_ids', JSON.stringify(ids))
  const ws = getWorkspace()
  if (ws.app_id !== APP_ALL && !ids.includes(ws.app_id)) {
    setWorkspace({ app_id: APP_ALL })
  }
  return ids
}
