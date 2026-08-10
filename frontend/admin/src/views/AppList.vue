<template>
  <PageContainer :title="t('appList.title')" :sub-title="t('appList.subtitle')">
    <div class="pro-toolbar">
      <el-button type="danger" size="small" @click="openCreate">{{ t('appList.add') }}</el-button>
      <el-button size="small" @click="load">{{ t('common.refresh') }}</el-button>
    </div>
    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="name" :label="t('appList.appName')" min-width="120" />
      <el-table-column prop="app_id" :label="t('appList.appId')" min-width="140" />
      <el-table-column prop="package_name" :label="t('appList.packageName')" min-width="140" />
      <el-table-column :label="t('appList.messagingMode')" width="120">
        <template #default="{ row }">
          {{ (row.product_profile && row.product_profile.messaging_mode) || 'any' }}
        </template>
      </el-table-column>
      <el-table-column :label="t('appList.modules')" min-width="260">
        <template #default="{ row }">
          <el-tag
            v-for="m in row.enabled_modules || []"
            :key="m"
            size="small"
            class="mod-tag"
          >{{ moduleLabel(m) }}</el-tag>
          <span v-if="!(row.enabled_modules || []).length" class="pro-hint">{{ t('appList.noModules') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button link type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="editingAppId ? t('appList.edit') : t('appList.add')"
      width="680px"
      destroy-on-close
    >
      <el-tabs v-model="editTab">
        <el-tab-pane :label="t('appList.tabBasic')" name="basic">
          <el-form label-width="140px" class="pro-form-wide">
            <el-form-item :label="t('appList.appId')">
              <el-input v-model="form.app_id" :disabled="!!editingAppId" placeholder="e.g. spark_main" />
            </el-form-item>
            <el-form-item :label="t('appList.appName')">
              <el-input v-model="form.name" />
            </el-form-item>
            <el-form-item :label="t('appList.packageName')">
              <el-input v-model="form.package_name" placeholder="e.g. app.spark" />
            </el-form-item>
            <el-form-item :label="t('config.tosUrl')">
              <el-input v-model="form.tos_url" />
            </el-form-item>
            <el-form-item :label="t('config.privacyUrl')">
              <el-input v-model="form.privacy_url" />
            </el-form-item>
            <el-form-item :label="t('appList.modules')">
              <el-checkbox-group v-model="form.enabled_modules">
                <el-checkbox
                  v-for="m in moduleCatalog"
                  :key="m.key"
                  :label="m.key"
                >{{ m.label }}</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('appList.tabProduct')" name="product">
          <el-form label-width="160px" class="pro-form-wide">
            <el-form-item :label="t('config.messagingMode')">
              <el-select v-model="form.product_profile.messaging_mode" style="width: 240px">
                <el-option label="any" value="any" />
                <el-option label="women_first" value="women_first" />
                <el-option label="qa_gate" value="qa_gate" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('config.matchOpenHours')">
              <el-input-number v-model="form.product_profile.match_open_hours" :min="0" />
            </el-form-item>
            <el-form-item :label="t('config.feedSameApp')">
              <el-switch v-model="form.product_profile.feed_same_app_only" />
            </el-form-item>
            <el-form-item :label="t('config.extendEnabled')">
              <el-switch v-model="form.product_profile.extend_enabled" />
            </el-form-item>
            <el-form-item :label="t('config.complimentEnabled')">
              <el-switch v-model="form.product_profile.compliment_enabled" />
            </el-form-item>
            <el-form-item :label="t('appList.qaGate')">
              <el-switch v-model="form.product_profile.qa_gate_enabled" />
            </el-form-item>
            <el-form-item :label="t('appList.dailyFeedCap')">
              <el-input-number v-model="form.product_profile.daily_feed_cap" :min="0" />
            </el-form-item>
            <el-form-item :label="t('config.displayPlus')">
              <el-input v-model="form.product_profile.display_tiers.plus" />
            </el-form-item>
            <el-form-item :label="t('config.displayGold')">
              <el-input v-model="form.product_profile.display_tiers.gold" />
            </el-form-item>
            <el-form-item :label="t('config.displayPlatinum')">
              <el-input v-model="form.product_profile.display_tiers.platinum" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('appList.tabDiscover')" name="discover" :disabled="!editingAppId && !form.app_id">
          <p class="pro-hint disc-hint">{{ t('appList.discoverHint') }}</p>
          <el-form label-width="160px" class="pro-form-wide">
            <el-form-item :label="t('funnel.region')">
              <el-select v-model="discoverCountry" style="width: 240px" @change="loadDiscover">
                <el-option
                  v-for="o in COUNTRY_OPTIONS"
                  :key="o.value"
                  :label="t(`regions.${o.value}`)"
                  :value="o.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('config.dailyLikes')">
              <el-input-number v-model="discover.daily_like_limit" :min="1" />
            </el-form-item>
            <el-form-item :label="t('config.matchExpireDays')">
              <el-input-number v-model="discover.match_expire_days" :min="1" />
            </el-form-item>
            <el-form-item :label="t('config.sayHiExpireDays')">
              <el-input-number v-model="discover.say_hi_expire_days" :min="1" />
            </el-form-item>
            <el-form-item :label="t('config.freeSayHiReplies')">
              <el-input-number v-model="discover.free_say_hi_replies" :min="0" />
            </el-form-item>
            <el-form-item :label="t('config.likeBonusThreshold')">
              <el-input-number v-model="discover.like_bonus_threshold" :min="0" />
            </el-form-item>
            <el-form-item :label="t('config.likeBonusCount')">
              <el-input-number v-model="discover.like_bonus_count" :min="0" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="t('appList.tabMaps')" name="maps">
          <p class="pro-hint disc-hint">{{ t('appList.mapsHint') }}</p>
          <el-form label-width="180px" class="pro-form-wide">
            <el-form-item :label="t('appList.amapEnabled')">
              <el-switch v-model="form.maps.amap.enabled" />
            </el-form-item>
            <el-form-item :label="t('appList.amapAndroidKey')">
              <el-input v-model="form.maps.amap.android_key" placeholder="Amap Android Key" />
            </el-form-item>
            <el-form-item :label="t('appList.amapIosKey')">
              <el-input v-model="form.maps.amap.ios_key" placeholder="Amap iOS Key" />
            </el-form-item>
            <el-form-item :label="t('appList.googleEnabled')">
              <el-switch v-model="form.maps.google.enabled" />
            </el-form-item>
            <el-form-item :label="t('appList.googleAndroidKey')">
              <el-input v-model="form.maps.google.android_key" placeholder="Google Maps Android Key" />
            </el-form-item>
            <el-form-item :label="t('appList.googleIosKey')">
              <el-input v-model="form.maps.google.ios_key" placeholder="Google Maps iOS Key" />
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="danger" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getAppList, saveAppList, deleteAppList, getAppModules,
  getDiscoverParams, saveDiscoverParams,
} from '../api'
import { COUNTRY_OPTIONS } from '../workspace'
import PageContainer from '../components/PageContainer.vue'

const { t } = useI18n()
const rows = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingAppId = ref('')
const editTab = ref('basic')
const moduleCatalog = ref([])
const discoverCountry = ref('*')

function emptyProduct() {
  return {
    messaging_mode: 'any',
    match_open_hours: null,
    feed_same_app_only: true,
    extend_enabled: false,
    compliment_enabled: false,
    qa_gate_enabled: false,
    daily_feed_cap: null,
    display_tiers: { plus: 'Plus', gold: 'Gold', platinum: 'Platinum' },
  }
}

function emptyMaps() {
  return {
    auto_rule: 'ip_cn_amap_else_google',
    amap: { enabled: true, android_key: '', ios_key: '' },
    google: { enabled: true, android_key: '', ios_key: '' },
  }
}

const form = reactive({
  app_id: '',
  name: '',
  package_name: '',
  tos_url: '',
  privacy_url: '',
  enabled_modules: [],
  product_profile: emptyProduct(),
  maps: emptyMaps(),
})

const discover = reactive({
  daily_like_limit: 50,
  match_expire_days: 7,
  say_hi_expire_days: 14,
  free_say_hi_replies: 2,
  like_bonus_threshold: 3,
  like_bonus_count: 3,
})

function moduleLabel(key) {
  const hit = moduleCatalog.value.find((m) => m.key === key)
  return hit ? hit.label : key
}

function resetForm() {
  form.app_id = ''
  form.name = ''
  form.package_name = ''
  form.tos_url = ''
  form.privacy_url = ''
  form.enabled_modules = moduleCatalog.value.filter((m) => !m.optional).map((m) => m.key)
  Object.assign(form.product_profile, emptyProduct())
  Object.assign(form.maps, emptyMaps())
  form.maps.amap = { ...emptyMaps().amap }
  form.maps.google = { ...emptyMaps().google }
  discoverCountry.value = '*'
  Object.assign(discover, {
    daily_like_limit: 50,
    match_expire_days: 7,
    say_hi_expire_days: 14,
    free_say_hi_replies: 2,
    like_bonus_threshold: 3,
    like_bonus_count: 3,
  })
}

async function loadCatalog() {
  try {
    const res = await getAppModules()
    moduleCatalog.value = (res.results && res.results.modules) || []
  } catch (e) {
    moduleCatalog.value = []
    ElMessage.error(e?.message || e?.response?.data?.detail || t('common.loadFailed'))
  }
}

async function load() {
  loading.value = true
  try {
    const res = await getAppList()
    rows.value = (res.results && res.results.list) || []
  } catch (e) {
    ElMessage.error(t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function loadDiscover() {
  const appId = editingAppId.value || form.app_id.trim()
  if (!appId) return
  try {
    const res = await getDiscoverParams({ app_id: appId, country: discoverCountry.value || '*' })
    Object.assign(discover, res.results || {})
  } catch (_) { /* keep defaults */ }
}

function openCreate() {
  editingAppId.value = ''
  editTab.value = 'basic'
  resetForm()
  dialogVisible.value = true
}

async function openEdit(row) {
  editingAppId.value = row.app_id
  editTab.value = 'basic'
  form.app_id = row.app_id
  form.name = row.name || ''
  form.package_name = row.package_name || ''
  form.tos_url = row.tos_url || ''
  form.privacy_url = row.privacy_url || ''
  form.enabled_modules = [...(row.enabled_modules || [])]
  const pp = row.product_profile || {}
  form.product_profile = {
    messaging_mode: pp.messaging_mode || 'any',
    match_open_hours: pp.match_open_hours ?? null,
    feed_same_app_only: pp.feed_same_app_only !== false,
    extend_enabled: !!pp.extend_enabled,
    compliment_enabled: !!pp.compliment_enabled,
    qa_gate_enabled: !!pp.qa_gate_enabled || pp.messaging_mode === 'qa_gate',
    daily_feed_cap: pp.daily_feed_cap ?? null,
    display_tiers: {
      plus: (pp.display_tiers && pp.display_tiers.plus) || 'Plus',
      gold: (pp.display_tiers && pp.display_tiers.gold) || 'Gold',
      platinum: (pp.display_tiers && pp.display_tiers.platinum) || 'Platinum',
    },
  }
  const maps = row.maps || emptyMaps()
  form.maps = {
    auto_rule: maps.auto_rule || 'ip_cn_amap_else_google',
    amap: {
      enabled: !(maps.amap && maps.amap.enabled === false),
      android_key: (maps.amap && maps.amap.android_key) || '',
      ios_key: (maps.amap && maps.amap.ios_key) || '',
    },
    google: {
      enabled: !(maps.google && maps.google.enabled === false),
      android_key: (maps.google && maps.google.android_key) || '',
      ios_key: (maps.google && maps.google.ios_key) || '',
    },
  }
  discoverCountry.value = '*'
  dialogVisible.value = true
  await loadDiscover()
}

async function save() {
  if (!form.app_id.trim() || !form.name.trim()) {
    ElMessage.warning(t('appList.required'))
    return
  }
  saving.value = true
  try {
    await saveAppList({
      app_id: form.app_id.trim(),
      name: form.name.trim(),
      package_name: form.package_name.trim(),
      tos_url: form.tos_url.trim(),
      privacy_url: form.privacy_url.trim(),
      enabled_modules: [...form.enabled_modules],
      product_profile: {
        messaging_mode: form.product_profile.messaging_mode,
        match_open_hours: form.product_profile.match_open_hours || null,
        feed_same_app_only: form.product_profile.feed_same_app_only,
        extend_enabled: form.product_profile.extend_enabled,
        compliment_enabled: form.product_profile.compliment_enabled,
        qa_gate_enabled: form.product_profile.qa_gate_enabled,
        daily_feed_cap: form.product_profile.daily_feed_cap || null,
        display_tiers: { ...form.product_profile.display_tiers },
      },
      maps: {
        auto_rule: form.maps.auto_rule || 'ip_cn_amap_else_google',
        amap: {
          enabled: !!form.maps.amap.enabled,
          android_key: (form.maps.amap.android_key || '').trim(),
          ios_key: (form.maps.amap.ios_key || '').trim(),
        },
        google: {
          enabled: !!form.maps.google.enabled,
          android_key: (form.maps.google.android_key || '').trim(),
          ios_key: (form.maps.google.ios_key || '').trim(),
        },
      },
    })
    // Discover is per app × country — save when editing or after create
    await saveDiscoverParams({
      app_id: form.app_id.trim(),
      country: discoverCountry.value || '*',
      daily_like_limit: discover.daily_like_limit,
      match_expire_days: discover.match_expire_days,
      say_hi_expire_days: discover.say_hi_expire_days,
      free_say_hi_replies: discover.free_say_hi_replies,
      like_bonus_threshold: discover.like_bonus_threshold,
      like_bonus_count: discover.like_bonus_count,
    })
    ElMessage.success(t('common.saved'))
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error((e && e.message) || t('common.loadFailed'))
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(t('appList.deleteConfirm', { name: row.name }), { type: 'warning' })
    await deleteAppList({ app_id: row.app_id })
    ElMessage.success(t('common.deleted'))
    load()
  } catch (_) { /* cancel */ }
}

onMounted(async () => {
  await loadCatalog()
  load()
})
</script>

<style scoped>
.mod-tag {
  margin: 2px 4px 2px 0;
}
.pro-hint {
  color: #909399;
  font-size: 12px;
}
.disc-hint {
  margin: 0 0 12px;
}
</style>
