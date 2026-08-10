<template>
	<view class="sheet-mask" v-if="show" @click="close">
		<view class="sheet" @click.stop>
			<template v-if="isItemShop">
				<text class="title">道具商城</text>
				<text class="sub">{{ reasonText }}</text>
				<view
					v-for="p in shopProducts"
					:key="p.product_id"
					class="sku"
					@click="buy(p.product_id)"
				>
					<view>
						<text class="sku-title">{{ p.title || p.product_id }}</text>
						<text class="sku-hint">购买后立即到账</text>
					</view>
					<text class="sku-price">{{ priceLabel(p) }}</text>
				</view>
				<view v-if="!shopProducts.length" class="empty"><text>暂无道具包</text></view>
			</template>

			<template v-else>
				<text class="title display-font">开通会员</text>
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
						<text v-if="t.id === 'gold'" class="badge">热门</text>
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
						<text class="period-m">{{ p.months }} 个月</text>
						<text class="period-p">{{ periodPrice(p.months) }}</text>
					</view>
				</view>

				<view class="benefits">
					<text v-for="(b, i) in benefits" :key="i" class="benefit">✓ {{ b }}</text>
				</view>

				<view class="cta" :class="{ busy: buying }" @click="buySelected">
					<text>{{ buying ? '购买中…' : ('继续 · ' + selectedPrice) }}</text>
				</view>
				<view class="cn-pay" v-if="showCnPay">
					<view class="cn-btn wechat" :class="{ busy: buying }" @click="cnPay('wechat')">
						<text>微信支付</text>
					</view>
					<view class="cn-btn alipay" :class="{ busy: buying }" @click="cnPay('alipay')">
						<text>支付宝</text>
					</view>
				</view>
			</template>

			<view class="close-link" @click="close"><text>暂不开通</text></view>
		</view>
	</view>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { apiProducts, apiPurchase, apiVipCnPay } from '@/api/vip.js'
import { track, trackClick } from '@/utils/analytics.js'
import { APP_NAME_DISPLAY, APP_ID } from '@/config/config.js'
import { isIapMock } from '@/utils/capabilities.js'
import { getProductProfile, tierDisplayName, superLikeLabel, boostLabel } from '@/utils/productProfile.js'

const showMockHint = !!isIapMock()

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
		{ id: 'plus', label: map.plus || '会员' },
		{ id: 'gold', label: map.gold || '高级会员' },
		{ id: 'platinum', label: map.platinum || '至尊会员' },
	]
})
const periods = [
	{ months: 1 },
	{ months: 6 },
	{ months: 12 }
]

const BENEFITS = {
	plus: ['无限喜欢', '反悔上一张', '每月曝光', '旅行模式'],
	gold: ['查看谁喜欢你', '高级筛选', '每月心动次数', '包含会员权益'],
	platinum: ['优先推荐', '曝光优先', '包含高级会员权益', '问答开聊优先']
}

