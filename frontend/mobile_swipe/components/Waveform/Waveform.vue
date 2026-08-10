<template>
	<view class="wave" :class="{ playing }" @click="$emit('toggle')">
		<view
			v-for="(h, i) in bars"
			:key="i"
			class="bar"
			:style="{ height: h + '%', animationDelay: (i * 0.05) + 's' }"
		/>
		<text class="label" v-if="label">{{ label }}</text>
	</view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	playing: { type: Boolean, default: false },
	seed: { type: [String, Number], default: 1 },
	label: { type: String, default: '' },
	count: { type: Number, default: 18 },
})
defineEmits(['toggle'])

const bars = computed(() => {
	const n = Math.max(8, Math.min(32, props.count))
	const s = String(props.seed || '1')
	let hash = 0
	for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0
	const out = []
	for (let i = 0; i < n; i++) {
		const v = ((hash >> (i % 16)) ^ (i * 17)) & 0xff
		out.push(28 + (v % 72))
	}
	return out
})
</script>

<!-- F-11: gap removed; prefer sibling margin -->
<style scoped>
.wave {
	display: flex; flex-direction: row; align-items: flex-end;
	height: 72rpx; padding: 12rpx 16rpx; background: #FFF8E1;
	border-radius: 16rpx; border: 1px solid rgba(255,198,41,0.4);

}
.bar {
	flex: 1; min-width: 6rpx; max-width: 12rpx;
	background: #FFC629; border-radius: 999rpx;
	transform-origin: bottom;
}
.playing .bar {
	animation: pulse 0.9s ease-in-out infinite;
}
@keyframes pulse {
	0%, 100% { transform: scaleY(0.55); opacity: 0.7; }
	50% { transform: scaleY(1); opacity: 1; }
}
.label {
	margin-left: 12rpx; color: #8A6D00; font-size: 22rpx; font-weight: 700;
	align-self: center; white-space: nowrap;
}
</style>
