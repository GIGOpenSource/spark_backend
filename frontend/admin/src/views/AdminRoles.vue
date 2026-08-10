<template>
  <PageContainer :title="t('adminRoles.title')" :sub-title="t('adminRoles.subtitle')">
    <WorkspaceFilter :show-country="false" :include-all="false" @change="onAppChange">
      <el-button type="danger" :loading="saving" @click="save">{{ t('adminRoles.save') }}</el-button>
    </WorkspaceFilter>

    <el-row :gutter="16">
      <el-col :span="8">
        <el-menu :default-active="activeRole" @select="onSelectRole">
          <el-menu-item v-for="r in roles" :key="r.key" :index="r.key">
            <span>{{ roleLabel(r.key) }}</span>
            <span class="role-key">{{ r.key }}</span>
          </el-menu-item>
        </el-menu>
      </el-col>
      <el-col :span="16">
        <div class="role-head">
          <h3>{{ currentLabel }} · {{ currentAppLabel }}</h3>
          <p>{{ currentDesc }}</p>
        </div>
        <el-checkbox
          v-model="checkAll"
          :indeterminate="indeterminate"
          @change="onCheckAll"
        >{{ t('adminRoles.selectAll') }}</el-checkbox>
        <el-divider />
        <el-checkbox-group v-model="selected" @change="onCheckedChange">
          <el-checkbox
            v-for="p in permissionOptions"
            :key="p.key"
            :label="p.key"
            style="display:block;margin:8px 0"
          >{{ permLabel(p.key) }}</el-checkbox>
        </el-checkbox-group>
      </el-col>
    </el-row>
  </PageContainer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getAdminRoles, saveAdminRolePermissions } from '../api'
import { workspaceAppId, getAppOptions, requireConcreteAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

/** Align with backend tools.admin_rbac.ALL_PERMISSIONS */
const PERM_MENU_KEY = {
  dashboard: 'menu.dashboard',
  users: 'menu.users',
  chats: 'menu.chats',
  quick_match: 'menu.quickMatch',
  groups: 'menu.groups',
  community: 'menu.community',
  funnel: 'menu.funnel',
  orders: 'menu.orders',
  firebase: 'menu.firebase',
  ads: 'menu.ads',
  safety: 'menu.safety',
  user_safety: 'menu.userSafety',
  verify: 'menu.verify',
  match_qa: 'menu.matchQa',
  swipe_night: 'menu.swipeNight',
  matchmaker: 'menu.matchmaker',
  campus: 'menu.campus',
  select: 'menu.select',
  face_to_face: 'menu.faceToFace',
  ops_banner: 'menu.opsBanner',
  matches: 'menu.matches',
  ledger: 'menu.ledger',
  events: 'menu.events',
  config: 'menu.appConfig',
  push_configs: 'menu.pushConfigs',
  providers: 'menu.providers',
  country: 'menu.country',
  review: 'menu.review',
  admin_members: 'menu.adminMembers',
  admin_roles: 'menu.adminRoles'
}

const { t, te } = useI18n()
const roles = ref([])
const permissionOptions = ref([])
const activeRole = ref('operator')
const selected = ref([])
const checkAll = ref(false)
const indeterminate = ref(false)
const saving = ref(false)
const overrides = ref({})

function roleLabel(key) {
  const k = `roles.${key}`
  return te(k) ? t(k) : key
}

function permLabel(key) {
  const menuKey = PERM_MENU_KEY[key]
  return menuKey && te(menuKey) ? t(menuKey) : key
}

const currentLabel = computed(() => roleLabel(activeRole.value))
const currentDesc = computed(() => {
  const k = `roleDesc.${activeRole.value}`
  return te(k) ? t(k) : ''
})
const currentAppLabel = computed(() => {
  const id = workspaceAppId()
  const hit = getAppOptions().find((o) => o.value === id)
  return hit ? hit.label : id
})

function syncChecks() {
  const allKeys = permissionOptions.value.map((p) => p.key)
  const n = selected.value.length
  checkAll.value = n === allKeys.length && n > 0
  indeterminate.value = n > 0 && n < allKeys.length
}

function onSelectRole(key) {
  activeRole.value = key
  const role = roles.value.find((r) => r.key === key)
  selected.value = [...(overrides.value[key] || (role && role.permissions) || [])]
  syncChecks()
}

function onCheckAll(val) {
  selected.value = val ? permissionOptions.value.map((p) => p.key) : []
  overrides.value[activeRole.value] = [...selected.value]
  syncChecks()
}

function onCheckedChange(val) {
  overrides.value[activeRole.value] = [...val]
  syncChecks()
}

async function load() {
  try {
    const res = await getAdminRoles({ app_id: workspaceAppId() })
    const data = res.results || {}
    roles.value = data.roles || []
    permissionOptions.value = data.permissions || []
    overrides.value = data.overrides || {}
    if (!activeRole.value && roles.value.length) activeRole.value = roles.value[0].key
    onSelectRole(activeRole.value)
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function onAppChange() {
  await load()
}

async function save() {
  const appId = requireConcreteAppId(() => ElMessage.warning(t('common.pickApp')))
  if (!appId) return
  saving.value = true
  try {
    await saveAdminRolePermissions({
      app_id: appId,
      role: activeRole.value,
      permissions: selected.value
    })
    ElMessage.success(t('adminRoles.saved', { app: currentAppLabel.value }))
    await load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.role-key {
  margin-left: var(--pro-space-sm);
  color: var(--pro-text-secondary);
  font-size: var(--pro-font-xs);
}
.role-head h3 {
  margin: 0 0 var(--pro-space-xs);
  font-size: var(--pro-font-lg);
  font-weight: 600;
  line-height: var(--pro-line-title);
}
.role-head p {
  margin: 0 0 var(--pro-space-md);
  color: var(--pro-text-secondary);
  font-size: var(--pro-font-sm);
}
</style>
