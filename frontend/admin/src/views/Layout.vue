<template>
  <div class="pro-layout">
    <aside class="pro-sider" :class="{ 'is-collapsed': collapsed }">
      <div class="pro-sider-brand">
        <span class="pro-logo-mark">S</span>
        <span class="pro-sider-brand-text">Spark Admin</span>
      </div>
      <el-menu
        class="pro-sider-menu"
        :default-active="activePath"
        :collapse="collapsed"
        :collapse-transition="false"
        background-color="#001529"
        text-color="rgba(255,255,255,0.65)"
        active-text-color="#fff"
        router
      >
        <template v-for="group in visibleMenuGroups" :key="group.titleKey">
          <div v-if="!collapsed" class="pro-menu-group-title">{{ t(group.titleKey) }}</div>
          <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ t(item.titleKey) }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </aside>

    <div class="pro-layout-main" :class="{ 'is-collapsed': collapsed }">
      <header class="pro-header">
        <div class="pro-header-left">
          <button type="button" class="pro-collapse-btn" @click="collapsed = !collapsed" aria-label="fold">
            <el-icon :size="18">
              <Fold v-if="!collapsed" />
              <Expand v-else />
            </el-icon>
          </button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ t('common.spark') }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.groupKey">{{ t(route.meta.groupKey) }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ route.meta.titleKey ? t(route.meta.titleKey) : t('common.page') }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="pro-header-right">
          <el-select v-model="localeModel" size="small" class="pro-control-xs" @change="onLocaleChange">
            <el-option label="中文" value="zh-CN" />
            <el-option label="English" value="en" />
          </el-select>
          <span class="pro-env-badge">{{ envBadge }}</span>
          <el-dropdown trigger="click" @command="onUserCommand">
            <span class="pro-user-trigger">
              <el-avatar :size="28" style="background:#FF4B55">{{ avatarLetter }}</el-avatar>
              <span class="pro-user-name">{{ displayName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ displayName }} · {{ roleLabel }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">{{ t('common.logout') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <main class="pro-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  ArrowDown,
  DataAnalysis,
  Expand,
  Fold,
  Histogram,
  Key,
  Link,
  Location,
  Lock,
  Setting,
  ShoppingCart,
  User,
  UserFilled,
  Warning,
  Monitor,
  Connection,
  ChatDotRound,
  Bell,
  Grid,
  ChatLineRound,
  VideoCamera,
  FirstAidKit,
  Postcard,
  Moon,
  School,
  Star,
  Place,
  Ticket,
  Wallet,
  QuestionFilled
} from '@element-plus/icons-vue'
import { setLocale } from '../i18n'
import { getAdminInfo, getAppList } from '../api'
import { workspaceAppId, setAppOptions } from '../workspace'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const collapsed = ref(localStorage.getItem('admin_sider_collapsed') === '1')
const displayName = ref(localStorage.getItem('admin_username') || 'admin')
const role = ref(localStorage.getItem('admin_role') || 'operator')
const permissions = ref(JSON.parse(localStorage.getItem('admin_permissions') || '[]'))
const localeModel = ref(locale.value)

const activePath = computed(() => route.path)
const avatarLetter = computed(() => (displayName.value || 'A').charAt(0).toUpperCase())
const roleLabel = computed(() => t(`roles.${role.value}`) || role.value)
const envBadge = computed(() => {
  const m = import.meta.env.MODE || 'development'
  if (m === 'production') return t('common.prod')
  if (m === 'development') return t('common.dev')
  return m
})

