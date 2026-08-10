<template>
  <PageContainer :title="t('providers.title')" :sub-title="t('providers.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load" />
    <p class="pro-hint">{{ t('providers.hint') }}</p>

    <div v-loading="loading" class="provider-grid">
      <div
        v-for="item in rows"
        :key="item.key"
        class="provider-card"
        @click="openEdit(item)"
      >
        <div class="provider-card-top">
          <div class="provider-icon" :data-cat="item.category">{{ iconLetter(item) }}</div>
          <el-tag :type="statusType(item.status)" size="small" effect="plain">
            {{ t(`providers.status.${item.status}`) }}
          </el-tag>
        </div>
        <h3 class="provider-name">{{ providerName(item) }}</h3>
        <p class="provider-note">{{ item.docs_note }}</p>
        <div class="provider-meta">
          <el-tag size="small" type="info">{{ t(`providers.category.${item.category}`) }}</el-tag>
          <el-tag size="small" :type="item.scope === 'global' ? 'warning' : 'info'">
            {{ item.scope === 'global' ? t('providers.scopeGlobal') : t('providers.scopeApp') }}
          </el-tag>
        </div>
        <div class="provider-actions" @click.stop>
          <el-button link type="primary" @click="openEdit(item)">{{ t('common.edit') }}</el-button>
          <el-link v-if="item.docs_url" :href="item.docs_url" target="_blank" type="info" underline="never">
            {{ t('providers.docs') }}
          </el-link>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="dialog"
      :title="editing ? providerName(editing) : ''"
      width="640px"
      destroy-on-close
      class="provider-dialog"
    >
      <template v-if="editing">
        <p class="dialog-docs">
          {{ editing.docs_note }}
          <el-link v-if="editing.docs_url" :href="editing.docs_url" target="_blank" type="primary">
            {{ t('providers.openDocs') }}
          </el-link>
        </p>
        <el-alert
          v-if="editing.scope === 'global'"
          :title="t('providers.globalAlert')"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />
        <el-form label-width="160px" label-position="right">
          <el-form-item
            v-for="field in (editing.fields || [])"
            :key="field.key"
            :label="fieldLabel(field)"
            :required="!!field.required"
          >
            <el-switch v-if="field.type === 'switch'" v-model="form.config[field.key]" />
            <el-select
              v-else-if="field.type === 'select'"
              v-model="form.config[field.key]"
              style="width: 100%"
            >
              <el-option
                v-for="o in field.options || []"
                :key="o.value"
                :label="o.label"
                :value="o.value"
              />
            </el-select>
            <el-input
              v-else-if="field.type === 'textarea'"
              v-model="form.config[field.key]"
              type="textarea"
              :rows="5"
              :placeholder="secretPlaceholder(field)"
              autocomplete="off"
            />
            <el-input
              v-else-if="field.type === 'password'"
              v-model="form.config[field.key]"
              type="password"
              show-password
              :placeholder="secretPlaceholder(field)"
              autocomplete="new-password"
            />
            <el-input
              v-else
              v-model="form.config[field.key]"
              :placeholder="field.placeholder || ''"
            />
            <div v-if="field.secret && form.config[`_${field.key}_set`]" class="secret-hint">
              {{ t('providers.secretKept') }}
            </div>
          </el-form-item>
          <el-form-item :label="t('providers.notes')">
            <el-input v-model="form.notes" type="textarea" :rows="2" :placeholder="t('providers.notesPh')" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="dialog = false">{{ t('common.cancel') }}</el-button>
        <el-button
          v-if="editing && (editing.key === 'google_translate' || editing.key === 'google_ads' || editing.key === 'facebook_ads')"
          :loading="testing"
          @click="runTest"
        >{{ t('providers.test') }}</el-button>
        <el-button type="danger" :loading="saving" @click="save">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getProviders, getProviderDetail, saveProvider, testProvider } from '../api'
import { workspaceAppId, workspaceAppIdOrDefault } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t, locale } = useI18n()
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const dialog = ref(false)
const rows = ref([])
const editing = ref(null)
const form = reactive({
  config: {},
  notes: '',
})

function providerName(item) {
  if (!item) return ''
  return locale.value === 'zh-CN' ? (item.name_zh || item.name) : item.name
}

function fieldLabel(field) {
  return locale.value === 'zh-CN' ? (field.label_zh || field.label) : field.label
}

function iconLetter(item) {
  const n = item.name_zh || item.name || '?'
  return n.charAt(0).toUpperCase()
}

function statusType(status) {
  if (status === 'configured') return 'success'
  if (status === 'partial') return 'warning'
  if (status === 'disabled') return 'info'
  return 'danger'
}

