import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token') || ''
  config.headers.token = token
  return config
})

function clearAdminSession() {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_role')
  localStorage.removeItem('admin_permissions')
  localStorage.removeItem('admin_app_ids')
}

http.interceptors.response.use(
  (resp) => {
    const body = resp.data || {}
    if (body.code && body.code !== 200 && body.code !== 201) {
      return Promise.reject(body)
    }
    return body
  },
  (err) => {
    const status = err && err.response && err.response.status
    const url = (err && err.config && err.config.url) || ''
    const isLogin = String(url).includes('/admin/login')
    if (status === 401 && !isLogin) {
      clearAdminSession()
      if (typeof window !== 'undefined' && !window.location.hash.includes('/login')) {
        window.location.hash = '#/login'
      }
    }
    return Promise.reject(err)
  }
)

export function adminLogin(data) {
  return http.post('/admin/login/', data)
}

export function getAdminInfo(params) {
  return http.get('/admin/info/', { params })
}

export function getDashboard(params) {
  return http.get('/spark-admin/dashboard/', { params })
}

export function getUsers(params) {
  return http.get('/spark-admin/users/', { params })
}

export function getUserDetail(params) {
  return http.get('/spark-admin/users/detail/', { params })
}

export function getChats(params) {
  return http.get('/spark-admin/chats/', { params })
}

export function getChatMessages(params) {
  return http.get('/spark-admin/chats/messages/', { params })
}

export function getFunnel(params) {
  return http.get('/spark-admin/funnel/', { params })
}

export function createFunnel(data) {
  return http.post('/spark-admin/funnel/', data)
}

export function downloadFunnelImportTemplate() {
  return http.get('/spark-admin/funnel-import-template/', {
    responseType: 'blob'
  })
}

export function importFunnelRobots(formData) {
  return http.post('/spark-admin/funnel-import/', formData, {
    timeout: 120000
  })
}

export function getOrders(params) {
  return http.get('/spark-admin/orders/', { params })
}

export function getAppConfig(params) {
  return http.get('/spark-admin/app-config/', { params })
}

export function saveAppConfig(data) {
  return http.post('/spark-admin/app-config/', data)
}

export function getProductProfile(params) {
  return http.get('/spark-admin/product-profile/', { params })
}

export function saveProductProfile(data) {
  return http.post('/spark-admin/product-profile/', data)
}

export function getAppList(params) {
  return http.get('/spark-admin/app-list/', { params })
}

export function saveAppList(data) {
  return http.post('/spark-admin/app-list/', data)
}

export function deleteAppList(params) {
  return http.delete('/spark-admin/app-list/', { params })
}

export function getAppModules(params) {
  return http.get('/spark-admin/app-modules/', { params })
}

export function getDiscoverParams(params) {
  return http.get('/spark-admin/discover-params/', { params })
}

export function saveDiscoverParams(data) {
  return http.post('/spark-admin/discover-params/', data)
}

export function getReview(params) {
  return http.get('/spark-admin/review-mode/', { params })
}

export function saveReview(data) {
  return http.post('/spark-admin/review-mode/', data)
}

export function getSafety(params) {
  return http.get('/spark-admin/safety/', { params })
}

export function saveSafety(data) {
  return http.post('/spark-admin/safety/', data)
}

export function userAction(data) {
  return http.post('/spark-admin/users/action/', data)
}

export function getFirebaseUsers(params) {
  return http.get('/spark-admin/firebase/users/', { params })
}

export function getFirebaseOrders(params) {
  return http.get('/spark-admin/firebase/orders/', { params })
}

export function getFirebasePayments(params) {
  return http.get('/spark-admin/firebase/payments/', { params })
}

export function getCountryConfig(params) {
  return http.get('/spark-admin/country-config/', { params })
}

export function saveCountryConfig(data) {
  return http.post('/spark-admin/country-config/', data)
}

export function getSkus(params) {
  return http.get('/spark-admin/skus/', { params })
}

export function saveSku(data) {
  return http.post('/spark-admin/skus/', data)
}

export function getEventsDict(params) {
  return http.get('/spark-admin/events/dict/', { params })
}

export function getAnalyticsOverview(params) {
  return http.get('/spark-admin/analytics/overview/', { params })
}

export function getAnalyticsEvents(params) {
  return http.get('/spark-admin/analytics/events/', { params })
}

export function getAnalyticsFunnel(params) {
  return http.get('/spark-admin/analytics/funnel/', { params })
}

export function getAnalyticsStream(params) {
  return http.get('/spark-admin/analytics/stream/', { params })
}

export function getPushConfigs(params) {
  return http.get('/spark-admin/push-configs/', { params })
}

export function createPushConfig(data) {
  return http.post('/spark-admin/push-configs/', data)
}

export function updatePushConfig(id, data) {
  return http.put(`/spark-admin/push-configs/${id}/`, data)
}

export function deletePushConfig(id) {
  return http.delete(`/spark-admin/push-configs/${id}/`)
}

export function getProviders(params) {
  return http.get('/spark-admin/providers/', { params })
}

export function getProviderDetail(providerKey, params) {
  return http.get(`/spark-admin/providers/${providerKey}/`, { params })
}

export function saveProvider(providerKey, data) {
  return http.post(`/spark-admin/providers/${providerKey}/`, data)
}

export function testProvider(providerKey, data) {
  return http.post(`/spark-admin/providers/${providerKey}/test/`, data || {})
}