const menuGroups = [
  {
    titleKey: 'menu.workspace',
    items: [{ path: '/', titleKey: 'menu.dashboard', icon: DataAnalysis, perm: 'dashboard' }]
  },
  {
    titleKey: 'menu.ops',
    items: [
      { path: '/users', titleKey: 'menu.users', icon: User, perm: 'users' },
      { path: '/chats', titleKey: 'menu.chats', icon: ChatDotRound, perm: 'chats' },
      { path: '/quick-match', titleKey: 'menu.quickMatch', icon: Connection, perm: 'quick_match' },
      { path: '/groups', titleKey: 'menu.groups', icon: ChatLineRound, perm: 'groups' },
      { path: '/community', titleKey: 'menu.community', icon: Grid, perm: 'community' },
      { path: '/funnel', titleKey: 'menu.funnel', icon: VideoCamera, perm: 'funnel' },
      { path: '/orders', titleKey: 'menu.orders', icon: ShoppingCart, perm: 'orders' },
      { path: '/matches', titleKey: 'menu.matches', icon: Connection, perm: 'matches' },
      { path: '/ledgers', titleKey: 'menu.ledger', icon: Wallet, perm: 'ledger' },
      { path: '/firebase', titleKey: 'menu.firebase', icon: Monitor, perm: 'firebase' },
      { path: '/swipe-night', titleKey: 'menu.swipeNight', icon: Moon, perm: 'swipe_night' },
      { path: '/matchmaker', titleKey: 'menu.matchmaker', icon: UserFilled, perm: 'matchmaker' },
      { path: '/campus', titleKey: 'menu.campus', icon: School, perm: 'campus' },
      { path: '/select', titleKey: 'menu.select', icon: Star, perm: 'select' },
      { path: '/face-to-face', titleKey: 'menu.faceToFace', icon: Place, perm: 'face_to_face' }
    ]
  },
  {
    titleKey: 'menu.growth',
    items: [
      { path: '/ads', titleKey: 'menu.ads', icon: Link, perm: 'ads' },
      { path: '/safety', titleKey: 'menu.safety', icon: Warning, perm: 'safety' },
      { path: '/user-safety', titleKey: 'menu.userSafety', icon: FirstAidKit, perm: 'user_safety' },
      { path: '/verify', titleKey: 'menu.verify', icon: Postcard, perm: 'verify' },
      { path: '/match-qa', titleKey: 'menu.matchQa', icon: QuestionFilled, perm: 'match_qa' },
      { path: '/qa-templates', titleKey: 'menu.qaTemplates', icon: Ticket, perm: 'match_qa' },
      { path: '/ops-banners', titleKey: 'menu.opsBanner', icon: Postcard, perm: 'ops_banner' },
      { path: '/events', titleKey: 'menu.events', icon: Histogram, perm: 'events' }
    ]
  },
  {
    titleKey: 'menu.config',
    items: [
      { path: '/config', titleKey: 'menu.appConfig', icon: Setting, perm: 'config' },
      { path: '/providers', titleKey: 'menu.providers', icon: Grid, perm: 'providers' },
      { path: '/push-configs', titleKey: 'menu.pushConfigs', icon: Bell, perm: 'push_configs' },
      { path: '/country', titleKey: 'menu.country', icon: Location, perm: 'country' },
      { path: '/review', titleKey: 'menu.review', icon: Lock, perm: 'review' }
    ]
  },
  {
    titleKey: 'menu.system',
    items: [
      { path: '/admin-members', titleKey: 'menu.adminMembers', icon: UserFilled, perm: 'admin_members' },
      { path: '/admin-roles', titleKey: 'menu.adminRoles', icon: Key, perm: 'admin_roles' }
    ]
  }
]

const visibleMenuGroups = computed(() => {
  const perms = permissions.value || []
  // Empty permissions DENY all menus (except super_admin / *).
  const isSuper = role.value === 'super_admin' || perms.includes('*')
  return menuGroups
    .map((g) => ({
      ...g,
        items: g.items.filter((item) =>
          isSuper
          || perms.includes(item.perm)
          || (item.perm === 'config' && perms.includes('app_list'))
        )
    }))
    .filter((g) => g.items.length)
})

function onLocaleChange(val) {
  setLocale(val)
}

async function refreshAppOptions() {
  try {
    const res = await getAppList({ app_id: workspaceAppId() })
    const list = (res.results && (res.results.list || res.results)) || res.results || []
    const rows = Array.isArray(list) ? list : []
    if (rows.length) {
      setAppOptions(rows.map((a) => ({
        label: a.name || a.app_id,
        value: a.app_id,
        name: a.name,
        app_id: a.app_id
      })))
    }
  } catch (e) {
    /* keep fallback APP_OPTIONS */
  }
}

async function refreshPermissionsForApp() {
  try {
    const res = await getAdminInfo({ app_id: workspaceAppId() })
    const data = res.results || {}
    if (data.permissions) {
      permissions.value = data.permissions
      localStorage.setItem('admin_permissions', JSON.stringify(data.permissions))
    }
    if (data.admin_app_ids) {
      localStorage.setItem('admin_app_ids', JSON.stringify(data.admin_app_ids))
    }
  } catch (e) {
    /* keep cached permissions */
  }
}

function onWorkspaceChange() {
  refreshPermissionsForApp()
}

function onUserCommand(cmd) {
  if (cmd === 'logout') {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_role')
    localStorage.removeItem('admin_permissions')
    localStorage.removeItem('admin_app_ids')
    router.push('/login')
  }
}

watch(collapsed, (v) => {
  localStorage.setItem('admin_sider_collapsed', v ? '1' : '0')
})

onMounted(() => {
  window.addEventListener('admin-workspace-change', onWorkspaceChange)
  refreshAppOptions()
  refreshPermissionsForApp()
})

onBeforeUnmount(() => {
  window.removeEventListener('admin-workspace-change', onWorkspaceChange)
})
</script>

<style scoped>
.pro-user-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--pro-space-sm);
  cursor: pointer;
  padding: var(--pro-space-xs) var(--pro-space-sm);
  border-radius: var(--pro-radius-sm);
}
.pro-user-trigger:hover {
  background: rgba(0, 0, 0, 0.04);
}
.pro-user-name {
  font-size: var(--pro-font-md);
  color: var(--pro-text);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
