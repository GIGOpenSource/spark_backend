<template>
  <PageContainer :title="t('groups.title')" :sub-title="t('groups.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">
      <el-input
        v-model="q"
        size="small"
        :placeholder="t('groups.searchPlaceholder')"
        class="pro-control-lg"
        clearable
        @keyup.enter="load"
      />
      <el-select v-model="status" size="small" clearable class="pro-control-sm" :placeholder="t('common.status')" @change="load">
        <el-option label="active" value="active" />
        <el-option label="muted" value="muted" />
        <el-option label="dissolved" value="dissolved" />
      </el-select>
      <el-button type="danger" size="small" @click="load">{{ t('common.search') }}</el-button>
    </WorkspaceFilter>

    <el-table :data="rows" style="width:100%" v-loading="loading" @row-click="openDetail">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column prop="name" :label="t('groups.name')" min-width="140" />
      <el-table-column prop="owner_nickname" :label="t('groups.owner')" min-width="120" />
      <el-table-column prop="member_count" :label="t('groups.members')" width="90" />
      <el-table-column prop="message_count" :label="t('groups.msgCount')" width="90" />
      <el-table-column prop="status" :label="t('common.status')" width="100" />
      <el-table-column prop="last_at" :label="t('groups.lastAt')" min-width="160" />
      <el-table-column :label="t('common.actions')" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="openDetail(row)">{{ t('groups.view') }}</el-button>
          <el-button
            v-if="row.status !== 'muted'"
            link
            @click.stop="setStatus(row, 'muted')"
          >{{ t('groups.mute') }}</el-button>
          <el-button
            v-if="row.status === 'muted'"
            link
            type="success"
            @click.stop="setStatus(row, 'active')"
          >{{ t('groups.unmute') }}</el-button>
          <el-button
            v-if="row.status !== 'dissolved'"
            link
            type="danger"
            @click.stop="setStatus(row, 'dissolved')"
          >{{ t('groups.dissolve') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager" v-if="total">{{ t('common.total', { n: total }) }}</div>

    <el-drawer v-model="visible" :title="detail?.name || t('groups.detail')" size="560px" destroy-on-close>
      <div v-loading="detailLoading">
        <h4>{{ t('groups.members') }}</h4>
        <el-table :data="detail?.members || []" size="small">
          <el-table-column prop="user_id" :label="t('common.id')" width="80" />
          <el-table-column prop="nickname" :label="t('common.user')" />
          <el-table-column prop="role" :label="t('groups.role')" width="90" />
        </el-table>
        <h4>{{ t('groups.messages') }}</h4>
        <div class="msg-list">
          <div v-for="m in detail?.messages || []" :key="m.id" class="msg-item">
            <div class="msg-meta">{{ m.sender_nickname }} · {{ m.created_at }}</div>
            <div class="msg-bubble">{{ m.content }}</div>
          </div>
          <div v-if="!(detail?.messages || []).length" class="msg-empty">{{ t('groups.empty') }}</div>
        </div>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getGroupsAdmin, getGroupAdminDetail, updateGroupAdmin } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const q = ref('')
const status = ref('')
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const visible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

async function load() {
  loading.value = true
  try {
    const params = {
      app_id: workspaceAppId(),
      q: q.value,
      currentPage: 1,
      pageSize: 50
    }
    if (status.value) params.status = status.value
    const res = await getGroupsAdmin(params)
    rows.value = res.results || []
    total.value = (res.pagination && res.pagination.total) || rows.value.length
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  visible.value = true
  detailLoading.value = true
  try {
    const res = await getGroupAdminDetail(row.id, { app_id: workspaceAppId() })
    detail.value = res.results || res.data || res
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    detailLoading.value = false
  }
}

async function setStatus(row, next) {
  await ElMessageBox.confirm(t('groups.confirmStatus', { status: next }), { type: 'warning' })
  await updateGroupAdmin(row.id, { app_id: workspaceAppId(), status: next })
  ElMessage.success(t('common.updated'))
  load()
}

onMounted(load)
</script>

<style scoped>
.pager { margin-top: 12px; color: #666; font-size: 13px; }
.pro-control-lg { width: 220px; }
.pro-control-sm { width: 140px; }
h4 { margin: 16px 0 8px; font-size: 14px; }
.msg-list { max-height: 360px; overflow: auto; }
.msg-item { margin-bottom: 10px; }
.msg-meta { font-size: 12px; color: #999; }
.msg-bubble { background: #f5f5f5; padding: 8px 10px; border-radius: 8px; margin-top: 4px; word-break: break-word; }
.msg-empty { color: #999; font-size: 13px; }
</style>
