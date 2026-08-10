# 功能清单 · APP「SPARK」

> 源码目录：`frontend/mobile_spark`  
> App ID：`spark_main` · Package：`spark-mobile` · Manifest：`Spark / __UNI__SPARK001`  
> 更新依据：页面路由、主流程页面与产品配置（`product_profile`）

---

## 1. 产品定位

| 项 | 说明 |
|---|---|
| 显示名 | SPARK |
| 定位 | 标准国际约会 App：匹配后随时互聊 |
| 标语 | 「Match. Chat. Date.」 |
| 消息规则 | `messaging_mode: any`（无 QA 门控 / 无女性先开口强制） |
| 支付渠道 | IAP（Apple / Google） |
| VIP 文案 | Plus / Gold / Platinum |
| 主题色 | `#FF4458` |

---

## 2. TabBar 结构

| Tab | 页面 | 说明 |
|---|---|---|
| Discover | `pages/discover/index` | For You / Top Picks / Explore |
| Likes | `pages/likes/index` | Likes You / Sent |
| Chat | `pages/chat/index` | New Matches + Messages |
| Me | `pages/me/index` | 个人中心与订阅管理 |

---

## 3. 认证与引导

| 功能 | 页面 / 入口 | 说明 |
|---|---|---|
| 欢迎页 | `pages/auth/welcome` | Create account / Sign in；**Google / Apple / Phone**（无微信欢迎入口） |
| 登录 / 注册 / 忘记密码 / 手机号 | `pages/auth/*` | 标准账号流 |
| Onboarding | `pages/auth/onboarding` | 基本信息 → 照片 → 简介 → prompts → 兴趣等 |

---

## 4. 发现（Discover）

| 功能点 | 说明 |
|---|---|
| For You | 主滑卡推荐流 |
| Top Picks | 今日精选卡片网格 + 刷新倒计时 |
| Explore | 附近网格 + 分类（如 dating） |
| Dock | Rewind / Nope / Super Like / Like / Boost |
| Boost | 进行中 banner + **Boost report** |
| Passport | 旅行护照，切换发现城市 |
| Filter | 发现筛选 |
| MatchModal | 配对成功弹窗 |
| ComplimentSheet | 能力取决于 bootstrap 开关 |
| 日配额 | 默认无硬帽（`daily_feed_cap` 通常关闭） |

---

## 5. 喜欢（Likes）

| 功能点 | 说明 |
|---|---|
| Likes You / Sent | 收到的喜欢 / 发出的喜欢 |
| 筛选 chips | All / Nearby / Common / New / Super |
| Like all | 批量喜欢 |
| Say Hi | Platinum 打招呼能力 |
| 解锁 | 单人解锁 / 模糊锁 |
| Sent 列表 | 行式布局；独立分包 `pagesA/likes/sent` |

---

## 6. 消息（Chat）

| 功能点 | 说明 |
|---|---|
| New Matches | 新配对横滑 |
| Messages | 会话列表 + 搜索 |
| Your move / 未读 | 状态提示 |
| 倒计时 UI | 代码保留 women_first 相关 UI，主规则为 `any` |
| 聊天室 | 文字 / 图 / GIF / 语音 + 翻译 + 视频通话 |
| 无 QA 环 | 与「她说」不同，无问答门控流程 |

---

## 7. 我的（Me）

| 功能点 | 说明 |
|---|---|
| VIP 管理 | 订阅管理、加购 |
| 库存 | Super Like / Boost / Rewind / **Unlocks** |
| Features | Swipe Night / Matchmaker / Campus / Select / Face to Face |
| Boost report | 曝光报告入口 |
| 编辑 / 预览 | 资料编辑与预览 |
| 分享 / 邀请 | 邀请归因 |
| 设置 / 协议 | 账号、通知、法律 |

---

## 8. 分包 `pagesA` 功能

| 页面 | 功能 |
|---|---|
| `profile/detail` | 他人资料详情；举报 / 拉黑 / 喜欢 |
| `chat/room` | 聊天室（图文语音 GIF、翻译、通话入口） |
| `chat/call` | 视频通话 |
| `likes/sent` | 发出的喜欢独立页 |
| `me/edit` | 照片、基本信息、prompts、兴趣、生活方式 |
| `me/preview` | 资料预览 |
| `me/settings` | 语言（en/zh/ja/ko/es/pt）、外观、Invisible、**Hide age**、**Show in discovery**、**Global mode (Plus)**、Google 绑定、恢复购买、Legal |
| `me/notifications` | 推送偏好 |
| `me/verify` | Photo / Persona 真人认证 |
| `me/legal` | 协议、导出数据、删号 |
| `me/safety` | Safety toolkit |
| `features/swipe-night` | 夜间限时互选 |
| `features/matchmaker` | 好友牵线 |
| `features/campus` | 校园绑定与 feed |
| `features/select` | Select 精选池 |
| `features/face-to-face` | 面对面附近匹配 |

---

## 9. VIP / 支付 / 道具

| 能力 | 说明 |
|---|---|
| VipSheet | Plus / Gold / Platinum + 道具 |
| 支付 | Apple IAP / Google Play；支持恢复购买 |
| 道具 | Super Like、Boost、Rewind、Unlocks |
| 权益示例 | 隐身、Global mode、喜欢解锁、Say Hi 等 |

---

## 10. 安全与合规

- Safety toolkit（紧急联系人、约会分享、屏蔽词等）
- Photo verify / Persona
- Blocked users
- Invisible mode
- 数据导出 / 账号注销
- Legal（协议与社区准则）

---

## 11. 相对其他 APP 的差异要点

- 标准 **任意互聊**，无 QA / 女性先开口强制
- 发现含 **Top Picks** 与 **Boost report**
- 喜欢页能力更全：**筛选 / Like all / Say Hi / Unlocks**
- **纯 IAP**，无国内微信支付宝主路径
- VIP 英文档位 Plus / Gold / Platinum
