<template>
	<view class="expiry-ring" :style="wrapStyle">
		<view class="ring-track" :style="ringStyle" />
		<view class="ring-hole" :style="holeStyle">
			<slot />
		</view>
	</view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	/** 0–1 remaining fraction (1 = full ring) */
	progress: { type: Number, default: 1 },
	size: { type: [Number, String], default: 110 },
	stroke: { type: [Number, String], default: 6 },
	color: { type: String, default: '#FF6B9A' },
	trackColor: { type: String, default: '#FFE0EA' },
	urgentColor: { type: String, default: '#FFC629' },
})

const sizePx = computed(() => {
	const n = Number(props.size)
	return Number.isFinite(n) ? n : 110
})

const strokePx = computed(() => {
	const n = Number(props.stroke)
	return Number.isFinite(n) ? n : 6
})

const ratio = computed(() => {
	const p = Number(props.progress)
	if (!Number.isFinite(p)) return 0
	return Math.max(0, Math.min(1, p))
})

const activeColor = computed(() => (ratio.value <= 0.25 ? props.urgentColor : props.color))

const wrapStyle = computed(() => ({
	width: `${sizePx.value}rpx`,
	height: `${sizePx.value}rpx`,
}))

const ringStyle = computed(() => {
	const deg = Math.round(ratio.value * 360)
	return {
		background: `conic-gradient(${activeColor.value} 0deg ${deg}deg, ${props.trackColor} ${deg}deg 360deg)`,
	}
})

const holeStyle = computed(() => {
	const inset = strokePx.value
	return {
		inset: `${inset}rpx`,
	}
})
</script>

<style scoped>
.expiry-ring {
	position: relative;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}
.ring-track {
	position: absolute;
	inset: 0;
	border-radius: 50%;
}
.ring-hole {
	position: absolute;
	border-radius: 50%;
	overflow: hidden;
	background: #FFF7FA;
	display: flex;
	align-items: center;
	justify-content: center;
}
.ring-hole > * {
	width: 100%;
	height: 100%;
}
</style>
