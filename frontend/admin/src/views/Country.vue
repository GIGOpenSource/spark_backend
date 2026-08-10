<template>
  <PageContainer :title="t('country.title')" :sub-title="t('country.subtitle')">
    <WorkspaceFilter :show-country="false" @change="load" />
    <el-form class="pro-form" label-width="120px">
      <el-form-item :label="t('country.country')">
        <el-select v-model="form.country" style="width:100%">
          <el-option
            v-for="o in COUNTRY_OPTIONS"
            :key="o.value"
            :label="t(`regions.${o.value}`)"
            :value="o.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('country.minAge')">
        <el-input-number v-model="form.min_age" :min="16" :max="21" />
      </el-form-item>
      <el-form-item :label="t('country.currency')">
        <el-input v-model="form.currency" placeholder="USD" />
      </el-form-item>
      <el-form-item :label="t('country.storeNote')">
        <el-input v-model="form.note" type="textarea" :rows="2" />
      </el-form-item>
      <el-button type="danger" @click="save">{{ t('common.save') }}</el-button>
    </el-form>

    <el-table :data="rows" class="pro-section-gap" style="width:100%">
      <el-table-column prop="country" :label="t('country.country')" width="120">
        <template #default="{ row }">{{ regionText(row.country) }}</template>
      </el-table-column>
      <el-table-column :label="t('country.config')">
        <template #default="{ row }">
          <code>{{ JSON.stringify(row.config || {}) }}</code>
        </template>
      </el-table-column>
    </el-table>
  </PageContainer>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getCountryConfig, saveCountryConfig } from '../api'
import { workspaceAppId, COUNTRY_OPTIONS } from '../workspace'
import PageContainer from '../components/PageContainer.vue'
import WorkspaceFilter from '../components/WorkspaceFilter.vue'

const { t, te } = useI18n()
const rows = ref([])
const form = reactive({ country: '*', min_age: 18, currency: 'USD', note: '' })

function regionText(code) {
  const key = `regions.${code || '*'}`
  return te(key) ? t(key) : (code || '*')
}

async function load() {
  try {
    const res = await getCountryConfig({ app_id: workspaceAppId() })
    rows.value = (res.results && res.results.list) || []
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
    await saveCountryConfig({
      app_id: workspaceAppId(),
      country: form.country || '*',
      config: {
        min_age: form.min_age,
        currency: form.currency,
        note: form.note
      }
    })
    ElMessage.success(t('common.saved'))
    load()
  } catch (e) {
    ElMessage.error(e?.message || t('common.loadFailed'))
  }
}

onMounted(load)
</script>

<style scoped>
code { font-size: var(--pro-font-xs); color: var(--pro-text-secondary); }
</style>
