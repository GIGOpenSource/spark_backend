<template>
	<view class="ring-wrap" :style="{ width: size + 'rpx', height: size + 'rpx' }">
		<view
			class="ring"
			:style="{
				background: `conic-gradient(#FFC629 0 ${deg}deg, rgba(0,0,0,0.08) ${deg}deg 360deg)`,
			}"
		/>
		<view class="inner" :style="innerStyle">
			<slot />
		</view>
	</view>
</template>

<script setup>
import { computed } from 'vue'
import { expireProgress, matchOpenHours } from '@/utils/productProfile.js'

const props = defineProps({
	expireAt: { type: String, default: '' },
	nowMs: { type: Number, default: 0 },
	size: { type: Number, default: 110 },
	thickness: { type: Number, default: 6 },
	totalHours: { type: Number, default: 0 },
})

const progress = computed(() => expireProgress(
	props.expireAt,
	props.nowMs || Date.now(),
	props.totalHours || matchOpenHours() || 24,
))
const deg = computed(() => Math.round(progress.value * 360))
const innerStyle = computed(() => ({
	inset: `${props.thickness}rpx`,
}))
</script>

<style scoped>
.ring-wrap { position: relative; margin: 0 auto; }
.ring {
	position: absolute; inset: 0; border-radius: 50%;
}
.inner {
	position: absolute; border-radius: 50%; overflow: hidden;
	background: #fff;
	display: flex; align-items: center; justify-content: center;
}
</style>