function secretPlaceholder(field) {
  if (form.config[`_${field.key}_set`]) {
    return t('providers.secretPlaceholder')
  }
  return field.placeholder || ''
}

function defaultConfig(fields) {
  const cfg = {}
  for (const f of fields || []) {
    if (f.type === 'switch') {
      cfg[f.key] = f.default !== undefined ? !!f.default : false
    } else if (f.default !== undefined) {
      cfg[f.key] = f.default
    } else {
      cfg[f.key] = ''
    }
  }
  return cfg
}

async function load() {
  loading.value = true
  try {
    const res = await getProviders({ app_id: workspaceAppId() })
    rows.value = (res.results && res.results.list) || []
  } catch (e) {
    ElMessage.error(e?.message || 'load failed')
  } finally {
    loading.value = false
  }
}

async function openEdit(item) {
  editing.value = item
  form.config = defaultConfig(item.fields)
  form.notes = item.notes || ''
  dialog.value = true
  try {
    const appId = workspaceAppIdOrDefault()
    if (!appId) {
      ElMessage.warning(t('common.pickApp'))
      dialog.value = false
      return
    }
    const res = await getProviderDetail(item.key, { app_id: appId })
    const data = res.results || {}
    const cfg = data.config || {}
    form.config = { ...defaultConfig(item.fields), ...cfg }
    form.notes = data.notes || ''
    if (data.provider) {
      editing.value = { ...item, ...data.provider, docs_note: data.provider.docs_note || item.docs_note }
    }
  } catch (e) {
    ElMessage.error(e?.message || 'load detail failed')
  }
}

async function save() {
  if (!editing.value) return
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  saving.value = true
  try {
    const payload = {
      app_id: appId,
      config: { ...form.config },
      notes: form.notes,
    }
    Object.keys(payload.config).forEach((k) => {
      if (k.startsWith('_')) delete payload.config[k]
    })
    await saveProvider(editing.value.key, payload)
    ElMessage.success(t('common.saved'))
    dialog.value = false
    await load()
  } catch (e) {
    ElMessage.error(e?.message || 'save failed')
  } finally {
    saving.value = false
  }
}

async function runTest() {
  if (!editing.value) return
  const appId = workspaceAppIdOrDefault()
  if (!appId) {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  // Persist current form first so test uses latest key
  testing.value = true
  try {
    const payload = {
      app_id: appId,
      config: { ...form.config },
      notes: form.notes,
    }
    Object.keys(payload.config).forEach((k) => {
      if (k.startsWith('_')) delete payload.config[k]
    })
    await saveProvider(editing.value.key, payload)
    const res = await testProvider(editing.value.key, { sample: 'Hello' })
    const data = res.results || {}
    if (data.ok) {
      if (editing.value.key === 'google_ads' || editing.value.key === 'facebook_ads') {
        ElMessage.success(
          `${t('providers.testOk')}: ${data.campaign_count || 0} campaigns` +
            (data.sample_campaign_id ? ` (e.g. ${data.sample_campaign_id})` : ''),
        )
      } else {
        ElMessage.success(`${t('providers.testOk')}: ${data.translated || ''}`)
      }
      await load()
    } else {
      ElMessage.error(data.error || res.message || t('providers.testFail'))
    }
  } catch (e) {
    ElMessage.error(e?.message || e?.results?.error || t('providers.testFail'))
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 8px;
}
.provider-card {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 16px 18px;
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
  display: flex;
  flex-direction: column;
  min-height: 200px;
}
.provider-card:hover {
  border-color: #ff4d4f;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}
.provider-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.provider-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #fff;
  background: #595959;
  font-size: 16px;
}
.provider-icon[data-cat='billing'] { background: #d48806; }
.provider-icon[data-cat='auth'] { background: #1d39c4; }
.provider-icon[data-cat='maps'] { background: #08979c; }
.provider-icon[data-cat='push'] { background: #c41d7f; }
.provider-icon[data-cat='ai'] { background: #531dab; }
.provider-icon[data-cat='trust'] { background: #389e0d; }
.provider-icon[data-cat='ads'] { background: #cf1322; }
.provider-icon[data-cat='analytics'] { background: #0958d9; }
.provider-name {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: #262626;
}
.provider-note {
  margin: 0;
  flex: 1;
  font-size: 12px;
  line-height: 1.5;
  color: #8c8c8c;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.provider-meta {
  display: flex;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.provider-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}
.dialog-docs {
  font-size: 13px;
  color: #595959;
  margin: 0 0 16px;
  line-height: 1.5;
}
.secret-hint {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 4px;
}
.pro-hint {
  margin: 0 0 8px;
  color: #8c8c8c;
  font-size: 13px;
}
</style>
