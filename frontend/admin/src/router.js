import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Layout from './views/Layout.vue'
import Dashboard from './views/Dashboard.vue'
import Users from './views/Users.vue'
import Chats from './views/Chats.vue'
import QuickMatch from './views/QuickMatch.vue'
import Groups from './views/Groups.vue'
import Community from './views/Community.vue'
import Funnel from './views/Funnel.vue'
import Orders from './views/Orders.vue'
import AppList from './views/AppList.vue'
import Safety from './views/Safety.vue'
import Review from './views/Review.vue'
import Firebase from './views/Firebase.vue'
import AdLinks from './views/AdLinks.vue'
import Analytics from './views/Analytics.vue'
import Country from './views/Country.vue'
import AdminMembers from './views/AdminMembers.vue'
import AdminRoles from './views/AdminRoles.vue'
import PushConfigs from './views/PushConfigs.vue'
import Providers from './views/Providers.vue'
import UserSafety from './views/UserSafety.vue'
import VerifyInquiries from './views/VerifyInquiries.vue'
import MatchQA from './views/MatchQA.vue'
import QaTemplates from './views/QaTemplates.vue'
import SwipeNight from './views/SwipeNight.vue'
import Matchmaker from './views/Matchmaker.vue'
import Campus from './views/Campus.vue'
import Select from './views/Select.vue'
import FaceToFace from './views/FaceToFace.vue'
import OpsBanners from './views/OpsBanners.vue'
import Matches from './views/Matches.vue'
import Ledgers from './views/Ledgers.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login, meta: { titleKey: 'login.title' } },
    {
      path: '/',
      component: Layout,
      children: [
        { path: '', component: Dashboard, meta: { titleKey: 'menu.dashboard', groupKey: 'menu.workspace', perm: 'dashboard' } },
        { path: 'users', component: Users, meta: { titleKey: 'menu.users', groupKey: 'menu.ops', perm: 'users' } },
        { path: 'chats', component: Chats, meta: { titleKey: 'menu.chats', groupKey: 'menu.ops', perm: 'chats' } },
        { path: 'matches', component: Matches, meta: { titleKey: 'menu.matches', groupKey: 'menu.ops', perm: 'matches' } },
        { path: 'ledgers', component: Ledgers, meta: { titleKey: 'menu.ledger', groupKey: 'menu.ops', perm: 'ledger' } },
        { path: 'quick-match', component: QuickMatch, meta: { titleKey: 'menu.quickMatch', groupKey: 'menu.ops', perm: 'quick_match' } },
        { path: 'groups', component: Groups, meta: { titleKey: 'menu.groups', groupKey: 'menu.ops', perm: 'groups' } },
        { path: 'community', component: Community, meta: { titleKey: 'menu.community', groupKey: 'menu.ops', perm: 'community' } },
        { path: 'funnel', component: Funnel, meta: { titleKey: 'menu.funnel', groupKey: 'menu.ops', perm: 'funnel' } },
        { path: 'orders', component: Orders, meta: { titleKey: 'menu.orders', groupKey: 'menu.ops', perm: 'orders' } },
        { path: 'firebase', component: Firebase, meta: { titleKey: 'menu.firebase', groupKey: 'menu.ops', perm: 'firebase' } },
        { path: 'swipe-night', component: SwipeNight, meta: { titleKey: 'menu.swipeNight', groupKey: 'menu.ops', perm: 'swipe_night' } },
        { path: 'matchmaker', component: Matchmaker, meta: { titleKey: 'menu.matchmaker', groupKey: 'menu.ops', perm: 'matchmaker' } },
        { path: 'campus', component: Campus, meta: { titleKey: 'menu.campus', groupKey: 'menu.ops', perm: 'campus' } },
        { path: 'select', component: Select, meta: { titleKey: 'menu.select', groupKey: 'menu.ops', perm: 'select' } },
        { path: 'face-to-face', component: FaceToFace, meta: { titleKey: 'menu.faceToFace', groupKey: 'menu.ops', perm: 'face_to_face' } },
        { path: 'ads', component: AdLinks, meta: { titleKey: 'menu.ads', groupKey: 'menu.growth', perm: 'ads' } },
        { path: 'safety', component: Safety, meta: { titleKey: 'menu.safety', groupKey: 'menu.growth', perm: 'safety' } },
        { path: 'user-safety', component: UserSafety, meta: { titleKey: 'menu.userSafety', groupKey: 'menu.growth', perm: 'user_safety' } },
        { path: 'verify', component: VerifyInquiries, meta: { titleKey: 'menu.verify', groupKey: 'menu.growth', perm: 'verify' } },
        { path: 'match-qa', component: MatchQA, meta: { titleKey: 'menu.matchQa', groupKey: 'menu.growth', perm: 'match_qa' } },
        { path: 'qa-templates', component: QaTemplates, meta: { titleKey: 'menu.qaTemplates', groupKey: 'menu.growth', perm: 'match_qa' } },
        { path: 'ops-banners', component: OpsBanners, meta: { titleKey: 'menu.opsBanner', groupKey: 'menu.growth', perm: 'ops_banner' } },
        { path: 'events', component: Analytics, meta: { titleKey: 'menu.events', groupKey: 'menu.growth', perm: 'events' } },
        { path: 'analytics', redirect: '/events' },
        { path: 'config', component: AppList, meta: { titleKey: 'menu.appConfig', groupKey: 'menu.config', perm: 'config' } },
        { path: 'app-list', redirect: '/config' },
        { path: 'push-configs', component: PushConfigs, meta: { titleKey: 'menu.pushConfigs', groupKey: 'menu.config', perm: 'push_configs' } },
        { path: 'providers', component: Providers, meta: { titleKey: 'menu.providers', groupKey: 'menu.config', perm: 'providers' } },
        { path: 'country', component: Country, meta: { titleKey: 'menu.country', groupKey: 'menu.config', perm: 'country' } },
        { path: 'review', component: Review, meta: { titleKey: 'menu.review', groupKey: 'menu.config', perm: 'review' } },
        { path: 'admin-members', component: AdminMembers, meta: { titleKey: 'menu.adminMembers', groupKey: 'menu.system', perm: 'admin_members' } },
        { path: 'admin-roles', component: AdminRoles, meta: { titleKey: 'menu.adminRoles', groupKey: 'menu.system', perm: 'admin_roles' } }
      ]
    }
  ]
})

router.beforeEach((to, from, next) => {
  if (to.path !== '/login' && !localStorage.getItem('admin_token')) {
    next('/login')
    return
  }
  const perm = to.meta && to.meta.perm
  if (perm) {
    const role = localStorage.getItem('admin_role') || ''
    let permissions = []
    try {
      permissions = JSON.parse(localStorage.getItem('admin_permissions') || '[]')
    } catch (e) {
      permissions = []
    }
    // Empty permissions DENY (not superadmin). Only super_admin / * / explicit keys pass.
    const ok = role === 'super_admin'
      || permissions.includes('*')
      || permissions.includes(perm)
      || (perm === 'config' && permissions.includes('app_list'))
    if (!ok) {
      next('/login')
      return
    }
  }
  next()
})

export default router
