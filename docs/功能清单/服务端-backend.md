# 功能清单 · 服务端（Django Backend）

> 源码目录：`backend/`  
> 基础路径：`/api/`  
> 认证：`Authorization: Token <token>`（Redis + AES，非 JWT）  
> 多 APP 隔离：`app_id`（如 `spark_main` / `swipe_main` / `matchup_main`）；模块开关见 `tools/app_modules.py`  
> 更新依据：`Apps/urls.py`、各 ViewSet、`models/`、相关 tools

> **说明**：仓库内 `API.md` 仍含旧脚手架（BuildMart）接口描述，**当前产品以本清单与源码为准**。

---

## 1. 架构概览

| 项 | 内容 |
|---|---|
| 根路由 | `uivsbe_backend/urls.py` → `/api/`、`/api/docs/`、`/api/upload/` |
| 业务路由 | `Apps/urls.py` |
| WebSocket | `ws/chat/<cid>/`、`ws/group/<rid>/`、`ws/match/<mid>/qa/` |
| 文档 | DRF Spectacular `/api/docs/` |

### 已注册业务模块

`bootstrap` · `auth` · `recommend` · `likes` · `profile` · `match` · `chat` · `vip` · `translate` · `maps` · `events` · `push` · `verify` · `safety` · `swipe-night` · `matchmaker` · `campus` · `select` · `face-to-face` · `quick-match` · `group` · `community` · `moments` · `videos` · `spark-admin` · `users` · `admin` · `example`

---

## 2. 认证与账号

**View**：`Apps/views/auth/view.py` · `AuthViewSet`

| 能力 | 主要端点 |
|---|---|
| 邮箱注册 / 登录 | `POST /api/auth/register/` · `/login/` |
| 当前用户 | `GET /api/auth/me/` |
| Onboarding | `POST /api/auth/onboarding/` |
| 登出 | `POST /api/auth/logout/` |
| Google | `/google/` · `/google/bind/` · `/google/unbind/` |
| Apple | `/apple/` · `/apple/bind/` · `/apple/unbind/` |
| 微信 | `/wechat/login/` · `/wechat/bind/` · `/wechat/unbind/` |
| Facebook | `/facebook/`（开发 stub） |
| 短信 OTP | `/sms/send/` · `/sms/verify/` |
| 社交 OAuth | `/oauth/{instagram\|spotify\|wechat\|douyin\|xiaohongshu}/start\|callback/` |
| 邀请归因 | `POST /api/auth/invite/track/` |
| 找回密码 | `/password/forgot/` · `/password/reset/` |
| 注销 / 导出 | `/account/delete/` · `/account/export/` |
| 心跳 / 角标 | `/heartbeat/` · `/badges/` |

脚手架遗留：`/api/users/*`、`/api/admin/register|login|logout|info/`、成员与角色管理。

**相关模型**：`User`、`PasswordResetToken`  
**工具**：`token_tools`、`google_oauth_service`、`apple_signin_service`、`sms_service`、`social_oauth_service`、`mail_service`

---

## 3. 启动配置与用户资料

| 能力 | 端点 |
|---|---|
| 启动配置 | `GET /api/bootstrap/config/`（模块开关、审核模式、地图、IAP/OAuth 能力） |
| 我的资料 | `GET /api/profile/me/` |
| 更新资料 | `PUT/PATCH /api/profile/me/update/` |
| 他人详情 / 预览 | `/profile/detail/` · `/preview/` |
| 照片 | `/photos/` · `/photos/smart/` · `/photos/reorder/` · `DELETE /photos/{id}/` |
| 发现筛选 | `GET/POST /api/profile/filters/` |
| 兴趣投票 | `POST /api/profile/interest-vote/` |
| 真人认证 | `/api/verify/start/` · `/status/` · `/sandbox/decide/` · `/webhook/` |

**相关模型**：`UserPhoto`、`UserFilter`、`VerifyInquiry`；画像字段含 MBTI、星座、lifestyle、interests 等。

---

## 4. 推荐 / 匹配 / 滑动

