/**
 * SPARK API facade — re-exports domain modules.
 * Prefer importing from `@/api/<domain>.js` in new code.
 */
export {
	apiBootstrap,
	apiRegister,
	apiLogin,
	apiGoogleLogin,
	apiMe,
	apiOnboarding,
	apiLogout,
	apiHeartbeat,
	apiBadges
} from './auth.js'

export {
	apiFeed,
	apiRecommendFeed,
	apiSwipe,
	apiRewind
} from './recommend.js'

export {
	apiLikesReceived,
	apiLikesSent,
	apiSayHi,
	apiMatches,
	apiUnmatch
} from './likes.js'

export {
	apiProfileMe,
	apiProfileUpdate,
	apiProfileDetail,
	apiFiltersGet,
	apiFiltersSave,
	apiBlock,
	apiBlocks,
	apiUnblock,
	apiReport,
	apiReorderPhotos
} from './profile.js'

export {
	apiConversations,
	apiMessages,
	apiSendMessage,
	apiTranslate
} from './chat.js'

export {
	apiProducts,
	apiEntitlements,
	apiPurchase,
	apiRestorePurchases,
	apiBoost
} from './vip.js'

export { apiEventsBatch } from './events.js'