const FALLBACK = {
	plus_1m: { price: '9.99', currency: 'USD', title: '会员 1个月', sku_type: 'subscription', tier: 'plus' },
	plus_6m: { price: '44.99', currency: 'USD', title: '会员 6个月', sku_type: 'subscription', tier: 'plus' },
	plus_12m: { price: '71.99', currency: 'USD', title: '会员 12个月', sku_type: 'subscription', tier: 'plus' },
	gold_1m: { price: '19.99', currency: 'USD', title: '高级会员 1个月', sku_type: 'subscription', tier: 'gold' },
	gold_6m: { price: '89.99', currency: 'USD', title: '高级会员 6个月', sku_type: 'subscription', tier: 'gold' },
	gold_12m: { price: '143.99', currency: 'USD', title: '高级会员 12个月', sku_type: 'subscription', tier: 'gold' },
	platinum_1m: { price: '29.99', currency: 'USD', title: '至尊会员 1个月', sku_type: 'subscription', tier: 'platinum' },
	platinum_6m: { price: '134.99', currency: 'USD', title: '至尊会员 6个月', sku_type: 'subscription', tier: 'platinum' },
	platinum_12m: { price: '215.99', currency: 'USD', title: '至尊会员 12个月', sku_type: 'subscription', tier: 'platinum' },
	super_like_3: { price: '4.99', currency: 'USD', title: '心动 x3', sku_type: 'consumable', tier: 'super_like' },
	super_like_5: { price: '7.99', currency: 'USD', title: '心动 x5', sku_type: 'consumable', tier: 'super_like' },
	super_like_15: { price: '19.99', currency: 'USD', title: '心动 x15', sku_type: 'consumable', tier: 'super_like' },
	boost_3: { price: '9.99', currency: 'USD', title: '曝光 x3', sku_type: 'consumable', tier: 'boost' },
	boost_5: { price: '14.99', currency: 'USD', title: '曝光 x5', sku_type: 'consumable', tier: 'boost' },
	boost_10: { price: '24.99', currency: 'USD', title: '曝光 x10', sku_type: 'consumable', tier: 'boost' }
}

const isItemShop = computed(() => ['need_super_like', 'need_boost', 'need_shop'].includes(props.reason))

const showCnPay = computed(() => {
	const boot = uni.getStorageSync('bootstrap') || {}
	const channel = String(boot.pay_channel || boot.payment_channel || '').toLowerCase()
	if (channel === 'wechat' || channel === 'alipay' || channel === 'cn') return true
	const appId = String(APP_ID || '')
	return appId === 'matchup_main'
})

const FALLBACK_CNY = {
	plus_1m: { price: '28', currency: 'CNY' },
	plus_6m: { price: '128', currency: 'CNY' },
	plus_12m: { price: '198', currency: 'CNY' },
	gold_1m: { price: '48', currency: 'CNY' },
	gold_6m: { price: '228', currency: 'CNY' },
	gold_12m: { price: '348', currency: 'CNY' },
	platinum_1m: { price: '68', currency: 'CNY' },
	platinum_6m: { price: '328', currency: 'CNY' },
	platinum_12m: { price: '498', currency: 'CNY' },
}

const reasonText = computed(() => {
	const sl = superLikeLabel()
	const bl = boostLabel()
	const map = {
		daily_like_limit: '今日喜欢次数已用完，开通会员继续滑',
		need_super_like: `购买更多${sl}`,
		need_plus: `${tierDisplayName('plus')}可解锁反悔、旅行与隐身`,
		need_boost: `购买${bl}，让更多人看到你`,
		need_shop: '选择道具包继续',
		need_vip: `开通${APP_NAME_DISPLAY}会员权益`,
		need_gold: `${tierDisplayName('gold')}可查看谁喜欢了你`,
		need_platinum: `${tierDisplayName('platinum')}提供优先曝光`,
		need_feed: '今日推荐已用完，开通会员获取更多推荐',
		tomorrow: '明天会刷新额度，会员可立即加量',
	}
	return map[props.reason] || `开通${APP_NAME_DISPLAY}会员权益`
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
	return all.filter((p) => p.sku_type === 'consumable' || /super|boost/i.test(p.product_id))
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
	if (showCnPay.value) {
		const cny = FALLBACK_CNY[p.product_id]
		if (p.currency === 'CNY' || p.price_cny) {
			return `¥${p.price_cny || p.price}`
		}
		if (cny) return `¥${cny.price}`
	}
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

async function cnPay(channel) {
	const productId = selectedProductId.value
	if (buying.value || !productId) return
	trackClick('vip_buy')
	buying.value = true
	try {
		await apiVipCnPay({ product_id: productId, channel })
		track('purchase_cn', { product_id: productId, channel, reason: props.reason || '' })
		uni.showToast({ title: '支付成功', icon: 'none' })
		emit('purchased')
		close()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '支付暂不可用（演示）', icon: 'none' })
	}
	buying.value = false
}

