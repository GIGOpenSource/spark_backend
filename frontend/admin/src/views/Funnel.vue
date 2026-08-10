<template>
  <PageContainer :title="t('funnel.title')" :sub-title="t('funnel.subtitle')">
    <WorkspaceFilter @change="onWorkspaceChange" />
    <PageTabs v-model="tab" :tabs="tabs">
      <template #default="{ active }">
        <div v-show="active === 'robot'">
          <div class="pro-toolbar">
            <el-button type="danger" @click="createRobot">{{ t('funnel.addRobot') }}</el-button>
            <el-button @click="downloadTemplate">{{ t('funnel.downloadTemplate') }}</el-button>
            <el-upload
              :show-file-list="false"
              :http-request="onImportExcel"
              accept=".xlsx,.xlsm"
              :disabled="importing"
            >
              <el-button :loading="importing">{{ t('funnel.importExcel') }}</el-button>
            </el-upload>
            <el-button @click="loadRobots">{{ t('common.refresh') }}</el-button>
          </div>
          <p class="pro-hint">{{ t('funnel.importHint') }}</p>
          <el-table :data="robots" style="width:100%" v-loading="loadingRobots">
            <el-table-column prop="id" :label="t('common.id')" :width="72" />
            <el-table-column prop="nickname" :label="t('funnel.nickname')" />
            <el-table-column prop="age" :label="t('funnel.age')" width="70" />
            <el-table-column prop="job" :label="t('funnel.job')" />
            <el-table-column prop="city" :label="t('funnel.city')" />
            <el-table-column prop="is_active" :label="t('funnel.active')" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? t('common.yes') : t('common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('common.actions')" width="180">
              <template #default="{ row }">
                <el-button link type="primary" @click="toggle(row)">
                  {{ row.is_active ? t('common.disable') : t('common.enable') }}
                </el-button>
                <el-button link type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-show="active === 'lists'">
          <p class="pro-hint">{{ t('funnel.listHint') }}</p>
          <div class="pro-toolbar">
            <el-button type="danger" @click="openListCreate">{{ t('funnel.addList') }}</el-button>
            <el-button @click="loadLists">{{ t('common.refresh') }}</el-button>
          </div>
          <el-table :key="'lists-' + lists.length" :data="lists" style="width:100%" v-loading="loadingLists">
            <el-table-column prop="id" :label="t('common.id')" :width="72" />
            <el-table-column prop="priority" :label="t('funnel.priority')" width="110" sortable>
              <template #default="{ row }">
                <span>{{ row.priority ?? 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('funnel.appName')" width="120">
              <template #default="{ row }">{{ appLabel(row.app_id) }}</template>
            </el-table-column>
            <el-table-column prop="country" :label="t('funnel.region')" width="120">
              <template #default="{ row }">{{ regionText(row.country) }}</template>
            </el-table-column>
            <el-table-column prop="locale" :label="t('common.language')" width="120">
              <template #default="{ row }">{{ localeText(row.locale) }}</template>
            </el-table-column>
            <el-table-column :label="t('funnel.robots')" min-width="220">
              <template #default="{ row }">
                <template v-if="(row.robots || []).length">
                  <el-tag
                    v-for="r in row.robots"
                    :key="r.id"
                    size="small"
                    class="robot-tag"
                    :type="r.is_active ? '' : 'info'"
                  >
                    {{ r.nickname || r.id }}
                  </el-tag>
                </template>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
            <el-table-column prop="is_active" :label="t('funnel.active')" width="90">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? t('common.yes') : t('common.no') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('common.actions')" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openListEdit(row)">{{ t('common.edit') }}</el-button>
                <el-button link type="danger" @click="removeList(row)">{{ t('common.delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-show="active === 'real'">
          <p class="pro-hint">{{ t('funnel.abcHint') }}</p>
          <div class="pro-toolbar">
            <el-button type="danger" @click="openCreate">{{ t('funnel.addRule') }}</el-button>
            <el-button @click="loadRules">{{ t('common.refresh') }}</el-button>
          </div>
          <el-table :key="'rules-' + rules.length" :data="rules" style="width:100%" v-loading="loadingRules">
            <el-table-column prop="id" :label="t('common.id')" :width="72" />
            <el-table-column prop="priority" :label="t('funnel.priority')" width="110" sortable>
              <template #default="{ row }">
                <span>{{ row.priority ?? 0 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="country" :label="t('funnel.region')" width="120">
              <template #default="{ row }">{{ regionText(row.country) }}</template>
            </el-table-column>
            <el-table-column prop="locale" :label="t('common.language')" width="120">
              <template #default="{ row }">{{ localeText(row.locale) }}</template>
            </el-table-column>
            <el-table-column :label="t('funnel.aPercent')" width="110">
              <template #default="{ row }">{{ row.a_percent }}%</template>
            </el-table-column>
            <el-table-column :label="t('funnel.bPercent')" width="110">
              <template #default="{ row }">{{ row.b_percent }}%</template>
            </el-table-column>
            <el-table-column :label="t('funnel.cPercent')" width="110">
              <template #default="{ row }">{{ row.c_percent }}%</template>
            </el-table-column>
            <el-table-column :label="t('common.actions')" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
                <el-button link type="danger" @click="removeRule(row)">{{ t('common.delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </PageTabs>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? t('common.edit') : t('funnel.addRule')"
      :width="480"
      destroy-on-close
    >
      <el-form label-width="120px">
        <el-form-item :label="t('funnel.region')">
          <el-select v-model="form.country" style="width:100%">
            <el-option
              v-for="o in COUNTRY_OPTIONS"
              :key="o.value"
              :label="t(`regions.${o.value}`)"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.language')">
          <el-select v-model="form.locale" style="width:100%">
            <el-option
              v-for="o in LOCALE_OPTIONS"
              :key="o.value"
              :label="t(`locales.${o.value}`)"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('funnel.priority')">
          <el-input-number v-model="form.priority" :step="1" />
          <p class="field-hint">{{ t('funnel.priorityHint') }}</p>
        </el-form-item>
        <el-form-item :label="t('funnel.aPercent')">
          <el-input-number v-model="form.a_percent" :min="0" :max="100" />
        </el-form-item>
        <el-form-item :label="t('funnel.bPercent')">
          <el-input-number v-model="form.b_percent" :min="0" :max="100" />
        </el-form-item>
        <el-form-item :label="t('funnel.cPercent')">
          <el-input-number v-model="form.c_percent" :min="0" :max="100" />
        </el-form-item>
        <div class="sum" :class="{ bad: formPercentSum !== 100 }">A+B+C = {{ formPercentSum }}</div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="danger" :loading="savingRule" @click="saveRule">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="listDialogVisible"
      :title="listEditingId ? t('funnel.editList') : t('funnel.addList')"
      :width="560"
      destroy-on-close
    >
      <el-form label-width="120px">
        <el-form-item :label="t('funnel.appName')">
          <el-select v-model="listForm.app_id" style="width:100%" @change="onListAppChange">
            <el-option
              v-for="o in appWriteOptions"
              :key="o.value"
              :label="o.label"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('funnel.region')">
          <el-select v-model="listForm.country" style="width:100%">
            <el-option
              v-for="o in COUNTRY_OPTIONS"
              :key="o.value"
              :label="t(`regions.${o.value}`)"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.language')">
          <el-select v-model="listForm.locale" style="width:100%">
            <el-option
              v-for="o in LOCALE_OPTIONS"
              :key="o.value"
              :label="t(`locales.${o.value}`)"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('funnel.priority')">
          <el-input-number v-model="listForm.priority" :step="1" />
          <p class="field-hint">{{ t('funnel.priorityHint') }}</p>
        </el-form-item>
        <el-form-item :label="t('funnel.robots')">
          <el-select
            v-model="listForm.robot_ids"
            multiple
            filterable
            style="width:100%"
            :placeholder="t('funnel.robots')"
          >
            <el-option
              v-for="r in pickerRobots"
              :key="r.id"
              :label="`${r.nickname || 'Robot'} (#${r.id})`"
              :value="r.id"
              :disabled="r.is_active === false"
            />
          </el-select>
          <p v-if="!pickerRobots.length" class="field-hint">{{ t('funnel.noRobots') }}</p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="listDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="danger" :loading="savingList" @click="saveList">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getFunnel, createFunnel, getFunnelAbcRules, createFunnelAbcRule, updateFunnelAbcRule, deleteFunnelAbcRule,
  getRobotRecommendLists, saveRobotRecommendList, deleteRobotRecommendList,
  downloadFunnelImportTemplate, importFunnelRobots
} from '../api'
import {
  getWorkspace, workspaceAppId, workspaceAppIdOrDefault, COUNTRY_OPTIONS, LOCALE_OPTIONS,
  getAppOptions, accessibleAppOptions, APP_ALL
} from '../workspace'
import http from '../api'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'
import PageTabs from '../components/PageTabs.vue'

const { t, te } = useI18n()

const tab = ref('robot')
const robots = ref([])
const lists = ref([])
const rules = ref([])
const pickerRobots = ref([])
const loadingRobots = ref(false)
const loadingLists = ref(false)
const loadingRules = ref(false)
const savingRule = ref(false)
const savingList = ref(false)
const importing = ref(false)
const dialogVisible = ref(false)
const listDialogVisible = ref(false)
const editingId = ref(null)
const listEditingId = ref(null)
const form = ref({
  country: '*',
  locale: '*',
  priority: 0,
  a_percent: 20,
  b_percent: 40,
  c_percent: 40
})
const listForm = ref({
  app_id: 'spark_main',
  country: '*',
  locale: '*',
  priority: 0,
  robot_ids: []
})

const appWriteOptions = computed(() => accessibleAppOptions({ includeAll: false }))

function regionText(code) {
  const key = `regions.${code || '*'}`
  return te(key) ? t(key) : (code || '*')
}

function localeText(code) {
  const key = `locales.${code || '*'}`
  return te(key) ? t(key) : (code || '*')
}

function appLabel(id) {
  const hit = getAppOptions().find((o) => o.value === id)
  return hit ? hit.label : (id || '—')
}

const tabs = computed(() => [
  { name: 'robot', label: t('funnel.tabRobot') },
  { name: 'lists', label: t('funnel.tabRobotList') },
  { name: 'real', label: t('funnel.tabReal') }
])

const formPercentSum = computed(() =>
  Number(form.value.a_percent || 0) + Number(form.value.b_percent || 0) + Number(form.value.c_percent || 0)
)

async function loadRobots() {
  loadingRobots.value = true
  try {
    const ws = getWorkspace()
    const res = await getFunnel({ app_id: workspaceAppId(), country: ws.country })
    robots.value = (res.results && res.results.list) || []
  } finally {
    loadingRobots.value = false
  }
}

async function loadPickerRobots(appId) {
  const res = await getFunnel({ app_id: appId || listForm.value.app_id, country: '*' })
  pickerRobots.value = (res.results && res.results.list) || []
}

async function loadLists() {
  loadingLists.value = true
  try {
    const ws = getWorkspace()
    const params = { app_id: workspaceAppId() }
    if (ws.country && ws.country !== '*') params.country = ws.country
    const res = await getRobotRecommendLists(params)
    lists.value = (res.results && res.results.list) || []
  } finally {
    loadingLists.value = false
  }
}

async function loadRules() {
  loadingRules.value = true
  try {
    const ws = getWorkspace()
    const res = await getFunnelAbcRules({ app_id: workspaceAppId(), country: ws.country })
    rules.value = (res.results && res.results.list) || []
  } finally {
    loadingRules.value = false
  }
}

async function onWorkspaceChange() {
  const jobs = [loadRobots()]
  if (tab.value === 'lists') jobs.push(loadLists())
  if (tab.value === 'real') jobs.push(loadRules())
  await Promise.all(jobs)
}

async function createRobot() {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  const ws = getWorkspace()
  try {
    await createFunnel({
      app_id: appId,
      country: ws.country,
      pool: 'robot',
      nickname: 'Robot',
      age: 24,
      job: 'UX Designer',
      city: 'California',
      photo_urls: ['https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800'],
      bio: 'Hello from robot funnel',
      tags: ['Travel']
    })
    ElMessage.success(t('funnel.created'))
    loadRobots()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function downloadTemplate() {
  try {
    const blob = await downloadFunnelImportTemplate()
    const url = URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'robot_cards_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error((e && e.message) || t('funnel.importFailed'))
  }
}

async function onImportExcel({ file }) {
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  importing.value = true
  try {
    const ws = getWorkspace()
    const fd = new FormData()
    fd.append('file', file)
    fd.append('app_id', appId)
    fd.append('country', ws.country || '*')
    fd.append('locale', 'en')
    const res = await importFunnelRobots(fd)
    const data = res.results || {}
    const n = data.created || 0
    ElMessage.success(t('funnel.importSuccess', { n }))
    if ((data.errors || []).length) {
      ElMessage.warning((data.errors || []).slice(0, 3).join('；'))
    }
    await loadRobots()
  } catch (e) {
    ElMessage.error((e && e.message) || t('funnel.importFailed'))
  } finally {
    importing.value = false
  }
}

async function toggle(row) {
  try {
    await http.put(`/spark-admin/funnel/${row.id}/`, { is_active: !row.is_active })
    loadRobots()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function remove(row) {
  try {
    await http.delete(`/spark-admin/funnel/${row.id}/`)
    ElMessage.success(t('common.deleted'))
    loadRobots()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

function openCreate() {
  editingId.value = null
  form.value = {
    country: getWorkspace().country || '*',
    locale: '*',
    priority: 0,
    a_percent: 20,
    b_percent: 40,
    c_percent: 40
  }
  dialogVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  form.value = {
    country: row.country || '*',
    locale: row.locale || '*',
    priority: row.priority ?? 0,
    a_percent: row.a_percent ?? 20,
    b_percent: row.b_percent ?? 40,
    c_percent: row.c_percent ?? 40
  }
  dialogVisible.value = true
}

async function saveRule() {
  if (formPercentSum.value !== 100) {
    ElMessage.warning(t('funnel.percentSumError'))
    return
  }
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  savingRule.value = true
  try {
    const payload = {
      app_id: appId,
      country: form.value.country || '*',
      locale: form.value.locale || '*',
      priority: Number(form.value.priority || 0),
      a_percent: form.value.a_percent,
      b_percent: form.value.b_percent,
      c_percent: form.value.c_percent
    }
    if (editingId.value) {
      await updateFunnelAbcRule(editingId.value, payload)
    } else {
      await createFunnelAbcRule(payload)
    }
    ElMessage.success(t('funnel.saved'))
    dialogVisible.value = false
    await loadRules()
  } catch (e) {
    ElMessage.error((e && e.message) || t('funnel.saveFailed'))
  } finally {
    savingRule.value = false
  }
}

async function removeRule(row) {
  try {
    await ElMessageBox.confirm(t('funnel.deleteRuleConfirm'), { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteFunnelAbcRule(row.id)
    ElMessage.success(t('common.deleted'))
    loadRules()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function openListCreate() {
  listEditingId.value = null
  const ws = getWorkspace()
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  listForm.value = {
    app_id: appId,
    country: ws.country || '*',
    locale: '*',
    priority: 0,
    robot_ids: []
  }
  await loadPickerRobots(listForm.value.app_id)
  listDialogVisible.value = true
}

async function openListEdit(row) {
  listEditingId.value = row.id
  listForm.value = {
    app_id: row.app_id,
    country: row.country || '*',
    locale: row.locale || '*',
    priority: row.priority ?? 0,
    robot_ids: [...(row.robot_ids || [])]
  }
  await loadPickerRobots(row.app_id)
  listDialogVisible.value = true
}

async function onListAppChange() {
  listForm.value.robot_ids = []
  await loadPickerRobots(listForm.value.app_id)
}

async function saveList() {
  if (!listForm.value.app_id || listForm.value.app_id === APP_ALL) {
    ElMessage.warning(t('funnel.appRequired'))
    return
  }
  if (!(listForm.value.robot_ids || []).length) {
    ElMessage.warning(t('funnel.robotsRequired'))
    return
  }
  savingList.value = true
  try {
    await saveRobotRecommendList({
      id: listEditingId.value || undefined,
      app_id: listForm.value.app_id,
      country: listForm.value.country || '*',
      locale: listForm.value.locale || '*',
      priority: Number(listForm.value.priority || 0),
      robot_ids: listForm.value.robot_ids,
      is_active: true
    })
    ElMessage.success(t('funnel.saved'))
    listDialogVisible.value = false
    await loadLists()
  } catch (e) {
    ElMessage.error((e && e.message) || t('funnel.saveFailed'))
  } finally {
    savingList.value = false
  }
}

async function removeList(row) {
  try {
    await ElMessageBox.confirm(t('funnel.deleteListConfirm'), { type: 'warning' })
  } catch {
    return
  }
  await deleteRobotRecommendList(row.id)
  ElMessage.success(t('common.deleted'))
  loadLists()
}

watch(tab, (v) => {
  if (v === 'lists') loadLists()
  if (v === 'real') loadRules()
})

onMounted(async () => {
  await loadRobots()
})
</script>

<style scoped>
.field-hint { color: var(--pro-text-secondary); font-size: var(--pro-font-xs); margin: 6px 0 0; }
.sum { margin: 0 0 0 var(--pro-label-width); font-size: var(--pro-font-sm); color: var(--pro-text-secondary); }
.sum.bad { color: #dc2626; font-weight: 600; }
.robot-tag { margin: 0 var(--pro-space-xs) var(--pro-space-xs) 0; }
.muted { color: var(--pro-text-secondary); }
</style>
