<template>
  <PageContainer :title="t('matches.title')" :sub-title="t('matches.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">

      <el-button type="danger" size="small" @click="load">{{ t('common.refresh') }}</el-button>

    </WorkspaceFilter>
    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column prop="user_a" :label="t('matches.a')" min-width="120" />
      <el-table-column prop="user_b" :label="t('matches.b')" min-width="120" />
      <el-table-column prop="status" :label="t('common.status')" min-width="120" />
      <el-table-column prop="messaging_mode" :label="t('matches.mode')" min-width="120" />
      <el-table-column v-if="hasActions" :label="t('common.actions')" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" @click="unmatch(row)">{{ t('matches.unmatch') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager" v-if="total">
      <span>{{ t('common.total', { n: total }) }}</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="sizes, prev, pager, next"
        background
        small
        @current-change="load"
        @size-change="onPageSizeChange"
      />
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMatches, matchesAction } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const hasActions = true
const page = ref(1)
const pageSize = ref(50)

function onPageSizeChange() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const params = {
      app_id: workspaceAppId(),
      currentPage: page.value,
      pageSize: pageSize.value
    }
    const res = await getMatches(params)
    rows.value = res.results || []
    total.value = (res.pagination && res.pagination.total) || rows.value.length
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function unmatch(row) {
  try {
    await ElMessageBox.confirm(t('common.updated') + '?', { type: 'warning' })
  } catch {
    return
  }
  if (!workspaceAppId() || workspaceAppId() === '*') {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await matchesAction({ app_id: workspaceAppId(), action: 'force_unmatch', match_id: row.id })
    ElMessage.success(t('common.updated'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}


onMounted(load)
</script>

<style scoped>
.pager {
  margin-top: 12px;
  color: #666;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.pro-control-sm { width: 160px; }
</style>
