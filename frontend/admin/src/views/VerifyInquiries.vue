<template>
  <PageContainer :title="t('verifyAdmin.title')" :sub-title="t('verifyAdmin.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">

      <el-button type="danger" size="small" @click="load">{{ t('common.refresh') }}</el-button>

    </WorkspaceFilter>
    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column prop="nickname" :label="t('common.user')" min-width="120" />
      <el-table-column prop="inquiry_id" :label="t('verifyAdmin.inquiry')" min-width="120" />
      <el-table-column prop="status" :label="t('common.status')" min-width="120" />
      <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="120" />
      <el-table-column v-if="hasActions" :label="t('common.actions')" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" @click="approve(row)">{{ t('verifyAdmin.approve') }}</el-button>
          <el-button link type="danger" @click="reject(row)">{{ t('verifyAdmin.reject') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager" v-if="total">{{ t('common.total', { n: total }) }}</div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getVerifyInquiries, verifyInquiryAction } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const hasActions = true


async function load() {
  loading.value = true
  try {
    const params = { app_id: workspaceAppId(), currentPage: 1, pageSize: 50 }

    const res = await getVerifyInquiries(params)
    rows.value = res.results || []
    total.value = (res.pagination && res.pagination.total) || rows.value.length
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function approve(row) {
  await ElMessageBox.confirm(t('common.updated') + '?', { type: 'warning' })
  await verifyInquiryAction({ app_id: workspaceAppId(), action: 'decide', id: row.id, approve: true })
  ElMessage.success(t('common.updated'))
  load()
}

async function reject(row) {
  await ElMessageBox.confirm(t('common.updated') + '?', { type: 'warning' })
  await verifyInquiryAction({ app_id: workspaceAppId(), action: 'decide', id: row.id, approve: false })
  ElMessage.success(t('common.updated'))
  load()
}


onMounted(load)
</script>

<style scoped>
.pager { margin-top: 12px; color: #666; font-size: 13px; }
.pro-control-sm { width: 160px; }
</style>
