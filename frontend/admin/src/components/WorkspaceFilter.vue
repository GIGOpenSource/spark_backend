<template>
  <div class="workspace-filter">
    <el-select
      v-if="showApp"
      v-model="appId"
      size="small"
      :placeholder="t('workspace.productPlaceholder')"
      class="pro-control-md"
      @change="onChange"
    >
      <el-option
        v-for="o in appOptions"
        :key="o.value"
        :label="o.value === '*' ? t('workspace.all') : o.label"
        :value="o.value"
      />
    </el-select>
    <el-select
      v-if="showCountry"
      v-model="country"
      size="small"
      :placeholder="t('workspace.countryPlaceholder')"
      class="pro-control-sm"
      @change="onChange"
    >
      <el-option
        v-for="o in COUNTRY_OPTIONS"
        :key="o.value"
        :label="t(`regions.${o.value}`)"
        :value="o.value"
      />
    </el-select>
    <slot />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  COUNTRY_OPTIONS, getWorkspace, setWorkspace, accessibleAppOptions
} from '../workspace'

const props = defineProps({
  showApp: { type: Boolean, default: true },
  showCountry: { type: Boolean, default: true },
  /** false：权限等需绑定具体 App 的场景，不展示「全部」 */
  includeAll: { type: Boolean, default: true }
})

const emit = defineEmits(['change'])
const { t } = useI18n()

const ws = getWorkspace()
const appId = ref(ws.app_id)
const country = ref(ws.country)
const appOptions = computed(() => accessibleAppOptions({ includeAll: props.includeAll }))

function syncFromStorage() {
  const next = getWorkspace()
  let nextApp = next.app_id
  if (!props.includeAll && nextApp === '*') {
    const first = appOptions.value[0]
    nextApp = first ? first.value : 'spark_main'
    if (props.showApp) setWorkspace({ app_id: nextApp })
  }
  appId.value = nextApp
  country.value = next.country
}

function onChange() {
  const detail = setWorkspace({
    app_id: props.showApp ? appId.value : undefined,
    country: props.showCountry ? country.value : undefined
  })
  emit('change', detail)
}

watch(
  () => [props.showApp, props.showCountry, props.includeAll],
  () => syncFromStorage()
)

onMounted(syncFromStorage)
window.addEventListener('admin-workspace-change', syncFromStorage)
window.addEventListener('storage', syncFromStorage)
</script>

<style scoped>
.workspace-filter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--pro-toolbar-gap);
  margin-bottom: var(--pro-space-lg);
}
</style>
