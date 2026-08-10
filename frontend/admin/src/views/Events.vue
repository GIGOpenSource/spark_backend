<template>
  <PageContainer :title="t('events.title')" :sub-title="t('events.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load">
      <el-button size="small" @click="load">{{ t('common.refresh') }}</el-button>
    </WorkspaceFilter>
    <el-table :data="rows" style="width:100%" v-loading="loading">
      <el-table-column type="index" :width="72" />
      <el-table-column prop="event" :label="t('events.eventName')" min-width="180" />
      <el-table-column prop="label_zh" :label="t('events.labelZh')" min-width="160" />
      <el-table-column prop="count" :label="t('events.count')" width="120" sortable />
      <el-table-column prop="users" :label="t('analytics.users')" width="100" sortable />
    </el-table>
    <div v-if="!rows.length && !loading" class="pro-empty">{{ t('events.empty') }}</div>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getEventsDict } from '../api'
import { workspaceAppId } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t } = useI18n()
const rows = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await getEventsDict({ app_id: workspaceAppId() })
    const list = (res.results && res.results.list) || []
    if (list.length) {
      rows.value = list
    } else {
      const names = (res.results && res.results.events) || []
      rows.value = names.map((e) => ({ event: e, count: 0 }))
    }
  } catch (e) {
    ElMessage.error((e && e.message) || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
