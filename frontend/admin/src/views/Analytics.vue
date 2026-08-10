<template>
  <PageContainer :title="t('analytics.title')" :sub-title="t('analytics.subtitle')" :ghost="true">
    <WorkspaceFilter :show-country="false" @change="reloadAll">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        size="small"
        class="dash-daterange"
        range-separator="~"
        :start-placeholder="t('dashboard.dateStart')"
        :end-placeholder="t('dashboard.dateEnd')"
        value-format="YYYY-MM-DD"
        @change="reloadAll"
      />
      <el-button type="danger" size="small" :loading="loading" @click="reloadAll">{{ t('common.refresh') }}</el-button>
    </WorkspaceFilter>

    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="12" :sm="8" :md="6" v-for="item in kpiCards" :key="item.key">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">{{ item.label }}</div>
          <div class="kpi-value">{{ item.value }}</div>
          <div class="kpi-delta" v-if="item.deltaText" :class="item.deltaClass">
            {{ t('analytics.vsPrev') }} {{ item.deltaText }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-tabs v-model="tab" @tab-change="onTab">
      <el-tab-pane :label="t('analytics.tabOverview')" name="overview">
        <el-row :gutter="16">
          <el-col :xs="24" :md="14">
            <el-card shadow="never" class="panel-card">
              <template #header>
                <div class="panel-head">
                  <span>{{ t('analytics.eventTrend') }}</span>
                  <span class="panel-unit">{{ t('dashboard.unitCount') }}</span>
                </div>
              </template>
              <div class="trend">
                <div
                  v-for="row in trend"
                  :key="row.day"
                  class="bar-col"
                  :title="`${row.day}: ${row.count} / ${row.users} users`"
                >
                  <div class="bar-val">{{ fmtCompact(row.count) }}</div>
                  <div class="bar" :style="{ height: barHeight(row.count, trendCounts) + 'px' }" />
                  <div class="day">{{ shortDay(row.day) }}</div>
                </div>
                <div v-if="!trend.length && !loading" class="empty">{{ t('analytics.noData') }}</div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="24" :md="10">
            <el-card shadow="never" class="panel-card">
              <template #header>{{ t('analytics.topEvents') }}</template>
              <el-table :data="topEvents" size="small" style="width:100%" max-height="280">
                <el-table-column prop="event" :label="t('events.eventName')" min-width="120" show-overflow-tooltip />
                <el-table-column prop="label_zh" :label="t('events.labelZh')" min-width="120" show-overflow-tooltip />
                <el-table-column prop="count" :label="t('events.count')" width="90" align="right" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
        <el-row :gutter="16" class="section-row">
          <el-col :xs="24" :md="12">
            <el-card shadow="never" class="panel-card">
              <template #header>{{ t('analytics.byLocale') }}</template>
              <el-table :data="byLocale" size="small" style="width:100%">
                <el-table-column prop="locale" :label="t('common.language')" />
                <el-table-column prop="count" :label="t('events.count')" width="100" align="right" />
              </el-table>
            </el-card>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-card shadow="never" class="panel-card">
              <template #header>{{ t('analytics.byVersion') }}</template>
              <el-table :data="byVersion" size="small" style="width:100%">
                <el-table-column prop="version" :label="t('analytics.version')" />
                <el-table-column prop="count" :label="t('events.count')" width="100" align="right" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane :label="t('analytics.tabEvents')" name="events">
        <el-table :data="eventRows" v-loading="loadingEvents" style="width:100%">
          <el-table-column type="index" width="60" />
          <el-table-column prop="event" :label="t('events.eventName')" min-width="180" />
          <el-table-column prop="label_zh" :label="t('events.labelZh')" min-width="160" />
          <el-table-column prop="count" :label="t('events.count')" width="120" sortable />
          <el-table-column prop="users" :label="t('analytics.users')" width="120" sortable />
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('analytics.tabFunnel')" name="funnel">
        <div class="pro-toolbar">
          <el-input
            v-model="funnelStepsInput"
            size="small"
            class="pro-control-xl"
            :placeholder="t('analytics.funnelStepsPh')"
          />
          <el-button type="danger" size="small" :loading="loadingFunnel" @click="loadFunnel">
            {{ t('analytics.runFunnel') }}
          </el-button>
        </div>
        <el-table :data="funnelSteps" v-loading="loadingFunnel" style="width:100%">
          <el-table-column prop="step" label="#" width="60" />
          <el-table-column prop="event" :label="t('events.eventName')" min-width="180" />
          <el-table-column prop="users" :label="t('analytics.users')" width="100" />
          <el-table-column prop="events" :label="t('events.count')" width="100" />
          <el-table-column :label="t('analytics.convPrev')" width="120">
            <template #default="{ row }">{{ fmtPct(row.conversion_from_prev) }}</template>
          </el-table-column>
          <el-table-column :label="t('analytics.convStart')" width="120">
            <template #default="{ row }">{{ fmtPct(row.conversion_from_start) }}</template>
          </el-table-column>
          <el-table-column :label="t('analytics.funnelBar')" min-width="160">
            <template #default="{ row }">
              <div class="funnel-bar-track">
                <div class="funnel-bar-fill" :style="{ width: Math.min(100, row.conversion_from_start || 0) + '%' }" />
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane :label="t('analytics.tabStream')" name="stream">
        <div class="pro-toolbar">
          <el-input v-model="streamEvent" size="small" clearable :placeholder="t('events.eventName')" class="pro-control-md" />
          <el-input v-model="streamQ" size="small" clearable :placeholder="t('analytics.search')" class="pro-control-md" />
          <el-button size="small" :loading="loadingStream" @click="loadStream">{{ t('common.refresh') }}</el-button>
        </div>
        <el-table :data="streamRows" v-loading="loadingStream" style="width:100%" size="small">
          <el-table-column prop="id" :label="t('common.id')" width="80" />
          <el-table-column prop="event" :label="t('events.eventName')" min-width="140" />
          <el-table-column prop="user_id" :label="t('analytics.userId')" width="90" />
          <el-table-column prop="app_version" :label="t('analytics.version')" width="100" />
          <el-table-column prop="device_locale" :label="t('common.language')" width="90" />
          <el-table-column prop="created_at" :label="t('common.createdAt')" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="props" label="props" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ JSON.stringify(row.props || {}) }}</template>
          </el-table-column>
        </el-table>
        <div class="stream-foot">
          <span>{{ t('analytics.total') }}: {{ streamTotal }}</span>
          <el-button size="small" :disabled="streamOffset <= 0" @click="streamPrev">{{ t('analytics.prev') }}</el-button>
          <el-button size="small" :disabled="streamOffset + streamRows.length >= streamTotal" @click="streamNext">
            {{ t('analytics.next') }}
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </PageContainer>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  getAnalyticsOverview, getAnalyticsEvents, getAnalyticsFunnel, getAnalyticsStream,
} from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const tab = ref('overview')
const loading = ref(false)
const loadingEvents = ref(false)
const loadingFunnel = ref(false)
const loadingStream = ref(false)