export function getGoogleAdsCampaigns(params) {
  return http.get('/spark-admin/google-ads/campaigns/', { params })
}

export function syncGoogleAdsCampaigns(data) {
  return http.post('/spark-admin/google-ads/sync/', data || {})
}

export function getFacebookAdsCampaigns(params) {
  return http.get('/spark-admin/facebook-ads/campaigns/', { params })
}

export function syncFacebookAdsCampaigns(data) {
  return http.post('/spark-admin/facebook-ads/sync/', data || {})
}

export function getAdAttributions(params) {
  return http.get('/spark-admin/ad-attributions/', { params })
}

export function resolveAdAttribution(data) {
  return http.post('/spark-admin/ad-attributions/resolve/', data || {})
}

export function getFunnelAbcRules(params) {
  return http.get('/spark-admin/funnel-abc-rule/', { params })
}

export function createFunnelAbcRule(data) {
  return http.post('/spark-admin/funnel-abc-rule/', data)
}

export function updateFunnelAbcRule(id, data) {
  return http.put(`/spark-admin/funnel-abc-rule/${id}/`, data)
}

export function deleteFunnelAbcRule(id) {
  return http.delete(`/spark-admin/funnel-abc-rule/${id}/`)
}

export function recomputeFunnelGrades(data) {
  return http.post('/spark-admin/funnel-recompute/', data)
}

export function getRobotRecommendLists(params) {
  return http.get('/spark-admin/robot-recommend-lists/', { params })
}

export function saveRobotRecommendList(data) {
  return http.post('/spark-admin/robot-recommend-lists/', data)
}

export function deleteRobotRecommendList(id) {
  return http.delete(`/spark-admin/robot-recommend-lists/${id}/`)
}

export function getQuickMatchAdmin(params) {
  return http.get('/spark-admin/quick-match/', { params })
}

export function quickMatchAction(data) {
  return http.post('/spark-admin/quick-match/action/', data)
}

export function getGroupsAdmin(params) {
  return http.get('/spark-admin/groups/', { params })
}

export function getGroupAdminDetail(id, params) {
  return http.get(`/spark-admin/groups/${id}/`, { params })
}

export function updateGroupAdmin(id, data) {
  return http.post(`/spark-admin/groups/${id}/`, data)
}

export function getTopicsAdmin(params) {
  return http.get('/spark-admin/topics/', { params })
}

export function saveTopicAdmin(data) {
  return http.post('/spark-admin/topics/', data)
}

export function getPostsAdmin(params) {
  return http.get('/spark-admin/posts/', { params })
}

export function updatePostAdmin(data) {
  return http.post('/spark-admin/posts/', data)
}

export function getAdminMembers(params) {
  return http.get('/admin/members/', { params })
}

export function saveAdminMember(data) {
  return http.post('/admin/members/', data)
}

export function toggleAdminMember(id) {
  return http.post(`/admin/members/${id}/toggle-status/`)
}

export function getAdminRoles(params) {
  return http.get('/admin/roles/', { params })
}

export function saveAdminRolePermissions(data) {
  return http.post('/admin/roles/', data)
}

export function getUserSafety(params) {
  return http.get('/spark-admin/user-safety/', { params })
}
export function userSafetyAction(data) {
  return http.post('/spark-admin/user-safety/', data)
}
export function getVerifyInquiries(params) {
  return http.get('/spark-admin/verify-inquiries/', { params })
}
export function verifyInquiryAction(data) {
  return http.post('/spark-admin/verify-inquiries/', data)
}
export function getMatchQa(params) {
  return http.get('/spark-admin/match-qa/', { params })
}
export function getQaTemplates(params) {
  return http.get('/spark-admin/qa-templates/', { params })
}
export function saveQaTemplate(data) {
  return http.post('/spark-admin/qa-templates/', data)
}
export function getSwipeNight(params) {
  return http.get('/spark-admin/swipe-night/', { params })
}
export function postSwipeNight(data) {
  return http.post('/spark-admin/swipe-night/', data)
}
export function swipeNightAction(data) {
  return http.post('/spark-admin/swipe-night/action/', data)
}
export function getMatchmaker(params) {
  return http.get('/spark-admin/matchmaker/', { params })
}
export function matchmakerAction(data) {
  return http.post('/spark-admin/matchmaker/', data)
}
export function getCampusAdmin(params) {
  return http.get('/spark-admin/campus/', { params })
}
export function campusAction(data) {
  return http.post('/spark-admin/campus/', data)
}
export function getSelectAdmin(params) {
  return http.get('/spark-admin/select/', { params })
}
export function selectAction(data) {
  return http.post('/spark-admin/select/', data)
}
export function getFaceToFace(params) {
  return http.get('/spark-admin/face-to-face/', { params })
}
export function faceToFaceAction(data) {
  return http.post('/spark-admin/face-to-face/', data)
}
export function getOpsBanners(params) {
  return http.get('/spark-admin/ops-banners/', { params })
}
export function opsBannerAction(data) {
  return http.post('/spark-admin/ops-banners/', data)
}
export function getMatches(params) {
  return http.get('/spark-admin/matches/', { params })
}
export function matchesAction(data) {
  return http.post('/spark-admin/matches/action/', data)
}
export function getLedgers(params) {
  return http.get('/spark-admin/ledgers/', { params })
}
export function ledgerAction(data) {
  return http.post('/spark-admin/ledgers/', data)
}

export default http
