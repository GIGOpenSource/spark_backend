<template>
	<view class="page">
		<view class="header">
			<text class="back" @click="back">‹</text>
			<text class="title">{{ title }}</text>
		</view>
		<slot />
	</view>
</template>
<script setup>
defineProps({ title: { type: String, default: '' } })
function back() { uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/me/index' }) }) }
</script>
<style scoped>
.page { min-height:100vh; background:var(--bg,#fff); padding: calc(env(safe-area-inset-top) + 24rpx) 24rpx 80rpx; color:var(--text,#111); }
.header { display:flex; flex-direction:row; align-items:center; margin-bottom:24rpx; }
.back { font-size:48rpx; width:60rpx; color:var(--text,#111); }
.title { font-size:40rpx; font-weight:700; }
</style>