const end = new Date()
const start = new Date()
start.setDate(end.getDate() - 6)
const dateRange = ref([
  start.toISOString().slice(0, 10),
  end.toISOString().slice(0, 10),
])

const overview = ref(null)
const eventRows = ref([])
const funnelSteps = ref([])
const funnelStepsInput = ref('')
const streamRows = ref([])
const streamTotal = ref(0)
const streamOffset = ref(0)
const streamEvent = ref('')
const streamQ = ref('')
const STREAM_LIMIT = 50

const trend = computed(() => (overview.value && overview.value.trend) || [])
const trendCounts = computed(() => trend.value.map((r) => r.count))
const topEvents = computed(() => (overview.value && overview.value.top_events) || [])
const byLocale = computed(() => (overview.value && overview.value.by_locale) || [])
const byVersion = computed(() => (overview.value && overview.value.by_version) || [])

const kpiCards = computed(() => {
  const k = (overview.value && overview.value.kpis) || {}
  return [
    {
      key: 'events',
      label: t('analytics.kpiEvents'),
      value: fmtInt(k.events || 0),
      ...deltaMeta(k.events_delta),
    },
    {
      key: 'dau',
      label: t('analytics.kpiDau'),
      value: fmtInt(k.dau || 0),
      ...deltaMeta(k.dau_delta),
    },
    {
      key: 'page_pv',
      label: t('analytics.kpiPagePv'),
      value: fmtInt(k.page_pv || 0),
    },
    {
      key: 'page_uv',
      label: t('analytics.kpiPageUv'),
      value: fmtInt(k.page_uv || 0),
    },
    {
      key: 'btn_pv',
      label: t('analytics.kpiBtnPv'),
      value: fmtInt(k.btn_pv || 0),
    },
    {
      key: 'btn_uv',
      label: t('analytics.kpiBtnUv'),
      value: fmtInt(k.btn_uv || 0),
    },
    {
      key: 'names',
      label: t('analytics.kpiNames'),
      value: fmtInt(k.unique_event_names || 0),
    },
    {
      key: 'avg',
      label: t('analytics.kpiAvg'),
      value: String(k.avg_events_per_user || 0),
    },
  ]
})

function paramsBase() {
  const [df, dt] = dateRange.value || []
  return {
    app_id: workspaceAppId(),
    date_from: df || undefined,
    date_to: dt || undefined,
  }
}

