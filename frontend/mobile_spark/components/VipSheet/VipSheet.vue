<template>
	<view class="sheet-mask" v-if="show" @click="close">
		<view class="sheet" @click.stop>
			<template v-if="isItemShop">
				<text class="title">Item Shop</text>
				<text class="sub">{{ reasonText }}</text>
				<view
					v-for="p in shopProducts"
					:key="p.product_id"
					class="sku"
					@click="buy(p.product_id)"
				>
					<view>
						<text class="sku-title">{{ p.title || p.product_id }}</text>
						<text class="sku-hint" v-if="showMockHint">Instant delivery · mock</text>
					</view>
					<text class="sku-price">{{ priceLabel(p) }}</text>
				</view>
				<view v-if="!shopProducts.length" class="empty"><text>No packs available</text></view>
			</template>

			<template v-else>
				<text class="title spark-serif">Go Premium</text>
				<text class="sub">{{ reasonText }}</text>

				<view class="tiers">
					<view
						v-for="t in tiers"
						:key="t.id"
						class="tier"
						:class="{ on: tier === t.id, featured: t.id === 'gold' }"
						@click="selectTier(t.id)"
					>
						<text class="tier-name">{{ t.label }}</text>
						<text v-if="t.id === 'gold'" class="badge">Popular</text>
					</view>
				</view>

				<view class="periods">
					<view
						v-for="p in periods"
						:key="p.months"
						class="period"
						:class="{ on: period === p.months }"
						@click="selectPeriod(p.months)"
					>
						<text class="period-m">{{ p.months }} mo</text>
						<text class="period-p">{{ periodPrice(p.months) }}</text>
					</view>
				</view>

				<view class="benefits">
					<text v-for="(b, i) in benefits" :key="i" class="benefit">✓ {{ b }}</text>
				</view>

				<view class="cta" :class="{ busy: buying }" @click="buySelected">
					<text>{{ buying ? 'Purchasing…' : ('Continue · ' + selectedPrice) }}</text>
				</view>
			</template>

			<view class="close-link" @click="close"><text>Not now</text></view>
		</view>
	</view>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { apiProducts, apiPurchase } from '@/api/vip.js'
import { track, trackClick } from '@/utils/analytics.js'
import {APP_NAME_DISPLAY} from '@/config/config.js'
import { getProductProfile, tierDisplayName, superLikeLabel, boostLabel } from '@/utils/productProfile.js'
import { isIapMock } from '@/utils/capabilities.js'

const showMockHint = computed(() => isIapMock())

const props = defineProps({
	show: Boolean,
	reason: { type: String, default: '' }
})
const emit = defineEmits(['update:show', 'purchased'])

const products = ref([])
const buying = ref(false)
const tier = ref('gold')
const period = ref(1)
const displayTiers = ref(getProductProfile().display_tiers || {})
const productMeta = ref({})

const tiers = computed(() => {
	const map = (displayTiers.value || {})
	return [
		{ id: 'plus', label: map.plus || 'Plus' },
		{ id: 'gold', label: map.gold || 'Gold' },
		{ id: 'platinum', label: map.platinum || 'Platinum' },
	]
})
const periods = [
	{ months: 1 },
	{ months: 6 },
	{ months: 12 }
]

const BENEFITS = {
	plus: ['Unlimited likes', 'Rewind last swipe', '1 free Boost / month', 'Passport travel mode'],
	gold: ['See who likes you', 'Advanced filters', '5 Super Likes / month', 'Everything in Plus'],
	platinum: ['Priority likes', 'Say Hi before match', 'Message before matching', 'Everything in Gold']
}

