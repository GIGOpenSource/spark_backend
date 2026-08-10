<template>
  <el-tabs v-model="active" class="page-tabs" @tab-change="onChange">
    <el-tab-pane v-for="t in tabs" :key="t.name" :label="t.label" :name="t.name" />
  </el-tabs>
  <div class="page-tabs-body">
    <slot :active="active" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  tabs: { type: Array, required: true },
  modelValue: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const active = ref(props.modelValue || (props.tabs[0] && props.tabs[0].name) || '')

watch(
  () => props.modelValue,
  (v) => {
    if (v && v !== active.value) active.value = v
  }
)

function onChange(name) {
  emit('update:modelValue', name)
  emit('change', name)
}
</script>

<style scoped>
.page-tabs {
  margin: calc(-1 * var(--pro-space-sm)) 0 var(--pro-space-lg);
}
.page-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}
.page-tabs-body {
  min-height: 120px;
}
</style>
