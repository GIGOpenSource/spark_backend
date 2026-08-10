<template>
  <PageContainer :title="t('quickMatch.title')" :sub-title="t('quickMatch.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">
      <el-select v-model="status" size="small" clearable class="pro-control-sm" :placeholder="t('common.status')" @change="load">
        <el-option :label="t('quickMatch.active')" value="active" />
        <el-option :label="t('quickMatch.ended')" value="ended" />
      </el-select>
      <el-button type="danger" size="small" @click="load">{{ t('common.refresh') }}</el-button>
      <el-button size="small" @click="purgeStale">{{ t('quickMatch.purge') }}</el-button>
    </WorkspaceFilter>

    <el-alert
      class="mb"
      type="info"
      :closable="false"
      :title="t('quickMatch.waiting', { n: waitingCount })"
    />

    <el-table :data="tickets" size="small" class="mb" v-if="tickets.length">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column :label="t('common.user')" min-width="160">
        <template #default="{ row }">{{ row.nickname }} #{{ row.user_id }}</template>
      </el-table-column>
      <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="160" />
      <el-table-column :label="t('common.actions')" width="120">
        <template #default="{ row }">
          <el-button link type="danger" @click="cancelTicket(row)">{{ t('quickMatch.cancelTicket') }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column :label="t('quickMatch.userA')" min-width="140">
        <template #default="{ row }">{{ row.user_a?.nickname }} #{{ row.user_a?.id }}</template>
      </el-table-column>
      <el-table-column :label="t('quickMatch.userB')" min-width="140">
        <template #default="{ row }">{{ row.user_b?.nickname }} #{{ row.user_b?.id }}</template>
      </el-table-column>
      <el-table-column prop="conversation_id" :label="t('quickMatch.conversation')" width="110" />
      <el-table-column prop="status" :label="t('common.status')" width="100" />
      <el-table-column prop="matched_at" :label="t('quickMatch.matchedAt')" min-width="160" />
      <el-table-column :label="t('common.actions')" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'active'"
            link
            type="danger"
            @click="endPair(row)"
          >{{ t('quickMatch.endPair') }}</el-button>
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
import { getQuickMatchAdmin, quickMatchAction } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const rows = ref([])
const tickets = ref([])
const waitingCount = ref(0)
const total = ref(0)
const loading = ref(false)
const status = ref('active')

async function load() {
  loading.value = true
  try {
    const params = {
      app_id: workspaceAppId(),
      currentPage: 1,
      pageSize: 50
    }
    if (status.value) params.status = status.value
    const res = await getQuickMatchAdmin(params)
    rows.value = res.results || []
    total.value = (res.pagination && res.pagination.total) || rows.value.length
    waitingCount.value = res.waiting_count || 0
    tickets.value = res.waiting_tickets || []
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function cancelTicket(row) {
  try {
    await ElMessageBox.confirm(t('quickMatch.confirmCancel'), { type: 'warning' })
  } catch {
    return
  }
  if (!workspaceAppId() || workspaceAppId() === '*') {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await quickMatchAction({
      app_id: workspaceAppId(),
      action: 'cancel_ticket',
      ticket_id: row.id
    })
    ElMessage.success(t('common.updated'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function endPair(row) {
  try {
    await ElMessageBox.confirm(t('quickMatch.confirmEnd'), { type: 'warning' })
  } catch {
    return
  }
  if (!workspaceAppId() || workspaceAppId() === '*') {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await quickMatchAction({
      app_id: workspaceAppId(),
      action: 'end_pair',
      pair_id: row.id
    })
    ElMessage.success(t('common.updated'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function purgeStale() {
  try {
    await ElMessageBox.confirm(t('quickMatch.confirmPurge') || 'Purge expired tickets?', { type: 'warning' })
  } catch {
    return
  }
  if (!workspaceAppId() || workspaceAppId() === '*') {
    ElMessage.warning(t('common.pickApp'))
    return
  }
  try {
    await quickMatchAction({ app_id: workspaceAppId(), action: 'purge_stale' })
    ElMessage.success(t('common.updated'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

onMounted(load)
</script>

<style scoped>
.mb { margin-bottom: 12px; }
.pager { margin-top: 12px; color: #666; font-size: 13px; }
.pro-control-sm { width: 140px; }
</style>
