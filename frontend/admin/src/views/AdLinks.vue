<template>
  <PageContainer :title="t('ads.title')" :sub-title="t('ads.subtitle')">
    <WorkspaceFilter @change="onWorkspaceChange" />
    <el-tabs v-model="tab" @tab-change="onTab">
      <el-tab-pane :label="t('ads.tabLinks')" name="links">
        <div class="pro-toolbar">
          <el-input v-model="form.name" size="small" :placeholder="t('ads.name')" class="pro-control-md" />
          <el-input v-model="form.deep_link" size="small" :placeholder="t('ads.deepLink')" class="pro-control-xl" />
          <el-input v-model="form.tag" size="small" :placeholder="t('ads.tag')" class="pro-control-sm" />
          <el-input v-model="form.campaign_id" size="small" :placeholder="t('ads.campaignId')" class="pro-control-md" />
          <el-select v-model="form.source" size="small" class="pro-control-sm">
            <el-option label="manual" value="manual" />
            <el-option label="google_ads" value="google_ads" />
            <el-option label="facebook_ads" value="facebook_ads" />
          </el-select>
          <el-button type="danger" size="small" @click="create">{{ t('ads.add') }}</el-button>
        </div>
        <el-table :data="rows" style="width:100%" v-loading="loadingLinks">
          <el-table-column prop="id" :label="t('common.id')" :width="72" />
          <el-table-column prop="name" :label="t('ads.name')" min-width="120" />
          <el-table-column prop="deep_link" :label="t('ads.link')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="tag" :label="t('ads.tag')" width="100" />
          <el-table-column prop="campaign_id" :label="t('ads.campaignId')" width="140" />
          <el-table-column prop="source" :label="t('ads.source')" width="110" />
          <el-table-column prop="is_active" :label="t('ads.active')" width="90" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('ads.tabCampaigns')" name="campaigns">
        <p class="pro-hint">{{ t('ads.campaignsHint') }}</p>
        <div class="pro-toolbar">
          <el-button type="danger" size="small" :loading="syncing" @click="syncCampaigns">
            {{ t('ads.sync') }}
          </el-button>
          <el-button size="small" :loading="loadingCampaigns" @click="loadCampaigns">
            {{ t('ads.refresh') }}
          </el-button>
          <el-tag v-if="campaignMeta.customer_id" type="info" size="small">
            Customer: {{ campaignMeta.customer_id }}
          </el-tag>
          <el-tag v-if="campaignMeta.synced_at" type="success" size="small" effect="plain">
            {{ t('ads.syncedAt') }}: {{ formatTime(campaignMeta.synced_at) }}
          </el-tag>
          <el-tag v-if="campaignMeta.configured === false" type="warning" size="small">
            {{ t('ads.notConfigured') }}
          </el-tag>
        </div>
        <el-table :data="campaigns" style="width:100%" v-loading="loadingCampaigns">
          <el-table-column prop="campaign_id" :label="t('ads.campaignId')" width="140" fixed>
            <template #default="{ row }">
              <el-text type="primary" style="cursor:pointer;font-family:monospace" @click="copyId(row.campaign_id)">
                {{ row.campaign_id }}
              </el-text>
            </template>
          </el-table-column>
          <el-table-column prop="name" :label="t('ads.campaignName')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="status" :label="t('ads.status')" width="120" />
          <el-table-column prop="channel_type" :label="t('ads.channel')" width="120" />
          <el-table-column prop="impressions" :label="t('ads.impressions')" width="110" />
          <el-table-column prop="clicks" :label="t('ads.clicks')" width="90" />
          <el-table-column prop="cost" :label="t('ads.cost')" width="100">
            <template #default="{ row }">{{ formatCost(row) }}</template>
          </el-table-column>
          <el-table-column prop="conversions" :label="t('ads.conversions')" width="100" />
          <el-table-column :label="t('common.actions')" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="bindCampaign(row, 'google_ads')">{{ t('ads.bindLink') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('ads.tabFacebook')" name="facebook">
        <p class="pro-hint">{{ t('ads.facebookHint') }}</p>
        <div class="pro-toolbar">
          <el-button type="danger" size="small" :loading="syncingFb" @click="syncFacebook">
            {{ t('ads.syncFb') }}
          </el-button>
          <el-button size="small" :loading="loadingFb" @click="loadFacebook">
            {{ t('ads.refresh') }}
          </el-button>
          <el-tag v-if="fbMeta.ad_account_id" type="info" size="small">
            {{ fbMeta.ad_account_id }}
          </el-tag>
          <el-tag v-if="fbMeta.synced_at" type="success" size="small" effect="plain">
            {{ t('ads.syncedAt') }}: {{ formatTime(fbMeta.synced_at) }}
          </el-tag>
          <el-tag v-if="fbMeta.configured === false" type="warning" size="small">
            {{ t('ads.notConfiguredFb') }}
          </el-tag>
        </div>
        <el-table :data="fbCampaigns" style="width:100%" v-loading="loadingFb">
          <el-table-column prop="campaign_id" :label="t('ads.campaignId')" width="160" fixed>
            <template #default="{ row }">
              <el-text type="primary" style="cursor:pointer;font-family:monospace" @click="copyId(row.campaign_id)">
                {{ row.campaign_id }}
              </el-text>
            </template>
          </el-table-column>
          <el-table-column prop="name" :label="t('ads.campaignName')" min-width="180" show-overflow-tooltip />
          <el-table-column prop="status" :label="t('ads.status')" width="120" />
          <el-table-column prop="objective" :label="t('ads.objective')" width="140" />
          <el-table-column prop="impressions" :label="t('ads.impressions')" width="110" />
          <el-table-column prop="clicks" :label="t('ads.clicks')" width="90" />
          <el-table-column prop="spend" :label="t('ads.cost')" width="100">
            <template #default="{ row }">{{ Number(row.spend || row.cost || 0).toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="conversions" :label="t('ads.conversions')" width="100" />
          <el-table-column :label="t('common.actions')" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="bindCampaign(row, 'facebook_ads')">{{ t('ads.bindLink') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('ads.tabAttribution')" name="attribution">
        <p class="pro-hint">{{ t('ads.attributionHint') }}</p>
        <div class="pro-toolbar">
          <el-select v-model="attrFilters.status" size="small" clearable :placeholder="t('ads.status')" class="pro-control-sm" @change="loadAttributions">
            <el-option :label="t('ads.statusPending')" value="pending" />
            <el-option :label="t('ads.statusMatched')" value="matched" />
            <el-option :label="t('ads.statusResolved')" value="resolved" />
            <el-option :label="t('ads.statusDiscarded')" value="discarded" />
          </el-select>
          <el-select v-model="attrFilters.platform" size="small" clearable :placeholder="t('ads.platform')" class="pro-control-sm" @change="loadAttributions">
            <el-option label="Facebook" value="facebook" />
            <el-option label="Google" value="google" />
            <el-option label="Other" value="other" />
          </el-select>
          <el-input v-model="attrFilters.q" size="small" clearable :placeholder="t('ads.searchAttr')" class="pro-control-md" @keyup.enter="loadAttributions" />
          <el-button size="small" :loading="loadingAttr" @click="loadAttributions">{{ t('ads.refresh') }}</el-button>
          <el-button type="danger" size="small" :loading="matchingAll" @click="autoMatchAll">{{ t('ads.autoMatchAll') }}</el-button>
        </div>
        <el-table :data="attributions" style="width:100%" v-loading="loadingAttr">
          <el-table-column prop="id" :label="t('common.id')" width="72" />
          <el-table-column prop="platform" :label="t('ads.platform')" width="100" />
          <el-table-column prop="status" :label="t('ads.status')" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="campaign_id" :label="t('ads.campaignId')" width="140" show-overflow-tooltip />
          <el-table-column prop="campaign_name" :label="t('ads.campaignName')" min-width="140" show-overflow-tooltip />
          <el-table-column prop="click_id" :label="t('ads.clickId')" width="120" show-overflow-tooltip />
          <el-table-column prop="utm_source" label="utm_source" width="110" show-overflow-tooltip />
          <el-table-column prop="user_id" :label="t('ads.userId')" width="90" />
          <el-table-column prop="created_at" :label="t('common.createdAt') || 'Created'" width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="220" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="autoMatchOne(row)">{{ t('ads.autoMatch') }}</el-button>
              <el-button link type="success" @click="openResolve(row)">{{ t('ads.resolve') }}</el-button>
              <el-button link type="info" @click="discardOne(row)">{{ t('ads.discard') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="resolveDialog" :title="t('ads.resolve')" width="520px" destroy-on-close>
      <el-form label-width="120px" v-if="resolveForm.id">
        <el-form-item :label="t('ads.platform')">
          <el-select v-model="resolveForm.platform" style="width:100%">
            <el-option label="facebook" value="facebook" />
            <el-option label="google" value="google" />
            <el-option label="other" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('ads.campaignId')">
          <el-input v-model="resolveForm.campaign_id" />
        </el-form-item>
        <el-form-item :label="t('ads.userId')">
          <el-input v-model="resolveForm.user_id" placeholder="optional" />
        </el-form-item>
        <el-form-item :label="t('ads.note')">
          <el-input v-model="resolveForm.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="danger" :loading="resolving" @click="submitResolve">{{ t('ads.resolve') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import http, {
  getGoogleAdsCampaigns, syncGoogleAdsCampaigns,
  getFacebookAdsCampaigns, syncFacebookAdsCampaigns,
  getAdAttributions, resolveAdAttribution,
} from '../api'
import { getWorkspace, workspaceAppId, workspaceAppIdOrDefault } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const tab = ref('links')
const rows = ref([])
const campaigns = ref([])
const fbCampaigns = ref([])
const attributions = ref([])
const loadingLinks = ref(false)
const loadingCampaigns = ref(false)
const loadingFb = ref(false)
const loadingAttr = ref(false)
const syncing = ref(false)
const syncingFb = ref(false)
const matchingAll = ref(false)
const resolving = ref(false)
const resolveDialog = ref(false)
const campaignMeta = reactive({ customer_id: '', synced_at: null, configured: null })
const fbMeta = reactive({ ad_account_id: '', synced_at: null, configured: null })
const form = reactive({ name: '', deep_link: '', tag: '', campaign_id: '', source: 'manual' })
const attrFilters = reactive({ status: 'pending', platform: '', q: '' })
const resolveForm = reactive({ id: null, platform: 'facebook', campaign_id: '', user_id: '', note: '' })

function formatCost(row) {
  const c = row.cost != null ? row.cost : (row.cost_micros || 0) / 1e6
  return Number(c || 0).toFixed(2)
}

function formatTime(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

function statusTag(s) {
  if (s === 'resolved' || s === 'matched') return 'success'
  if (s === 'pending') return 'warning'
  return 'info'
}

async function load() {
  loadingLinks.value = true
  try {
    const ws = getWorkspace()
    const res = await http.get('/spark-admin/ad-links/', {
      params: { app_id: workspaceAppId(), country: ws.country },
    })
    rows.value = (res.results && res.results.list) || []
  } finally {
    loadingLinks.value = false
  }
}

async function loadCampaigns() {
  loadingCampaigns.value = true
  try {
    const res = await getGoogleAdsCampaigns({ app_id: workspaceAppId() })
    const data = res.results || {}
    campaigns.value = data.list || []
    campaignMeta.customer_id = data.customer_id || (campaigns.value[0] && campaigns.value[0].customer_id) || ''
    campaignMeta.synced_at = data.synced_at || null
    campaignMeta.configured = data.configured
  } catch (e) {
    ElMessage.error(e?.message || 'load campaigns failed')
  } finally {
    loadingCampaigns.value = false
  }
}

async function syncCampaigns() {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  syncing.value = true
  try {
    const res = await syncGoogleAdsCampaigns({ app_id: appId, with_metrics: true })
    const data = res.results || {}
    ElMessage.success(`${t('ads.syncOk')}: ${data.synced || 0}`)
    await loadCampaigns()
  } catch (e) {
    ElMessage.error(e?.message || t('ads.syncFail'))
  } finally {
    syncing.value = false
  }
}

async function loadFacebook() {
  loadingFb.value = true
  try {
    const res = await getFacebookAdsCampaigns({ app_id: workspaceAppId() })
    const data = res.results || {}
    fbCampaigns.value = data.list || []
    fbMeta.ad_account_id = data.ad_account_id || ''
    fbMeta.synced_at = data.synced_at || null
    fbMeta.configured = data.configured
  } catch (e) {
    ElMessage.error(e?.message || 'load facebook failed')
  } finally {
    loadingFb.value = false
  }
}

async function syncFacebook() {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  syncingFb.value = true
  try {
    const res = await syncFacebookAdsCampaigns({ app_id: appId })
    const data = res.results || {}
    ElMessage.success(`${t('ads.syncOk')}: ${data.synced || 0}`)
    await loadFacebook()
  } catch (e) {
    ElMessage.error(e?.message || t('ads.syncFail'))
  } finally {
    syncingFb.value = false
  }
}

async function loadAttributions() {
  loadingAttr.value = true
  try {
    const params = { app_id: workspaceAppId(), limit: 200 }
    if (attrFilters.status) params.status = attrFilters.status
    if (attrFilters.platform) params.platform = attrFilters.platform
    if (attrFilters.q) params.q = attrFilters.q
    const res = await getAdAttributions(params)
    attributions.value = (res.results && res.results.list) || []
  } catch (e) {
    ElMessage.error(e?.message || 'load attribution failed')
  } finally {
    loadingAttr.value = false
  }
}

async function autoMatchAll() {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  matchingAll.value = true
  try {
    const res = await resolveAdAttribution({
      app_id: appId,
      action: 'auto_match_all',
    })
    const data = res.results || {}
    ElMessage.success(`${t('ads.autoMatchOk')}: ${data.matched || 0}/${data.scanned || 0}`)
    await loadAttributions()
  } catch (e) {
    ElMessage.error(e?.message || 'auto match failed')
  } finally {
    matchingAll.value = false
  }
}

async function autoMatchOne(row) {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await resolveAdAttribution({
      app_id: appId,
      action: 'auto_match',
      id: row.id,
    })
    ElMessage.success(t('ads.autoMatchOk'))
    await loadAttributions()
  } catch (e) {
    ElMessage.error(e?.message || 'auto match failed')
  }
}

function openResolve(row) {
  resolveForm.id = row.id
  resolveForm.platform = row.platform || 'facebook'
  resolveForm.campaign_id = row.campaign_id || ''
  resolveForm.user_id = row.user_id || ''
  resolveForm.note = ''
  resolveDialog.value = true
}

async function submitResolve() {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  resolving.value = true
  try {
    await resolveAdAttribution({
      app_id: appId,
      action: 'resolve',
      id: resolveForm.id,
      status: 'resolved',
      platform: resolveForm.platform,
      campaign_id: resolveForm.campaign_id,
      user_id: resolveForm.user_id || undefined,
      note: resolveForm.note,
    })
    ElMessage.success(t('common.saved'))
    resolveDialog.value = false
    await loadAttributions()
  } catch (e) {
    ElMessage.error(e?.message || 'resolve failed')
  } finally {
    resolving.value = false
  }
}

async function discardOne(row) {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await resolveAdAttribution({
      app_id: appId,
      action: 'resolve',
      id: row.id,
      status: 'discarded',
      note: 'discarded by admin',
    })
    await loadAttributions()
  } catch (e) {
    ElMessage.error(e?.message || 'discard failed')
  }
}

async function create() {
  const ws = getWorkspace()
  await http.post('/spark-admin/ad-links/', {
    app_id: workspaceAppId(),
    country: ws.country,
    ...form,
  })
  ElMessage.success(t('common.created'))
  form.name = ''
  form.deep_link = ''
  form.tag = ''
  form.campaign_id = ''
  form.source = 'manual'
  load()
}

function bindCampaign(row, source) {
  form.campaign_id = String(row.campaign_id || '')
  form.name = form.name || row.name || `Campaign ${row.campaign_id}`
  form.tag = form.tag || `${source === 'facebook_ads' ? 'fb' : 'gads'}_${row.campaign_id}`
  form.source = source
  tab.value = 'links'
  ElMessage.success(t('ads.boundHint'))
}

function copyId(id) {
  const text = String(id || '')
  if (!text) return
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => ElMessage.success(t('ads.copied')))
  } else {
    ElMessage.info(text)
  }
}

function onWorkspaceChange() {
  load()
  if (tab.value === 'campaigns') loadCampaigns()
  if (tab.value === 'facebook') loadFacebook()
  if (tab.value === 'attribution') loadAttributions()
}

function onTab(name) {
  if (name === 'campaigns') loadCampaigns()
  if (name === 'facebook') loadFacebook()
  if (name === 'attribution') loadAttributions()
}

onMounted(load)
</script>

<style scoped>
.pro-hint {
  margin: 0 0 8px;
  color: #8c8c8c;
  font-size: 13px;
}
</style>
