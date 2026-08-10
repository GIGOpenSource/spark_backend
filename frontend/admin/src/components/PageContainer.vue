<template>
  <div class="pro-page">
    <div class="pro-page-header">
      <div class="pro-page-header-row">
        <div>
          <h1 class="pro-page-title">{{ title }}</h1>
          <p v-if="subTitle" class="pro-page-subtitle">{{ subTitle }}</p>
        </div>
        <div v-if="$slots.extra" class="pro-page-extra">
          <slot name="extra" />
        </div>
      </div>
    </div>
    <div class="pro-page-body" :class="{ 'is-ghost': ghost }">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subTitle: { type: String, default: '' },
  ghost: { type: Boolean, default: false }
})
</script>