| 模块 | 能力 | 主要端点 |
|---|---|---|
| recommend | 推荐流、Like/Pass/Super、回撤 | `/feed/` · `/swipe/` · `/rewind/` |
| match | 匹配列表、开聊、延长、解除 | `/list/` · `/open-message/` · `/extend/` · `/unmatch/` |
| match QA | 「她说」问答门控 | `/qa/templates/` · `/qa/ask|answer|review/`；WS `ws/match/<id>/qa/` |
| swipe-night | 夜间互选 | `/current/` · `/candidates/` · `/pick/` · `/settle/` |
| matchmaker | 红娘邀请 | `/invite/` · `/inbox/` · `/respond/` |
| campus | 校园绑定与 feed | `/bind/` · `/verify-stub/` · `/feed/` |
| select | 精选队列 | `/apply/` · `/status/` · `/feed/` |
| face-to-face | 面对面附近匹配 | `/start/` · `/feed/` · `/stop/` |
| quick-match | 快速匹配排队 | `/enter/` · `/cancel/` · `/leave/` · `/status/` |

**相关模型**：`Swipe`、`Match`、`MatchQA`、`TopPicksSnapshot`、`FunnelPool`、`FunnelAbcRule`、`RobotRecommendList`、`UserRecommendStat`、`DiscoverParam`、`SwipeNight*`、`MatchmakerInvite`、`CampusProfile`、`SelectQueue`、`FaceToFaceSession`、`QmTicket`、`QmPair`

**工具**：`spark_helpers`、`qa_templates`、`robot_excel`

---

## 5. 点赞 / 互动

| 能力 | 端点 |
|---|---|
| 收到的 / 发出的赞 | `GET /api/likes/received/` · `/sent/` |
| 解锁 | `POST /api/likes/unlock/` |
| Say Hi | `POST /api/likes/say-hi/` |
| Compliment | `POST /api/likes/compliment/` · `GET /compliments/` |

### 社交内容（同源模块）

| 模块 | 能力 |
|---|---|
| community | topics、posts CRUD、comments、like、upload |
| moments | feed / create / detail / comments / like / upload |
| videos | 短视频同构接口 |

**相关模型**：`Compliment`、`SayHi`、`LikeUnlock`、`Topic`、`Post*`、`PostComment`、`PostLike`

---

## 6. 聊天 / 消息

| 能力 | 端点 |
|---|---|
| 会话列表 | `GET /api/chat/conversations/` |
| 历史 / 发送 | `/conversations/{cid}/messages/` · `/send/` |
| GIF | `GET /api/chat/gifs/search/`（Tenor） |
| 音视频 | `POST /api/chat/call/token/` · `/call/hangup/`（Agora） |
| 媒体上传 | `POST /api/chat/upload/` |
| 实时聊天 | WS `ws/chat/<conversation_id>/` |
| 群聊 | `/api/group/rooms/` CRUD、invite/kick/leave、messages/send、upload；WS `ws/group/<rid>/` |
| 翻译 | `POST /api/translate/text/` |

**相关模型**：`Conversation`、`Message`、`ChatRoom*`  
**工具**：`agora_service`、`tenor_service`、`translate_service`

---

## 7. VIP / 支付 / 权益

| 能力 | 端点 |
|---|---|
| 商品 / 权益 | `GET /api/vip/products/` · `/entitlements/` |
| IAP 购买核验 | `POST /api/vip/purchase/` |
| Boost | `POST /api/vip/boost/` · `GET /boost/report/` |
| 恢复购买 | `POST /api/vip/restore/` |
| 商店 Webhook | `POST /api/vip/webhook/`（公开） |
| 国内支付 | `POST /api/vip/cn-pay/`（微信 / 支付宝，mock 友好） |

**VIP 档位**：`none` / `plus` / `gold` / `platinum`  
**权益账本示例**：super_like、boost、daily_like、rewind、daily_feed、likes_unlock、extend、rematch…

**相关模型**：`Order`、`Payment`、`SkuMap`、`EntitlementLedger`、`BoostSession`  
**工具**：`iap_service`、`firebase_mock`

---

## 8. 安全 / 举报 / 拉黑

| 能力 | 端点 |
|---|---|
| 拉黑 / 解除 / 列表 | `/api/profile/block/` · `/unblock/` · `/blocks/` |
| 举报 | `POST /api/profile/report/` |
| 紧急联系人 | `GET/PUT/PATCH /api/safety/emergency/` |
| 约会分享 | `POST /api/safety/share-date/`（+ SMS） |
| 个人屏蔽词 | `GET/PUT /api/safety/blocked-words/` |