function deltaMeta(d) {
  if (!d) return {}
  const abs = d.abs
  const pct = d.pct
  if (abs == null) return {}
  const sign = abs > 0 ? '+' : ''
  const text = pct == null ? `${sign}${abs}` : `${sign}${pct}%`
  return {
    deltaText: text,
    deltaClass: abs > 0 ? 'up' : abs < 0 ? 'down' : '',
  }
}

function fmtInt(n) {
  return Number(n || 0).toLocaleString()
}

function fmtCompact(n) {
  const v = Number(n || 0)
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}k`
  return String(v)
}

function fmtPct(v) {
  if (v == null || v === '') return '—'
  return `${Number(v).toFixed(1)}%`
}

function shortDay(day) {
  if (!day) return ''
  return String(day).slice(5)
}

function barHeight(val, arr) {
  const max = Math.max(...(arr || [0]), 1)
  return Math.max(4, Math.round((Number(val || 0) / max) * 120))
}

function formatTime(iso) {
  if (!iso) return ''
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

async function loadOverview() {
  loading.value = true
  try {
    const res = await getAnalyticsOverview(paramsBase())
    overview.value = res.results || null
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function loadEvents() {
  loadingEvents.value = true
  try {
    const res = await getAnalyticsEvents(paramsBase())
    eventRows.value = (res.results && res.results.list) || []
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loadingEvents.value = false
  }
}

async function loadFunnel() {
  loadingFunnel.value = true
  try {
    const p = { ...paramsBase() }
    if (funnelStepsInput.value.trim()) p.steps = funnelStepsInput.value.trim()
    const res = await getAnalyticsFunnel(p)
    const data = res.results || {}
    funnelSteps.value = data.steps || []
    if (!funnelStepsInput.value && data.default_steps) {
      funnelStepsInput.value = data.default_steps.join(',')
    }
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loadingFunnel.value = false
  }
}

async function loadStream() {
  loadingStream.value = true
  try {
    const res = await getAnalyticsStream({
      ...paramsBase(),
      event: streamEvent.value || undefined,
      q: streamQ.value || undefined,
      limit: STREAM_LIMIT,
      offset: streamOffset.value,
    })
    const data = res.results || {}
    streamRows.value = data.list || []
    streamTotal.value = data.total || 0
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loadingStream.value = false
  }
}

function streamPrev() {
  streamOffset.value = Math.max(0, streamOffset.value - STREAM_LIMIT)
  loadStream()
}

function streamNext() {
  streamOffset.value += STREAM_LIMIT
  loadStream()
}

function onTab(name) {
  if (name === 'events') loadEvents()
  if (name === 'funnel') loadFunnel()
  if (name === 'stream') loadStream()
}

async function reloadAll() {
  streamOffset.value = 0
  await loadOverview()
  if (tab.value === 'events') await loadEvents()
  if (tab.value === 'funnel') await loadFunnel()
  if (tab.value === 'stream') await loadStream()
}

onMounted(reloadAll)
</script>

<style scoped>
.dash-daterange { width: 240px; }
.kpi-row { margin-bottom: 16px; }
.kpi-card { border-radius: 8px; }
.kpi-label { color: #8c8c8c; font-size: 13px; }
.kpi-value { font-size: 28px; font-weight: 600; margin-top: 4px; color: #262626; }
.kpi-delta { margin-top: 6px; font-size: 12px; color: #8c8c8c; }
.kpi-delta.up { color: #389e0d; }
.kpi-delta.down { color: #cf1322; }
.panel-card { margin-bottom: 16px; border-radius: 8px; }
.panel-head { display: flex; justify-content: space-between; align-items: center; }
.panel-unit { color: #8c8c8c; font-size: 12px; }
.section-row { margin-top: 0; }
.trend {
  display: flex; align-items: flex-end; gap: 6px; min-height: 160px;
  overflow-x: auto; padding-top: 8px;
}
.bar-col { flex: 0 0 36px; text-align: center; }
.bar {
  width: 20px; margin: 0 auto; background: #ff4d4f; border-radius: 4px 4px 0 0;
  min-height: 4px;
}
.bar-val { font-size: 10px; color: #8c8c8c; margin-bottom: 4px; }
.day { font-size: 10px; color: #8c8c8c; margin-top: 4px; }
.empty { color: #bfbfbf; padding: 40px 0; text-align: center; width: 100%; }
.funnel-bar-track {
  height: 8px; background: #f5f5f5; border-radius: 4px; overflow: hidden;
}
.funnel-bar-fill {
  height: 100%; background: #ff4d4f; border-radius: 4px;
}
.stream-foot {
  display: flex; gap: 12px; align-items: center; margin-top: 12px; color: #8c8c8c; font-size: 13px;
}
</style>