async function buy(productId) {
	if (buying.value || !productId) return
	trackClick('vip_buy')
	buying.value = true
	try {
		await apiPurchase(productId)
		track('purchase', { product_id: productId, reason: props.reason || '' })
		uni.showToast({ title: '购买成功', icon: 'none' })
		emit('purchased')
		close()
	} catch (e) {
		uni.showToast({ title: (e && e.message) || '购买失败', icon: 'none' })
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
	background: rgba(0,0,0,0.4);
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
	font-weight: 800;
	color: #222;
	margin-bottom: 12rpx;
}
.display-font { font-family: 'PingFang SC', 'Hiragino Sans GB', sans-serif; }
.sub {
	display: block;
	color: #888;
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
	background: #FFF7FA;
	border-radius: 16rpx;
	padding: 22rpx 8rpx;
	text-align: center;
	margin-right: 12rpx;
	border: 2rpx solid transparent;
}
.tier:last-child { margin-right: 0; }
.tier.on {
	border-color: #FF6B9A;
	background: rgba(255,107,154,0.12);
}
.tier.featured.on { box-shadow: 0 0 0 1px rgba(255,107,154,0.35); }
.tier-name { color: #222; font-size: 26rpx; font-weight: 700; }
.badge {
	position: absolute;
	top: -14rpx; left: 50%; transform: translateX(-50%);
	background: #FF6B9A; color: #fff; font-size: 18rpx;
	padding: 4rpx 12rpx; border-radius: 999rpx; white-space: nowrap;
}
.periods {
	display: flex;
	flex-direction: row;
	margin-bottom: 24rpx;
}
.period {
	flex: 1;
	background: #FFF7FA;
	border-radius: 16rpx;
	padding: 20rpx 8rpx;
	text-align: center;
	margin-right: 12rpx;
	border: 2rpx solid transparent;
}
.period:last-child { margin-right: 0; }
.period.on { border-color: #FF6B9A; background: #FFE8F0; }
.period-m { display:block; color:#222; font-size:26rpx; font-weight:700; margin-bottom:6rpx; }
.period-p { display:block; color:#FF6B9A; font-size:22rpx; }
.benefits { margin-bottom: 28rpx; }
.benefit {
	display: block;
	color: #444;
	font-size: 26rpx;
	margin-bottom: 12rpx;
}
.cta {
	background: linear-gradient(90deg, #FF6B9A, #FF8FB3);
	border-radius: 999rpx;
	padding: 28rpx;
	text-align: center;
	margin-bottom: 8rpx;
}
.cta.busy { opacity: 0.7; }
.cta text { color: #fff; font-size: 30rpx; font-weight: 800; }
.sku {
	background: #FFF7FA;
	border-radius: 20rpx;
	padding: 28rpx;
	margin-bottom: 16rpx;
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: center;
	border: 1px solid rgba(255,107,154,0.2);
}
.sku-title { display:block; color: #222; font-size: 28rpx; }
.sku-hint { display:block; color:#888; font-size:20rpx; margin-top:6rpx; }
.sku-price { color: #FF6B9A; font-size: 28rpx; font-weight: 700; }
.empty { padding: 24rpx; text-align: center; }
.empty text { color: #888; }
.close-link {
	text-align: center;
	padding: 20rpx;
}
.close-link text { color: #888; }
.cn-pay {
	display:flex; flex-direction:row; margin: 12rpx 0 8rpx;
}
.cn-btn {
	flex:1; border-radius:999rpx; padding: 24rpx; text-align:center; margin-right: 12rpx;
}
.cn-btn:last-child { margin-right: 0; }
.cn-btn.wechat { background:#07C160; }
.cn-btn.alipay { background:#1677FF; }
.cn-btn text { color:#fff; font-weight:700; font-size:26rpx; }
.cn-btn.busy { opacity: 0.7; }
</style>
