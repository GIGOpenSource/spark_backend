<template>
	<view class="page" />
</template>

<script setup>
import { onMounted } from 'vue'
onMounted(() => {
	const token = uni.getStorageSync('token')
	if (token) uni.switchTab({ url: '/pages/discover/index' })
	else uni.reLaunch({ url: '/pages/auth/welcome' })
})
</script>

<style scoped>
.page { min-height: 100vh; background: #FFFFFF; }
</style>