const FALLBACK = {
	plus_1m: { price: '9.99', currency: 'USD', title: 'Plus 1 Month', sku_type: 'subscription', tier: 'plus' },
	plus_6m: { price: '44.99', currency: 'USD', title: 'Plus 6 Months', sku_type: 'subscription', tier: 'plus' },
	plus_12m: { price: '71.99', currency: 'USD', title: 'Plus 12 Months', sku_type: 'subscription', tier: 'plus' },
	gold_1m: { price: '19.99', currency: 'USD', title: 'Gold 1 Month', sku_type: 'subscription', tier: 'gold' },
	gold_6m: { price: '89.99', currency: 'USD', title: 'Gold 6 Months', sku_type: 'subscription', tier: 'gold' },
	gold_12m: { price: '143.99', currency: 'USD', title: 'Gold 12 Months', sku_type: 'subscription', tier: 'gold' },
	platinum_1m: { price: '29.99', currency: 'USD', title: 'Platinum 1 Month', sku_type: 'subscription', tier: 'platinum' },
	platinum_6m: { price: '134.99', currency: 'USD', title: 'Platinum 6 Months', sku_type: 'subscription', tier: 'platinum' },
	platinum_12m: { price: '215.99', currency: 'USD', title: 'Platinum 12 Months', sku_type: 'subscription', tier: 'platinum' },
	super_like_3: { price: '4.99', currency: 'USD', title: 'Super Like x3', sku_type: 'consumable', tier: 'super_like' },
	super_like_5: { price: '7.99', currency: 'USD', title: 'Super Like x5', sku_type: 'consumable', tier: 'super_like' },
	super_like_15: { price: '19.99', currency: 'USD', title: 'Super Like x15', sku_type: 'consumable', tier: 'super_like' },
	boost_3: { price: '9.99', currency: 'USD', title: 'Boost x3', sku_type: 'consumable', tier: 'boost' },
	boost_5: { price: '14.99', currency: 'USD', title: 'Boost x5', sku_type: 'consumable', tier: 'boost' },
	boost_10: { price: '24.99', currency: 'USD', title: 'Boost x10', sku_type: 'consumable', tier: 'boost' },
	rewind_3: { price: '3.99', currency: 'USD', title: 'Rewind x3', sku_type: 'consumable', tier: 'rewind' },
	rewind_5: { price: '5.99', currency: 'USD', title: 'Rewind x5', sku_type: 'consumable', tier: 'rewind' },
	rewind_15: { price: '14.99', currency: 'USD', title: 'Rewind x15', sku_type: 'consumable', tier: 'rewind' },
	likes_unlock_1: { price: '1.99', currency: 'USD', title: 'Likes Unlock x1', sku_type: 'consumable', tier: 'likes_unlock' },
	likes_unlock_5: { price: '7.99', currency: 'USD', title: 'Likes Unlock x5', sku_type: 'consumable', tier: 'likes_unlock' },
}

const isItemShop = computed(() => ['need_super_like', 'need_boost', 'need_shop', 'need_rewind', 'need_likes_unlock'].includes(props.reason))

const reasonText = computed(() => {
	const sl = superLikeLabel()
	const bl = boostLabel()
	const map = {
		daily_like_limit: 'Out of likes today. Upgrade to continue.',
		need_super_like: `Get more ${sl}s.`,
		need_plus: `${tierDisplayName('plus')} unlocks unlimited rewind, passport & invisible mode.`,
		need_boost: `Get ${bl}s to be seen more.`,
		need_rewind: 'Get Rewind packs — or Plus for unlimited.',
		need_likes_unlock: 'Unlock individual likes, or get Gold to see everyone.',
		need_shop: 'Pick a pack to continue.',
		need_vip: `Unlock ${APP_NAME_DISPLAY} premium features.`,
		need_gold: `${tierDisplayName('gold')} lets you see who likes you.`,
		need_platinum: `${tierDisplayName('platinum')} unlocks Say Hi & priority likes.`
	}
	return map[props.reason] || `Unlock ${APP_NAME_DISPLAY} premium features.`
})

const benefits = computed(() => BENEFITS[tier.value] || BENEFITS.gold)

const catalog = computed(() => {
	const list = products.value || []
	const byId = {}
	Object.keys(FALLBACK).forEach((k) => {
		byId[k] = { product_id: k, ...FALLBACK[k], price_string: `${FALLBACK[k].currency} ${FALLBACK[k].price}` }
	})
	list.forEach((p) => {
		byId[p.product_id] = { ...byId[p.product_id], ...p }
	})
	return byId
})

const shopProducts = computed(() => {
	const all = Object.values(catalog.value)
	if (props.reason === 'need_super_like') {
		return all.filter((p) => /super/i.test(p.product_id) || p.tier === 'super_like')
	}
	if (props.reason === 'need_boost') {
		return all.filter((p) => /boost/i.test(p.product_id) || p.tier === 'boost')
	}
	if (props.reason === 'need_rewind') {
		return all.filter((p) => /rewind/i.test(p.product_id) || p.tier === 'rewind')
	}
	if (props.reason === 'need_likes_unlock') {
		return all.filter((p) => /likes_unlock/i.test(p.product_id) || p.tier === 'likes_unlock')
	}
	return all.filter((p) => p.sku_type === 'consumable' || /super|boost|rewind|likes_unlock/i.test(p.product_id))
})

const selectedProductId = computed(() => `${tier.value}_${period.value}m`)

const selectedPrice = computed(() => {
	const p = catalog.value[selectedProductId.value]
	return p ? priceLabel(p) : ''
})

watch(() => props.show, async (v) => {
	if (!v) return
	buying.value = false
	if (props.reason === 'need_plus') tier.value = 'plus'
	else if (props.reason === 'need_platinum') tier.value = 'platinum'
	else tier.value = 'gold'
	period.value = 1
	track('paywall_open', { reason: props.reason || 'need_vip' })
	try {
		const res = await apiProducts()
		products.value = (res.results && res.results.list) || []
		displayTiers.value = (res.results && res.results.display_tiers) || getProductProfile().display_tiers || {}
		productMeta.value = (res.results && res.results.product_profile) || {}
	} catch (e) {
		products.value = []
		displayTiers.value = getProductProfile().display_tiers || {}
	}
})

