<template>
  <PageContainer :title="t('matchmaker.title')" :sub-title="t('matchmaker.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">

      <el-button type="danger" size="small" @click="load">{{ t('common.refresh') }}</el-button>

    </WorkspaceFilter>
    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column prop="matchmaker_id" :label="t('matchmaker.mm')" min-width="120" />
      <el-table-column prop="user_a_id" :label="t('matchmaker.a')" min-width="120" />
      <el-table-column prop="user_b_id" :label="t('matchmaker.b')" min-width="120" />
      <el-table-column prop="a_status" :label="t('matchmaker.aStatus')" min-width="120" />
      <el-table-column prop="b_status" :label="t('matchmaker.bStatus')" min-width="120" />
      <el-table-column v-if="hasActions" :label="t('common.actions')" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" @click="voidInvite(row)">{{ t('matchmaker.void') }}</el-button>
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
import { getMatchmaker, matchmakerAction } from '../api'
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

    const res = await getMatchmaker(params)
    rows.value = res.results || []
    total.value = (res.pagination && res.pagination.total) || rows.value.length
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function voidInvite(row) {
  await ElMessageBox.confirm(t('common.updated') + '?', { type: 'warning' })
  await matchmakerAction({ app_id: workspaceAppId(), action: 'void', id: row.id })
  ElMessage.success(t('common.updated'))
  load()
}


onMounted(load)
</script>

<style scoped>
.pager { margin-top: 12px; color: #666; font-size: 13px; }
.pro-control-sm { width: 160px; }
</style>
