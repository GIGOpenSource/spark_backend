<template>
  <PageContainer :title="t('dashboard.title')" :sub-title="t('dashboard.subtitle')" :ghost="true">
    <WorkspaceFilter @change="load">
      <el-select v-model="platform" clearable size="small" :placeholder="t('workspace.platform')" class="pro-control-sm" @change="load">
        <el-option :label="t('workspace.allPlatforms')" value="" />
        <el-option v-for="o in PLATFORM_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        size="small"
        class="dash-daterange"
        range-separator="~"
        :start-placeholder="t('dashboard.dateStart')"
        :end-placeholder="t('dashboard.dateEnd')"
        value-format="YYYY-MM-DD"
        @change="load"
      />
      <el-button type="danger" size="small" @click="load">{{ t('common.refresh') }}</el-button>
    </WorkspaceFilter>

    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="12" :sm="8" :md="4" v-for="item in cards" :key="item.key">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-label">{{ item.label }}</div>
          <div class="kpi-value">{{ item.value }}</div>
          <div class="kpi-delta" v-if="item.deltaText" :class="item.deltaClass">
            {{ t('dashboard.vsYesterday') }} {{ item.deltaText }}
          </div>
          <div class="kpi-delta muted" v-else>{{ t('dashboard.noCompare') }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="panel-head">
              <span>{{ t('dashboard.registerTrend') }}</span>
              <span class="panel-unit">{{ t('dashboard.unitCount') }}</span>
            </div>
          </template>
          <div class="trend">
            <div
              v-for="row in trend"
              :key="'r' + row.day"
              class="bar-col"
              :title="`${row.day}: ${fmtInt(row.count)}`"
            >
              <div class="bar-val">{{ fmtCompact(row.count) }}</div>
              <div class="bar" :style="{ height: barHeight(row.count, trendCounts) + 'px' }" />
              <div class="day">{{ shortDay(row.day) }}</div>
            </div>
            <div v-if="!trend.length" class="empty">{{ t('dashboard.noTrend') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="panel-head">
              <span>{{ t('dashboard.gmvTrend') }}</span>
              <span class="panel-unit">{{ t('dashboard.unitMoney') }}</span>
            </div>
          </template>
          <div class="trend">
            <div
              v-for="row in gmvTrend"
              :key="'g' + row.day"
              class="bar-col"
              :title="`${row.day}: ${fmtMoney(row.amount)}`"
            >
              <div class="bar-val">{{ fmtCompact(row.amount) }}</div>
              <div class="bar gmv" :style="{ height: barHeight(row.amount, gmvAmounts) + 'px' }" />
              <div class="day">{{ shortDay(row.day) }}</div>
            </div>
            <div v-if="!gmvTrend.length" class="empty">{{ t('dashboard.noGmv') }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="section-row">
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="panel-card">
          <template #header>{{ t('dashboard.platformMix') }}</template>
          <el-table :data="platformMix" style="width:100%" size="small" empty-text="—">
            <el-table-column prop="platform" :label="t('workspace.platform')" min-width="100" />
            <el-table-column :label="t('dashboard.orders')" width="100" align="right">
              <template #default="{ row }">{{ fmtInt(row.count) }}</template>
            </el-table-column>
            <el-table-column :label="t('dashboard.gmv')" min-width="120" align="right">
              <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="never" class="panel-card">
          <template #header>{{ t('dashboard.vipTierMix') }}</template>
          <el-table :data="tierMix" style="width:100%" size="small" empty-text="—">
            <el-table-column prop="tier" :label="t('dashboard.tier')" min-width="100" />
            <el-table-column :label="t('dashboard.users')" width="100" align="right">
              <template #default="{ row }">{{ fmtInt(row.count) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="panel-card retention-card">
      <template #header>
        <div class="panel-head">
          <span>{{ t('dashboard.retentionWide') }}</span>
          <span class="panel-unit">{{ t('dashboard.retentionHint') }}</span>
        </div>
      </template>
      <div class="retention-wrap" v-loading="loading">
        <table class="retention-table" v-if="retentionRows.length">
          <thead>
            <tr>
              <th class="sticky-col">{{ t('dashboard.cohortDate') }}</th>
              <th class="sticky-col sticky-col-2">{{ t('dashboard.newUsers') }}</th>
              <th v-for="d in retentionDays" :key="'h' + d">D{{ d }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in retentionRows" :key="row.cohort_date">
              <td class="sticky-col">{{ row.cohort_date }}</td>
              <td class="sticky-col sticky-col-2 num">{{ fmtInt(row.new_users) }}</td>
              <td
                v-for="(rate, idx) in row.rates"
                :key="row.cohort_date + '-' + idx"
                class="rate-cell"
                :style="retentionCellStyle(rate)"
                :title="retentionTitle(row, idx)"
              >
                {{ formatRetention(rate) }}
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">{{ t('dashboard.noRetention') }}</div>
      </div>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <template #header>{{ t('dashboard.recentPayments') }}</template>
      <el-table :data="payments" style="width:100%" size="small" empty-text="—">
        <el-table-column prop="id" :label="t('common.id')" width="72" />
        <el-table-column prop="user_id" :label="t('common.user')" width="100" />
        <el-table-column prop="product_id" :label="t('dashboard.product')" min-width="140" />
        <el-table-column prop="platform" :label="t('workspace.platform')" width="100" />
        <el-table-column :label="t('dashboard.amount')" width="120" align="right">
          <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column :label="t('common.time')" min-width="160">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getDashboard } from '../api'
import { getWorkspace, PLATFORM_OPTIONS } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t, locale } = useI18n()
const kpi = ref({})
const payments = ref([])
const trend = ref([])
const gmvTrend = ref([])
const platformMix = ref([])
const tierMix = ref([])
const retentionDays = ref([...Array(31).keys()])
const retentionRows = ref([])
const platform = ref('')
const dateRange = ref([])
const loading = ref(false)
const errorMsg = ref('')

function localeTag() {
  return locale.value === 'zh-CN' ? 'zh-CN' : 'en-US'
}

function fmtInt(n) {
  return Number(n || 0).toLocaleString(localeTag())
}

function fmtMoney(n) {
  return Number(n || 0).toLocaleString(localeTag(), {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

function fmtPercent(ratio) {
  return `${(Number(ratio || 0) * 100).toLocaleString(localeTag(), {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  })}%`
}

function fmtCompact(n) {
  const v = Number(n || 0)
  if (Math.abs(v) >= 1000) {
    return v.toLocaleString(localeTag(), { notation: 'compact', maximumFractionDigits: 1 })
  }
  return Number.isInteger(v) ? String(v) : v.toFixed(1)
}

function fmtTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso).replace('T', ' ').slice(0, 19)
  return d.toLocaleString(localeTag(), {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

function shortDay(day) {
  return String(day || '').slice(5)
}

function deltaPair(today, yesterday, formatter) {
  const d = Number(today || 0) - Number(yesterday || 0)
  const sign = d > 0 ? '+' : ''
  return {
    deltaText: `${sign}${formatter(d)}`,
    deltaClass: d > 0 ? 'up' : d < 0 ? 'down' : ''
  }
}

const cards = computed(() => {
  const k = kpi.value || {}
  const regDelta = deltaPair(k.register_today, k.register_yesterday, fmtInt)
  const gmvDelta = deltaPair(k.gmv_today, k.gmv_yesterday, fmtMoney)
  return [
    {
      key: 'register',
      label: t('dashboard.registerToday'),
      value: fmtInt(k.register_today),
      ...regDelta
    },
    {
      key: 'dau',
      label: t('dashboard.dau'),
      value: fmtInt(k.dau)
    },
    {
      key: 'gmv',
      label: t('dashboard.gmvToday'),
      value: fmtMoney(k.gmv_today),
      ...gmvDelta
    },
    {
      key: 'pays',
      label: t('dashboard.paysToday'),
      value: fmtInt(k.pay_count_today)
    },
    {
      key: 'first',
      label: t('dashboard.firstBuyers'),
      value: fmtInt(k.first_buyers)
    },
    {
      key: 'rate',
      label: t('dashboard.payRate'),
      value: fmtPercent(k.pay_rate)
    }
  ]
})

const trendCounts = computed(() => trend.value.map((x) => x.count))
const gmvAmounts = computed(() => gmvTrend.value.map((x) => x.amount))

function barHeight(c, values) {
  const max = Math.max(...(values || [0]).map((v) => Number(v || 0)), 1)
  return Math.max(4, Math.round((Number(c || 0) / max) * 110))
}

function formatRetention(rate) {
  if (rate === null || rate === undefined) return '—'
  return `${(Number(rate) * 100).toFixed(1)}%`
}

function retentionTitle(row, idx) {
  const rate = row.rates?.[idx]
  const count = row.counts?.[idx]
  if (rate === null || rate === undefined) return t('dashboard.retentionPending')
  return `${row.cohort_date} D${idx}: ${formatRetention(rate)} (${fmtInt(count)} / ${fmtInt(row.new_users)})`
}

function retentionCellStyle(rate) {
  if (rate === null || rate === undefined) {
    return { background: 'transparent', color: 'var(--pro-text-secondary)' }
  }
  const p = Math.max(0, Math.min(1, Number(rate) || 0))
  // heat from light → brand red
  const alpha = 0.08 + p * 0.72
  return {
    background: `rgba(255, 75, 85, ${alpha.toFixed(3)})`,
    color: p >= 0.45 ? '#fff' : 'var(--pro-text)'
  }
}

async function load() {
  const ws = getWorkspace()
  const params = {
    app_id: ws.app_id,
    country: ws.country,
    platform: platform.value || undefined
  }
  if (dateRange.value && dateRange.value.length === 2) {
    params.date_from = dateRange.value[0]
    params.date_to = dateRange.value[1]
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await getDashboard(params)
    if (res && res.code && res.code >= 400) {
      errorMsg.value = res.message || 'dashboard_error'
      ElMessage.error(errorMsg.value)
      return
    }
    const data = res.results || {}
    kpi.value = data.kpi || {}
    payments.value = data.recent_payments || []
    trend.value = data.register_trend || []
    gmvTrend.value = data.gmv_trend || []
    platformMix.value = data.platform_mix || []
    tierMix.value = data.vip_tier_mix || []
    const rw = data.retention_wide || {}
    retentionDays.value = Array.isArray(rw.days) && rw.days.length ? rw.days : [...Array(31).keys()]
    retentionRows.value = rw.rows || []
  } catch (e) {
    console.warn(e)
    errorMsg.value = (e && e.message) || 'Failed to load dashboard'
    ElMessage.error(errorMsg.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dash-daterange {
  width: 240px;
  max-width: 240px;
}
.dash-daterange :deep(.el-range-input) {
  width: 72px;
}
.kpi-row { margin-bottom: 8px; }
.kpi-card {
  margin-bottom: 16px;
  height: 100%;
}
.kpi-label {
  color: var(--pro-text-secondary);
  font-size: var(--pro-font-sm);
  line-height: 1.4;
}
.kpi-value {
  margin-top: 8px;
  font-size: var(--pro-font-kpi);
  font-weight: 700;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.kpi-delta {
  margin-top: 10px;
  font-size: var(--pro-font-xs);
  color: var(--pro-text-secondary);
  min-height: 18px;
  font-variant-numeric: tabular-nums;
}
.kpi-delta.up { color: #16a34a; }
.kpi-delta.down { color: #dc2626; }
.kpi-delta.muted { color: var(--pro-text-secondary); opacity: 0.7; }

.section-row { margin-bottom: 16px; }
.panel-card { margin-bottom: 16px; }
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.panel-unit {
  color: var(--pro-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.trend {
  display: flex;
  align-items: flex-end;
  min-height: 168px;
  padding: 8px 0 0;
  overflow-x: auto;
}
.bar-col {
  width: 40px;
  text-align: center;
  flex-shrink: 0;
  margin-right: 8px;
}
.bar-val {
  font-size: 10px;
  color: var(--pro-text-secondary);
  margin-bottom: 4px;
  height: 14px;
  font-variant-numeric: tabular-nums;
}
.bar {
  width: 22px;
  margin: 0 auto;
  background: var(--pro-primary);
  border-radius: 4px 4px 0 0;
}
.bar.gmv { background: #3b82f6; }
.day {
  font-size: 10px;
  color: var(--pro-text-secondary);
  margin-top: 6px;
}
.empty {
  color: var(--pro-text-secondary);
  padding: 24px 0;
}

.retention-card :deep(.el-card__body) {
  padding-top: 8px;
}
.retention-wrap {
  overflow: auto;
  max-height: 480px;
  border: 1px solid var(--pro-border, #f0f0f0);
  border-radius: 8px;
}
.retention-table {
  border-collapse: separate;
  border-spacing: 0;
  width: max-content;
  min-width: 100%;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
.retention-table th,
.retention-table td {
  padding: 6px 8px;
  text-align: center;
  white-space: nowrap;
  border-bottom: 1px solid #f0f0f0;
  border-right: 1px solid #f5f5f5;
  min-width: 56px;
}
.retention-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #fafafa;
  font-weight: 600;
  color: var(--pro-text-secondary);
}
.retention-table .sticky-col {
  position: sticky;
  left: 0;
  z-index: 1;
  background: #fff;
  text-align: left;
  min-width: 108px;
  box-shadow: 1px 0 0 #f0f0f0;
}
.retention-table .sticky-col-2 {
  left: 108px;
  min-width: 72px;
  text-align: right;
}
.retention-table thead .sticky-col {
  z-index: 3;
  background: #fafafa;
}
.retention-table .num {
  text-align: right;
}
.retention-table .rate-cell {
  font-weight: 500;
}
</style>
