<template>
  <PageContainer :title="t('push.title')" :sub-title="t('push.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load" />
    <div class="pro-toolbar">
      <el-select v-model="filters.locale" size="small" clearable :placeholder="t('common.language')" class="pro-control-sm" @change="load">
        <el-option
          v-for="o in LOCALE_OPTIONS.filter((x) => x.value !== '*')"
          :key="o.value"
          :label="t(`locales.${o.value}`)"
          :value="o.value"
        />
      </el-select>
      <el-select v-model="filters.event_type" size="small" clearable :placeholder="t('push.event')" class="pro-control-md" @change="load">
        <el-option v-for="e in EVENT_OPTIONS" :key="e" :label="t(`push.events.${e}`)" :value="e" />
      </el-select>
      <el-button type="danger" size="small" @click="openCreate">{{ t('push.add') }}</el-button>
    </div>
    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column prop="app_id" :label="t('workspace.product')" width="120">
        <template #default="{ row }">{{ appLabel(row.app_id) }}</template>
      </el-table-column>
      <el-table-column prop="locale" :label="t('common.language')" width="100">
        <template #default="{ row }">{{ localeText(row.locale) }}</template>
      </el-table-column>
      <el-table-column prop="event_type" :label="t('push.event')" width="140">
        <template #default="{ row }">{{ eventLabel(row.event_type) }}</template>
      </el-table-column>
      <el-table-column prop="recall_day" :label="t('push.recallDay')" width="90" />
      <el-table-column prop="title_template" :label="t('push.titleTpl')" min-width="160" show-overflow-tooltip />
      <el-table-column prop="enabled" :label="t('push.enabled')" width="90">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? t('common.on') : t('common.off') }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="daily_push_cap" :label="t('push.dailyCap')" width="90" />
      <el-table-column :label="t('common.actions')" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">{{ t('common.edit') }}</el-button>
          <el-button link type="danger" @click="remove(row)">{{ t('common.delete') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="form.id ? t('push.edit') : t('push.add')" width="560px" destroy-on-close>
      <el-form label-width="120px">
        <el-form-item :label="t('workspace.product')">
          <el-select v-model="form.app_id" style="width:100%" :disabled="!!form.id">
            <el-option v-for="o in appWriteOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('common.language')">
          <el-select v-model="form.locale" style="width:100%">
            <el-option
              v-for="o in LOCALE_OPTIONS.filter((x) => x.value !== '*')"
              :key="o.value"
              :label="t(`locales.${o.value}`)"
              :value="o.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('push.event')">
          <el-select v-model="form.event_type" style="width:100%">
            <el-option v-for="e in EVENT_OPTIONS" :key="e" :label="t(`push.events.${e}`)" :value="e" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.event_type === 'silent_recall'" :label="t('push.recallDay')">
          <el-select v-model="form.recall_day" style="width:100%">
            <el-option :label="'D1'" :value="1" />
            <el-option :label="'D3'" :value="3" />
            <el-option :label="'D7'" :value="7" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('push.titleTpl')">
          <el-input v-model="form.title_template" :placeholder="'{nickname}'" />
        </el-form-item>
        <el-form-item :label="t('push.bodyTpl')">
          <el-input v-model="form.body_template" type="textarea" :rows="3" :placeholder="'{nickname} {preview}'" />
        </el-form-item>
        <el-form-item :label="t('push.deepLink')">
          <el-input v-model="form.deep_link" />
        </el-form-item>
        <el-form-item :label="t('push.dailyCap')">
          <el-input-number v-model="form.daily_push_cap" :min="1" :max="20" />
        </el-form-item>
        <el-form-item :label="t('push.delayMin')">
          <el-input-number v-model="form.delay_minutes_min" :min="0" />
        </el-form-item>
        <el-form-item :label="t('push.delayMax')">
          <el-input-number v-model="form.delay_minutes_max" :min="0" />
        </el-form-item>
        <el-form-item :label="t('push.enabled')">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="danger" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPushConfigs, createPushConfig, updatePushConfig, deletePushConfig } from '../api'
import {
  workspaceAppId, workspaceAppIdOrDefault, accessibleAppOptions, getAppOptions,
  APP_ALL, LOCALE_OPTIONS,
} from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const EVENT_OPTIONS = ['new_like', 'new_match', 'new_message', 'silent_recall']
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const rows = ref([])
const filters = reactive({ locale: '', event_type: '' })
const form = reactive({
  id: null,
  app_id: 'spark_main',
  locale: 'en',
  event_type: 'new_like',
  recall_day: 0,
  title_template: '',
  body_template: '',
  deep_link: '/pages/likes/index',
  enabled: true,
  daily_push_cap: 1,
  delay_minutes_min: 0,
  delay_minutes_max: 0,
})

const appWriteOptions = computed(() => accessibleAppOptions({ includeAll: false }))

function appLabel(id) {
  const hit = getAppOptions().find((o) => o.value === id)
  return hit ? hit.label : id
}

function localeText(code) {
  const key = `locales.${code || 'en'}`
  const label = t(key)
  return label === key ? code : label
}

function eventLabel(eventType) {
  if (!eventType) return '—'
  const key = `push.events.${eventType}`
  const label = t(key)
  return label === key ? eventType : label
}

function resetForm() {
  const appId = workspaceAppIdOrDefault()
  Object.assign(form, {
    id: null,
    app_id: appId || (appWriteOptions.value[0]?.value || ''),
    locale: 'en',
    event_type: 'new_like',
    recall_day: 0,
    title_template: '',
    body_template: '',
    deep_link: '/pages/likes/index',
    enabled: true,
    daily_push_cap: 1,
    delay_minutes_min: 0,
    delay_minutes_max: 0,
  })
}

async function load() {
  loading.value = true
  try {
    const params = { app_id: workspaceAppId() }
    if (filters.locale) params.locale = filters.locale
    if (filters.event_type) params.event_type = filters.event_type
    const res = await getPushConfigs(params)
    rows.value = (res.results && res.results.list) || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  resetForm()
  dialog.value = true
}

function openEdit(row) {
  Object.assign(form, {
    id: row.id,
    app_id: row.app_id,
    locale: row.locale,
    event_type: row.event_type,
    recall_day: row.recall_day || 0,
    title_template: row.title_template || '',
    body_template: row.body_template || '',
    deep_link: row.deep_link || '/pages/chat/index',
    enabled: !!row.enabled,
    daily_push_cap: row.daily_push_cap || 1,
    delay_minutes_min: row.delay_minutes_min || 0,
    delay_minutes_max: row.delay_minutes_max || 0,
  })
  dialog.value = true
}

async function save() {
  saving.value = true
  try {
    const payload = {
      app_id: form.app_id,
      locale: form.locale,
      event_type: form.event_type,
      recall_day: form.event_type === 'silent_recall' ? form.recall_day : 0,
      title_template: form.title_template,
      body_template: form.body_template,
      deep_link: form.deep_link,
      enabled: form.enabled,
      daily_push_cap: form.daily_push_cap,
      delay_minutes_min: form.delay_minutes_min,
      delay_minutes_max: form.delay_minutes_max,
    }
    if (form.id) {
      await updatePushConfig(form.id, payload)
    } else {
      await createPushConfig(payload)
    }
    ElMessage.success(t('common.saved'))
    dialog.value = false
    load()
  } catch (e) {
    ElMessage.error((e && e.message) || t('common.loadFailed'))
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(t('push.deleteConfirm'), { type: 'warning' })
    await deletePushConfig(row.id)
    ElMessage.success(t('common.deleted'))
    load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error((e && e.message) || t('common.loadFailed'))
  }
}

onMounted(load)
</script>