function priceLabel(p) {
	if (!p) return ''
	if (p.price_string) return p.price_string
	return `${p.currency || 'USD'} ${p.price || ''}`
}

function periodPrice(months) {
	const p = catalog.value[`${tier.value}_${months}m`]
	return p ? priceLabel(p) : '—'
}

function selectTier(id) {
	trackClick('vip_tier')
	tier.value = id
}

function selectPeriod(months) {
	trackClick('vip_period')
	period.value = months
}

function close() {
	emit('update:show', false)
}

async function buy(productId) {
	if (buying.value || !productId) return
	trackClick('vip_buy')
	buying.value = true
	try {
		await apiPurchase(productId)
		track('purchase', { product_id: productId, reason: props.reason || '' })
		uni.showToast({ title: 'Purchased', icon: 'none' })
		emit('purchased')
		close()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || 'Purchase failed', icon: 'none' })
	}
	buying.value = false
}

function buySelected() {
	buy(selectedProductId.value)
}
</script>

<style scoped>
.sheet-mask {
	position: fixed;
	left: 0; right: 0; top: 0; bottom: 0;
	background: rgba(0,0,0,0.55);
	z-index: 1000;
	display: flex;
	align-items: flex-end;
}
.sheet {
	width: 100%;
	background: #FFFFFF;
	border-radius: 32rpx 32rpx 0 0;
	padding: 40rpx 32rpx calc(env(safe-area-inset-bottom) + 40rpx);
	max-height: 88vh;
	overflow-y: auto;
}
.title {
	display: block;
	font-size: 40rpx;
	font-weight: 700;
	color: #111;
	margin-bottom: 12rpx;
}
.spark-serif { font-family: 'Playfair Display', 'Times New Roman', serif; }
.sub {
	display: block;
	color: #666;
	font-size: 26rpx;
	margin-bottom: 28rpx;
}
.tiers {
	display: flex;
	flex-direction: row;
	margin-bottom: 20rpx;
}
.tier {
	flex: 1;
	position: relative;
	background: #F3F0F7;
	border-radius: 16rpx;
	padding: 22rpx 8rpx;
	text-align: center;
	margin-right: 12rpx;
	border: 2rpx solid transparent;
}
.tier:last-child { margin-right: 0; }
.tier.on {
	border-color: #FD267A;
	background: rgba(253,38,122,0.1);
}
.tier.featured.on { box-shadow: 0 0 0 1px rgba(253,38,122,0.25); }
.tier-name { color: #111; font-size: 26rpx; font-weight: 600; }
.badge {
	position: absolute;
	top: -14rpx; left: 50%; transform: translateX(-50%);
	background: #FF4B55; color: #fff; font-size: 18rpx;
	padding: 4rpx 12rpx; border-radius: 999rpx; white-space: nowrap;
}
.periods {
	display: flex;
	flex-direction: row;
	margin-bottom: 24rpx;
}
.period {
	flex: 1;
	background: #F8F8F8;
	border-radius: 16rpx;
	padding: 20rpx 8rpx;
	text-align: center;
	margin-right: 12rpx;
	border: 2rpx solid transparent;
}
.period:last-child { margin-right: 0; }
.period.on { border-color: #FD267A; background: rgba(253,38,122,0.08); }
.period-m { display:block; color:#111; font-size:26rpx; font-weight:600; margin-bottom:6rpx; }
.period-p { display:block; color:#FD267A; font-size:22rpx; }
.benefits { margin-bottom: 28rpx; }
.benefit {
	display: block;
	color: #222;
	font-size: 26rpx;
	margin-bottom: 12rpx;
}
.cta {
	background: #FF4B55;
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
	margin-bottom: 8rpx;
}
.cta.busy { opacity: 0.7; }
.cta text { color: #fff; font-size: 30rpx; font-weight: 700; }
.sku {
	background: #F3F0F7;
	border-radius: 20rpx;
	padding: 28rpx;
	margin-bottom: 16rpx;
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: center;
	border: 1px solid rgba(0,0,0,0.04);
}
.sku-title { display:block; color: #111; font-size: 28rpx; }
.sku-hint { display:block; color:#666; font-size:20rpx; margin-top:6rpx; }
.sku-price { color: #FD267A; font-size: 28rpx; font-weight: 600; }
.empty { padding: 24rpx; text-align: center; }
.empty text { color: #666; }
.close-link {
	text-align: center;
	padding: 20rpx;
}
.close-link text { color: #999; }
</style>
