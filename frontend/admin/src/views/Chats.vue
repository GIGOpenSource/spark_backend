<template>
  <PageContainer :title="t('chats.title')" :sub-title="t('chats.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">
      <el-input
        v-model="q"
        size="small"
        :placeholder="t('chats.searchPlaceholder')"
        class="pro-control-lg"
        clearable
        @keyup.enter="load"
      />
      <el-button type="danger" size="small" @click="load">{{ t('common.search') }}</el-button>
    </WorkspaceFilter>

    <el-table :data="rows" style="width:100%" v-loading="loading" @row-click="openMessages">
      <el-table-column prop="id" :label="t('common.id')" width="72" />
      <el-table-column :label="t('chats.userA')" min-width="160">
        <template #default="{ row }">
          <div class="peer">
            <span>{{ row.user_a?.nickname || '-' }}</span>
            <span class="peer-meta">#{{ row.user_a?.id }} · {{ row.user_a?.email }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column :label="t('chats.userB')" min-width="160">
        <template #default="{ row }">
          <div class="peer">
            <span>{{ row.user_b?.nickname || '-' }}</span>
            <span class="peer-meta">#{{ row.user_b?.id }} · {{ row.user_b?.email }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="last_message" :label="t('chats.lastMessage')" min-width="200" show-overflow-tooltip />
      <el-table-column prop="message_count" :label="t('chats.msgCount')" width="90" />
      <el-table-column prop="last_at" :label="t('chats.lastAt')" min-width="160" />
      <el-table-column :label="t('common.actions')" width="100" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="openMessages(row)">{{ t('chats.view') }}</el-button>
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

    <el-drawer v-model="msgVisible" :title="msgTitle" size="520px" destroy-on-close>
      <div v-loading="msgLoading" class="msg-list">
        <div v-if="!messages.length && !msgLoading" class="msg-empty">{{ t('chats.empty') }}</div>
        <div
          v-for="m in messages"
          :key="m.id"
          class="msg-item"
          :class="{ mine: activeConv && m.sender_id === activeConv.user_a_id }"
        >
          <div class="msg-meta">
            <span class="msg-sender">{{ m.sender_nickname }}</span>
            <span class="msg-time">{{ m.created_at }}</span>
          </div>
          <div class="msg-bubble">
            <template v-if="m.msg_type === 'image' || m.msg_type === 'photo'">
              <el-image :src="m.content" fit="cover" class="msg-image" :preview-src-list="[m.content]" />
            </template>
            <template v-else-if="m.msg_type === 'voice' || m.msg_type === 'audio'">
              <audio :src="m.content" controls preload="none" class="msg-audio" />
              <span v-if="m.duration_ms" class="msg-duration">{{ Math.round(m.duration_ms / 1000) }}s</span>
            </template>
            <template v-else>
              {{ m.content }}
            </template>
          </div>
          <div v-if="m.translated" class="msg-translated">{{ m.translated }}</div>
        </div>
      </div>
    </el-drawer>
  </PageContainer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getChats, getChatMessages } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const q = ref('')
const rows = ref([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(50)

const msgVisible = ref(false)
const msgLoading = ref(false)
const messages = ref([])
const activeConv = ref(null)

const msgTitle = computed(() => {
  if (!activeConv.value) return t('chats.messages')
  const a = activeConv.value.user_a?.nickname || activeConv.value.user_a_nickname || 'A'
  const b = activeConv.value.user_b?.nickname || activeConv.value.user_b_nickname || 'B'
  return `${t('chats.messages')} · ${a} ↔ ${b}`
})

function onPageSizeChange() {
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const res = await getChats({
      app_id: workspaceAppId(),
      q: q.value,
      currentPage: page.value,
      pageSize: pageSize.value
    })
    rows.value = res.results || []
    total.value = (res.pagination && res.pagination.total) || rows.value.length
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function openMessages(row) {
  activeConv.value = row
  msgVisible.value = true
  msgLoading.value = true
  messages.value = []
  try {
    const res = await getChatMessages({
      conversation_id: row.id,
      currentPage: 1,
      pageSize: 200
    })
    messages.value = res.results || []
    if (res.conversation) {
      activeConv.value = { ...row, ...res.conversation }
    }
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    msgLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.pager {
  margin-top: var(--pro-space-md);
  color: var(--pro-text-secondary);
  font-size: var(--pro-font-sm);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.peer { display: flex; flex-direction: column; gap: 2px; line-height: 1.3; }
.peer-meta { font-size: 12px; color: var(--pro-text-secondary); }
.msg-list { display: flex; flex-direction: column; gap: 12px; padding-bottom: 24px; }
.msg-empty { color: var(--pro-text-secondary); text-align: center; padding: 40px 0; }
.msg-item { max-width: 90%; }
.msg-meta {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--pro-text-secondary);
}
.msg-sender { font-weight: 600; color: var(--pro-text); }
.msg-bubble {
  display: inline-block;
  padding: 8px 12px;
  border-radius: 10px;
  background: #f5f5f5;
  word-break: break-word;
  white-space: pre-wrap;
}
.msg-item.mine .msg-bubble { background: #ffe8ea; }
.msg-translated {
  margin-top: 4px;
  font-size: 12px;
  color: var(--pro-text-secondary);
}
.msg-image { width: 160px; height: 160px; border-radius: 8px; }
.msg-audio { width: 220px; vertical-align: middle; }
.msg-duration { margin-left: 8px; font-size: 12px; color: #888; }
</style>
