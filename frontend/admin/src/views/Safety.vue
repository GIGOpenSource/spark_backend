<template>
  <PageContainer :title="t('safety.title')" :sub-title="t('safety.subtitle')">
    <WorkspaceFilter @change="load" />
    <PageTabs v-model="tab" :tabs="tabs">
      <template #default="{ active }">
        <div v-show="active === 'photos'">
          <el-table :data="photos" style="width:100%">
            <el-table-column prop="id" :label="t('common.id')" :width="72" />
            <el-table-column prop="nickname" :label="t('common.user')" width="120" />
            <el-table-column :label="t('safety.preview')" width="100">
              <template #default="{ row }">
                <el-image :src="row.url" class="thumb" fit="cover" :preview-src-list="[row.url]" />
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="t('common.createdAt')" min-width="160" />
            <el-table-column :label="t('common.actions')" width="180">
              <template #default="{ row }">
                <el-button link type="success" @click="setPhoto(row, 'approved')">{{ t('safety.approve') }}</el-button>
                <el-button link type="danger" @click="setPhoto(row, 'rejected')">{{ t('safety.reject') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-show="active === 'reports'">
          <el-table :data="reports" style="width:100%">
            <el-table-column prop="id" :label="t('common.id')" :width="72" />
            <el-table-column prop="reason" :label="t('safety.reason')" />
            <el-table-column prop="status" :label="t('common.status')" width="110" />
            <el-table-column prop="detail" :label="t('safety.detail')" />
            <el-table-column :label="t('common.actions')" width="120">
              <template #default="{ row }">
                <el-button link type="primary" v-if="row.status !== 'resolved'" @click="resolve(row)">
                  {{ t('safety.resolve') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-show="active === 'words'">
          <div class="pro-toolbar">
            <el-select v-model="wordCountry" size="small" class="pro-control-sm" :placeholder="t('workspace.countryPlaceholder')">
              <el-option
                v-for="o in COUNTRY_OPTIONS"
                :key="o.value"
                :label="t(`regions.${o.value}`)"
                :value="o.value"
              />
            </el-select>
            <el-input v-model="newWord" size="small" :placeholder="t('safety.addWordPlaceholder')" class="pro-control-lg" />
            <el-button type="danger" size="small" @click="addWord">{{ t('safety.addWord') }}</el-button>
          </div>
          <el-table :data="words" style="width:100%">
            <el-table-column prop="word" :label="t('safety.word')" />
            <el-table-column prop="country" :label="t('safety.country')" width="120">
              <template #default="{ row }">{{ regionText(row.country) }}</template>
            </el-table-column>
            <el-table-column prop="kind" :label="t('safety.kind')" />
          </el-table>
        </div>

        <div v-show="active === 'domains'">
          <div class="pro-toolbar">
            <el-input v-model="newDomain" size="small" placeholder="instagram.com" class="pro-control-lg" />
            <el-button size="small" @click="addDomain">{{ t('safety.addDomain') }}</el-button>
          </div>
          <el-table :data="domains" style="width:100%">
            <el-table-column prop="domain" :label="t('safety.domain')" />
          </el-table>
        </div>
      </template>
    </PageTabs>
  </PageContainer>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getSafety, saveSafety } from '../api'
import { getWorkspace, workspaceAppId, COUNTRY_OPTIONS } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'
import PageTabs from '../components/PageTabs.vue'

const { t, te } = useI18n()
const tabs = computed(() => [
  { name: 'photos', label: t('safety.tabPhotos') },
  { name: 'reports', label: t('safety.tabReports') },
  { name: 'words', label: t('safety.tabWords') },
  { name: 'domains', label: t('safety.tabDomains') }
])
const tab = ref('photos')
const reports = ref([])
const words = ref([])
const domains = ref([])
const photos = ref([])
const newWord = ref('')
const newDomain = ref('')
const wordCountry = ref(getWorkspace().country || '*')

function regionText(code) {
  const key = `regions.${code || '*'}`
  return te(key) ? t(key) : (code || '*')
}

async function load() {
  const ws = getWorkspace()
  wordCountry.value = ws.country || '*'
  const res = await getSafety({ app_id: workspaceAppId(), country: ws.country })
  reports.value = (res.results && res.results.reports) || []
  words.value = (res.results && res.results.words) || []
  domains.value = (res.results && res.results.domains) || []
  photos.value = (res.results && res.results.photos) || []
}

async function resolve(row) {
  await saveSafety({ app_id: workspaceAppId(), kind: 'report_status', id: row.id, status: 'resolved' })
  ElMessage.success(t('safety.resolved'))
  load()
}

async function setPhoto(row, status) {
  await saveSafety({ app_id: workspaceAppId(), kind: 'photo_status', id: row.id, status })
  ElMessage.success(status === 'approved' ? t('safety.approve') : t('safety.reject'))
  load()
}

async function addWord() {
  if (!newWord.value.trim()) return
  await saveSafety({
    app_id: workspaceAppId(),
    country: wordCountry.value || '*',
    kind: 'word',
    word: newWord.value.trim()
  })
  newWord.value = ''
  ElMessage.success(t('safety.added'))
  load()
}

async function addDomain() {
  if (!newDomain.value.trim()) return
  await saveSafety({ app_id: workspaceAppId(), kind: 'domain', domain: newDomain.value.trim() })
  newDomain.value = ''
  ElMessage.success(t('safety.added'))
  load()
}

onMounted(load)
</script>

<style scoped>
.thumb {
  width: 56px;
  height: 56px;
  border-radius: var(--pro-radius-sm);
}
</style>
