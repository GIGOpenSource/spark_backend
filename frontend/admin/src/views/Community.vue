<template>
  <PageContainer :title="t('community.title')" :sub-title="t('community.subtitle')">
    <el-tabs v-model="tab">
      <el-tab-pane :label="t('community.postsTab')" name="posts">
        <WorkspaceFilter :show-country="false" @change="loadPosts">
          <el-select v-model="postType" size="small" clearable class="pro-control-sm" :placeholder="t('community.postType')" @change="loadPosts">
            <el-option label="moment" value="moment" />
            <el-option label="community" value="community" />
            <el-option label="video" value="video" />
          </el-select>
          <el-select v-model="postStatus" size="small" clearable class="pro-control-sm" :placeholder="t('common.status')" @change="loadPosts">
            <el-option label="visible" value="visible" />
            <el-option label="hidden" value="hidden" />
            <el-option label="deleted" value="deleted" />
          </el-select>
          <el-input v-model="q" size="small" class="pro-control-lg" clearable :placeholder="t('community.searchPlaceholder')" @keyup.enter="loadPosts" />
          <el-button type="danger" size="small" @click="loadPosts">{{ t('common.search') }}</el-button>
          <el-button size="small" @click="batchHide">{{ t('community.batchHide') }}</el-button>
        </WorkspaceFilter>

        <el-table :data="posts" v-loading="loadingPosts" style="width:100%" @selection-change="onSel">
          <el-table-column type="selection" width="42" />
          <el-table-column prop="id" :label="t('common.id')" width="72" />
          <el-table-column prop="post_type" :label="t('community.postType')" width="110" />
          <el-table-column prop="author_nickname" :label="t('common.user')" min-width="120" />
          <el-table-column prop="text" :label="t('community.text')" min-width="200" show-overflow-tooltip />
          <el-table-column prop="like_count" :label="t('community.likes')" width="80" />
          <el-table-column prop="comment_count" :label="t('community.comments')" width="80" />
          <el-table-column prop="status" :label="t('common.status')" width="100" />
          <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="160" />
          <el-table-column :label="t('common.actions')" width="180" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status !== 'hidden'" link @click="setPostStatus(row, 'hidden')">{{ t('community.hide') }}</el-button>
              <el-button v-if="row.status !== 'visible'" link type="success" @click="setPostStatus(row, 'visible')">{{ t('community.show') }}</el-button>
              <el-button v-if="row.status !== 'deleted'" link type="danger" @click="setPostStatus(row, 'deleted')">{{ t('common.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager" v-if="postsTotal">{{ t('common.total', { n: postsTotal }) }}</div>
      </el-tab-pane>

      <el-tab-pane :label="t('community.topicsTab')" name="topics">
        <div class="toolbar">
          <el-button type="danger" size="small" @click="openTopic()">{{ t('community.addTopic') }}</el-button>
          <el-button size="small" @click="loadTopics">{{ t('common.refresh') }}</el-button>
        </div>
        <el-table :data="topics" v-loading="loadingTopics" style="width:100%">
          <el-table-column prop="id" :label="t('common.id')" width="72" />
          <el-table-column prop="title" :label="t('community.topicTitle')" min-width="160" />
          <el-table-column prop="sort" :label="t('community.sort')" width="80" />
          <el-table-column :label="t('common.active')" width="90">
            <template #default="{ row }">{{ row.is_active ? t('common.yes') : t('common.no') }}</template>
          </el-table-column>
          <el-table-column :label="t('common.actions')" width="100">
            <template #default="{ row }">
              <el-button link type="primary" @click="openTopic(row)">{{ t('common.edit') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="topicVisible" :title="topicForm.id ? t('common.edit') : t('community.addTopic')" width="420px">
      <el-form label-width="80px">
        <el-form-item :label="t('community.topicTitle')">
          <el-input v-model="topicForm.title" />
        </el-form-item>
        <el-form-item :label="t('community.sort')">
          <el-input-number v-model="topicForm.sort" :min="0" />
        </el-form-item>
        <el-form-item :label="t('common.active')">
          <el-switch v-model="topicForm.is_active" />
        </el-form-item>
        <el-form-item :label="t('community.cover')">
          <el-input v-model="topicForm.cover" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="topicVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="danger" @click="saveTopic">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getPostsAdmin, updatePostAdmin, getTopicsAdmin, saveTopicAdmin } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const tab = ref('posts')
const posts = ref([])
const postsTotal = ref(0)
const loadingPosts = ref(false)
const postType = ref('')
const postStatus = ref('visible')
const q = ref('')
const selectedIds = ref([])

const topics = ref([])
const loadingTopics = ref(false)
const topicVisible = ref(false)
const topicForm = ref({ id: null, title: '', sort: 0, is_active: true, cover: '' })

async function loadPosts() {
  loadingPosts.value = true
  try {
    const params = {
      app_id: workspaceAppId(),
      q: q.value,
      currentPage: 1,
      pageSize: 50
    }
    if (postType.value) params.post_type = postType.value
    if (postStatus.value) params.status = postStatus.value
    const res = await getPostsAdmin(params)
    posts.value = res.results || []
    postsTotal.value = (res.pagination && res.pagination.total) || posts.value.length
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loadingPosts.value = false
  }
}

async function setPostStatus(row, status) {
  try {
    await ElMessageBox.confirm(t('community.confirmStatus', { status }), { type: 'warning' })
  } catch {
    return
  }
  try {
    await updatePostAdmin({ app_id: workspaceAppId(), id: row.id, status })
    ElMessage.success(t('common.updated'))
    loadPosts()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

function onSel(rows) {
  selectedIds.value = (rows || []).map((r) => r.id)
}

async function batchHide() {
  if (!selectedIds.value.length) {
    ElMessage.warning(t('community.batchEmpty') || 'Select rows')
    return
  }
  try {
    await ElMessageBox.confirm(t('community.confirmStatus', { status: 'hidden' }), { type: 'warning' })
  } catch {
    return
  }
  try {
    await updatePostAdmin({ app_id: workspaceAppId(), ids: selectedIds.value, status: 'hidden' })
    ElMessage.success(t('common.updated'))
    loadPosts()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

async function loadTopics() {
  loadingTopics.value = true
  try {
    const res = await getTopicsAdmin({ app_id: workspaceAppId() })
    topics.value = (res.results && res.results.list) || []
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  } finally {
    loadingTopics.value = false
  }
}

function openTopic(row) {
  if (row) {
    topicForm.value = {
      id: row.id,
      title: row.title,
      sort: row.sort || 0,
      is_active: !!row.is_active,
      cover: row.cover || ''
    }
  } else {
    topicForm.value = { id: null, title: '', sort: 0, is_active: true, cover: '' }
  }
  topicVisible.value = true
}

async function saveTopic() {
  if (!topicForm.value.title || !String(topicForm.value.title).trim()) {
    ElMessage.warning(t('community.topicTitleRequired') || 'Title required')
    return
  }
  try {
    await saveTopicAdmin({
      app_id: workspaceAppId(),
      ...topicForm.value
    })
    ElMessage.success(t('common.saved'))
    topicVisible.value = false
    loadTopics()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

watch(tab, (v) => {
  if (v === 'topics') loadTopics()
  else loadPosts()
})

onMounted(loadPosts)
</script>

<style scoped>
.pager { margin-top: 12px; color: #666; font-size: 13px; }
.pro-control-lg { width: 200px; }
.pro-control-sm { width: 130px; }
.toolbar { margin-bottom: 12px; display: flex; gap: 8px; }
</style>