**相关模型**：`Block`、`Report`、`EmergencyContact`、`DateShare`、`UserSafetyPref`、`WordFilter`、`DomainWhitelist`

---

## 9. 内容审核

| 能力 | 说明 |
|---|---|
| 照片审核状态 | `UserPhoto.audit_status`；管理端可审图 |
| Persona 真人核验 | `/api/verify/*` |
| 敏感词 / 域名白名单 | 运营 `/api/spark-admin/safety/` |
| 审核模式 | `ReviewMode`；bootstrap 下发；`/api/spark-admin/review-mode/` |
| 帖子审核 | Admin `/posts/` 状态管理 |

---

## 10. 通知 / 推送

| 能力 | 端点 |
|---|---|
| 注册设备 Token | `POST /api/push/token/` |
| 打开回执 | `POST /api/push/opened/` |
| 用户通知偏好 | `GET/PUT/PATCH /api/push/prefs/` |
| 系统推送配置 | Admin `/api/spark-admin/push-configs/` |

**事件类型示例**：new_like、new_match、new_message、silent_recall、qa_need_*  

**相关模型**：`SystemPushConfig`、`UserPushToken`、`UserPushLedger`、`UserSilentRecallState`、`UserNotificationPref`  
**工具**：`push_service`（UniPush / mock、静默时段、日上限）

---

## 11. 运营后台 API（服务端侧）

### A. Spark 运营 `/api/spark-admin/`

| 分组 | 能力 |
|---|---|
| 概览 | `dashboard` |
| 用户 | `users`、`users/detail`、`users/action`、Firebase 用户/订单/支付 |
| 漏斗 / 机器人 | `funnel`、`funnel-import`、`robot-recommend-lists`、`funnel-abc-rule`、`funnel-recompute`、`discover-params` |
| 聊天监管 | `chats`、`chats/messages` |
| 商业 | `skus`、`orders` |
| 广告 | `ad-links`、`google-ads/*`、`facebook-ads/*`、`ad-attributions/*` |
| 安全配置 | `safety` |
| 配置 | `app-config`、`product-profile`、`review-mode`、`country-config`、`app-modules`、`app-list` |
| 分析 | `events/dict`、`analytics/overview|events|funnel|stream` |
| 推送 | `push-configs` |
| Provider | `providers`、测试连通 |
| 社交运营 | `quick-match`、`groups`、`topics`、`posts` |

### B. 脚手架 Admin `/api/admin/`

登录、成员、角色权限等。

### C. 埋点客户端

`POST /api/events/batch/` · `/attribution/`

---

## 12. 其他能力

| 能力 | 说明 |
|---|---|
| 地图 | `GET /api/maps/geocode/` · `/regeo/` · `/provider/`（国内高德 / 海外 Google） |
| 通用上传 | `POST /api/upload/`（可 COS） |
| 定时维护 | `spark_maintenance`、`seed_spark` 等 management commands |
| i18n | `locale/` + 翻译工具 |

---

## 13. 核心数据域映射

| 领域 | 主要表 / 模型 |
|---|---|
| 账号画像 | `t_user`、`t_user_photo`、`t_user_filter` |
| 滑动匹配 | `t_swipe`、`t_match`、`t_match_qa`、`t_top_picks_snapshot` |
| 互动 | `t_compliment`、`t_say_hi`、`t_like_unlock` |
| 权益支付 | `t_entitlement_ledger`、`t_boost_session`、`t_order`、`t_payment`、`t_sku_map` |
| 安全 | `t_block`、`t_report`、`t_emergency_contact`、`t_date_share` |
| 特色玩法 | Swipe Night / Matchmaker / Campus / Select / FaceToFace / QuickMatch |
| 聊天社交 | `t_conversation`、`t_message`、`t_chat_room*`、`t_topic`、`t_post*` |
| 运营配置 | App、国家、漏斗、机器人、发现参数、审核模式、广告、词库、Provider |
| 推送分析 | 推送配置 / Token / Ledger、Event、VerifyInquiry |
