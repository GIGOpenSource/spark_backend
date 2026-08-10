# 功能清单 · APP「bee」(Swipe)

> 源码目录：`frontend/mobile_swipe`  
> App ID：`swipe_main` · Package：`bee-mobile` · Manifest：`bee / __UNI__SWIPE001`  
> 更新依据：页面路由、主流程页面与产品配置（`product_profile`）

---

## 1. 产品定位

| 项 | 说明 |
|---|---|
| 显示名 | bee |
| 定位 | 女性先开口 + Compliment 文化；多交友模式 |
| 标语 | 「Make the first move」/「主动一点，先开口」 |
| 消息规则 | `women_first`：女性先开口；匹配窗口约 **24h**，支持 **Extend** |
| 支付渠道 | IAP（Apple / Google） |
| VIP 文案 | Premium / Premium+ / Premium+ Spotlight |
| Boost 文案 | **Spotlight** |

---

## 2. TabBar 结构

| Tab | 页面 | 说明 |
|---|---|---|
| People | `pages/discover/index` | 发现 / 资料卡滑动 |
| Beeline | `pages/likes/index` | 喜欢你的人（含 Compliment） |
| Chats | `pages/chat/index` | 聊天与开聊倒计时 |
| Profile | `pages/me/index` | 个人主页与增值 |

---

## 3. 认证与引导

| 功能 | 页面 / 入口 | 说明 |
|---|---|---|
| 欢迎页 | `pages/auth/welcome` | bee 品牌；Create / Sign in；Apple / Phone / Google |
| 登录 / 注册 / 忘记密码 / 手机号 | `pages/auth/*` | 标准账号流 |
| Onboarding | `pages/auth/onboarding` | 资料引导；含 prompts / Opening Moves 等能力位 |

---

## 4. 发现（People）— 差异最大

| 功能点 | 说明 |
|---|---|
| Dating modes | **Date / BFF / Bizz**（约会 / 交友 / 商务） |
| Best Bees | 精选条 |
| 资料卡形态 | **纵向可滚动资料卡**（非纯叠卡） |
| 卡片区块 | About、Prompts、Opening Moves、Voice / Video prompt、Badges、Interests、Looking for |
| Compliment | 各区块可直接夸夸（照片 / 简介 / prompt / 语音 / 视频） |
| Dock | Rewind / Nope / Compliment / Like / Spotlight |
| Waveform | 语音波形展示 |
| Passport / Filter | 旅行护照与筛选 |
| MatchModal / ComplimentSheet | 配对与夸夸弹层 |
| ExpireRing | 匹配时效相关 UI |

---

## 5. Beeline（喜欢）

| 功能点 | 说明 |
|---|---|
| 筛选 | All / Recently active / **Compliments** / Verified / Nearby / More(Filter) |
| Compliment 高亮 | 夸夸文案突出展示；卡片内 Compliment CTA |
| Sent | 发出的喜欢；独立 `pagesA/likes/sent` |
| 解锁 / 模糊 | 会员解锁逻辑同系产品 |

---

## 6. Chats（消息）

| 功能点 | 说明 |
|---|---|
| 24h 开聊倒计时 | Expire / Expiry 环 |
| 空态 | 「Make the first move」引导女性先开口 |
| 聊天室 | 文字 / 图 / 语音 / GIF + 翻译 + 视频通话 |
| **Extend** | 延长匹配窗口 |
| New Matches / 搜索 | 新配对与会话搜索 |

---

## 7. Profile（我的）

| 功能点 | 说明 |
|---|---|
| 照片网格 | **6 格照片** hero |
| 库存 | Compliment / Spotlight / **Extends**；可立即 Spotlight |
| 增值位 | **Hive / Connect / Date Night / Rematch**（产品入口文案） |
| Features | Swipe Night / Matchmaker / Campus / Select / Face to Face |
| Verify / Safety | 真人认证与安全中心 |
| 设置 / 协议 / 邀请 | 同系能力 |

---

## 8. 资料编辑增强

| 能力 | 说明 |
|---|---|
| Prompts | 灵魂问答 |
| Opening Moves | 开场动作 / 开场白素材 |
| Voice & Video prompts | 语音 / 视频 prompt |
| Badges | 徽章体系（`BADGE_CATALOG`） |

---

## 9. 分包 `pagesA` 功能

| 页面 | 功能 |
|---|---|
| `profile/detail` | 他人资料；举报 / 拉黑 / 喜欢 / Compliment |
| `chat/room` | 聊天室 + Extend |
| `chat/call` | 视频通话 |
| `likes/sent` | 发出的喜欢 |
| `me/edit` | 照片、基本信息、prompts、Opening Moves、语音视频、兴趣等 |
| `me/preview` | 资料预览 |
| `me/settings` | 语言 / 外观 / Invisible（Premium）/ 发现相关开关 / 社交绑定 / 恢复购买 / Legal |
| `me/notifications` | 推送偏好 |
| `me/verify` | 真人认证 |
| `me/legal` | 协议、导出、删号 |
| `me/safety` | 安全工具箱 |
| `features/*` | Swipe Night / Matchmaker / Campus / Select / Face to Face |

---

## 10. VIP / 支付 / 道具

| 能力 | 说明 |
|---|---|
| VipSheet | Premium 三档 + 道具 |
| 支付 | IAP + restore |
| 道具 / 权益 | Compliment、Spotlight、Extends、Rewind 等 |
| Boost 命名 | 统一为 Spotlight |

---

## 11. 安全与合规

- Safety toolkit
- Verify
- Blocked users
- Invisible（标 Premium）
- 数据导出 / 删号
- Legal

---

## 12. 相对其他 APP 的差异要点

- **women_first** + **24h** + **Extend**
- **Compliment** 为核心互动（非仅 Super Like）
- 发现支持 **Date / BFF / Bizz** 多模式与纵向资料卡
- 资料含 Opening Moves、Voice/Video prompt、Badges
- VIP / Boost 文案为 Premium / Spotlight 体系
- 独有增值入口文案：Hive / Connect / Date Night / Rematch
