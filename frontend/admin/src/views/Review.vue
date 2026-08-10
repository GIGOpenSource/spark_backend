<template>
  <PageContainer :title="t('review.title')" :sub-title="t('review.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load" />
    <el-form class="pro-form" label-width="120px">
      <el-form-item :label="t('review.platform')">
        <el-select v-model="form.platform" style="width:100%">
          <el-option v-for="o in PLATFORM_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('review.package')"><el-input v-model="form.package_name" /></el-form-item>
      <el-form-item :label="t('review.version')"><el-input v-model="form.version" /></el-form-item>
      <el-form-item :label="t('review.enabled')"><el-switch v-model="form.enabled" /></el-form-item>
      <el-button type="danger" @click="save">{{ t('common.save') }}</el-button>
    </el-form>

    <el-table :data="rows" class="pro-section-gap" style="width:100%">
      <el-table-column prop="platform" :label="t('review.platform')" />
      <el-table-column prop="package_name" :label="t('review.package')" />
      <el-table-column prop="version" :label="t('review.version')" />
      <el-table-column prop="enabled" :label="t('review.enabled')" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'danger' : 'info'" size="small">
            {{ row.enabled ? t('common.on') : t('common.off') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('common.actions')" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="quickToggle(row)">
            {{ row.enabled ? t('common.disable') : t('common.enable') }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </PageContainer>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getReview, saveReview } from '../api'
import { workspaceAppId, PLATFORM_OPTIONS } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const form = reactive({
  platform: 'ios',
  package_name: 'com.spark.app',
  version: '1.0.0',
  enabled: false
})
const rows = ref([])

async function load() {
  try {
    const res = await getReview({ app_id: workspaceAppId() })
    rows.value = ((res.results && res.results.list) || []).filter((r) =>
      r.platform === 'ios' || r.platform === 'android'
    )
    const first = rows.value[0]
    if (first) {
      Object.assign(form, {
        platform: first.platform,
        package_name: first.package_name,
        version: first.version,
        enabled: !!first.enabled
      })
    }
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function save() {
  if (!workspaceAppId() || workspaceAppId() === '*') {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await saveReview({ app_id: workspaceAppId(), ...form })
    ElMessage.success(t('common.saved'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function quickToggle(row) {
  if (!workspaceAppId() || workspaceAppId() === '*') {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await saveReview({
      app_id: workspaceAppId(),
      platform: row.platform,
      package_name: row.package_name,
      version: row.version,
      enabled: !row.enabled
    })
    ElMessage.success(t('common.updated'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

onMounted(load)
</script>
