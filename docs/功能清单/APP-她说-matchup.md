# 功能清单 · APP(MatchUp)

> 源码目录：`frontend/mobile_matchup`  
> App ID：`matchup_main` · Package：`matchup-mobile` · Manifest：`MatchUp / __UNI__MATCH001`  
> 更新依据：页面路由、主流程页面与产品配置（`product_profile`）

---

## 1. 产品定位

| 项 | 说明 |
|---|---|
| 显示名 | Match Up |
| 定位 | 国内向约会 App：女问男答（`qa_gate`），审阅后再开聊 |
| 标语 | 「女问男答，审阅后再开聊」 |
| 消息规则 | `qa_gate`：配对后需问答门控通过才能正常聊天 |
| 支付渠道 | 国内（微信 / 支付宝，`pay_channel: cn`） |
| VIP 文案 | 会员 / 高级会员 / 至尊会员 |
| 主题 | 粉系 `#FF6B9A`，背景 `#FFF7FA` |

---

## 2. TabBar 结构

自定义 `SparkTabBar`：

| Tab | 页面 | 说明 |
|---|---|---|
| 发现 | `pages/discover/index` | 滑卡推荐 / 探索 |
| 喜欢 | `pages/likes/index` | 收到的喜欢 / 发出的喜欢 |
| 消息 | `pages/chat/index` | 新配对 + 会话列表 |
| 我 | `pages/me/index` | 个人中心与增值入口 |

---

## 3. 认证与引导

| 功能 | 页面 / 入口 | 说明 |
|---|---|---|
| 欢迎页 | `pages/auth/welcome` | 手机号 / Apple / **微信**登录；邮箱注册登录入口；用户协议 |
| 登录 | `pages/auth/login` | 账号密码登录 |
| 手机号登录 | `pages/auth/phone` | 短信 OTP |
| 注册 | `pages/auth/register` | 邮箱注册 |
| 忘记密码 | `pages/auth/forgot` | 找回密码 |
| Onboarding | `pages/auth/onboarding` | 约 5 步：基本信息 → 最多 6 张照片 → 简介 → 个性问答（最多 3）→ 兴趣等 |

---

## 4. 发现（核心滑卡）

| 功能点 | 说明 |
|---|---|
| 推荐模式 | 主滑卡推荐流 |
| 探索模式 | 附近网格，可按距离等排序 |
| 手势 | 左滑跳过、右滑喜欢、上滑 / 按钮「心动」（Super Like） |
| Dock | 跳过 / 心动 / 喜欢 |
| 曝光（Boost） | 提升曝光 |
| 旅行护照（Passport） | 切换发现城市 |
| 筛选（Filter） | 年龄、距离等发现筛选 |
| 每日推荐配额 | 默认约 21 人；VIP 加量（plus+5 / gold+10 / platinum+21） |
| HomeBanner | 运营位（官方 tips / 深链） |
| 配对成功 | `MatchModal`，可直接发开场白 |
| 资料信息 | 照片切换 + info pills（基本 / 简介 / looking / 兴趣 / 生活方式） |

---

## 5. 喜欢

| 功能点 | 说明 |
|---|---|
| 收到的喜欢 | 页内 Tab |
| 发出的喜欢 | 页内切换（无独立分包页） |
| 未解锁态 | 模糊头像 + 高级会员解锁引导 |
| 解锁后操作 | Pass / Like；Super Like 角标 |
| QA 提示 | 配对后需女问男答再开聊（无 Say Hi） |

---

## 6. 消息

| 功能点 | 说明 |
|---|---|
| 搜索会话 | 支持搜索 |
| 新配对 | 横滑展示 |
| 会话列表 | 文字会话入口 |
| ExpiryRing | 配对 / 会话倒计时（约 48h 相关窗口） |
| QA 待处理 | 红点与文案；「轮到你」提示 |
| 跳转 | 聊天室 / 对方资料 |

---

## 7. 我的

| 功能点 | 说明 |
|---|---|
| 头像与完整度 | 资料完整度展示 |
| VIP 卡 | 会员购买 / 管理入口 |
| 库存 | 心动 / 曝光 / 反悔 |
| 编辑资料 | 跳转 `pagesA/me/edit` |
| 特色玩法入口 | Swipe Night / Matchmaker / Campus / Select / Face to Face |
| 安全中心 | Safety |
| 分享 / 邀请 | 邀请归因 |
| 设置 / 协议 / 退出 | 账号与合规 |

---

## 8. 分包 `pagesA` 功能

| 页面 | 功能 |
|---|---|
| `profile/detail` | 他人资料：照片轮播、bio、prompts、兴趣；举报 / 拉黑 / 喜欢 |
| `chat/room` | **完整 QA 门控**（提问模板 → 回答 → 女方审阅）+ 文字 / 图 / GIF / 语音 + 翻译 + 视频通话入口 |
| `chat/call` | 视频通话（Agora） |
| `me/edit` | 照片智能排序、基本信息、MBTI / 星座 / 感情、灵魂问答、兴趣、生活方式 |
| `me/preview` | 资料预览 |
| `me/settings` | 语言 / 外观、隐身、社交账号、通知、安全、真人认证、黑名单、微信 / Apple / Google、恢复购买、法律 |
| `me/notifications` | 配对 / 消息 / 喜欢 / 营销推送开关 |
| `me/verify` | 真人认证（Persona + 沙箱） |
| `me/legal` | 协议、社区准则、导出数据、删号 |
| `me/safety` | 紧急联系人、约会分享链接、SOS、屏蔽词 |
| `features/swipe-night` | 夜间限时互选 |
| `features/matchmaker` | 为两位好友牵线 |
| `features/campus` | 绑定学校 / .edu 校验 stub / 校园 feed |
| `features/select` | 精选池申请与 feed |
| `features/face-to-face` | 约 30 分钟附近窗口 |

---

## 9. VIP / 支付 / 道具

| 能力 | 说明 |
|---|---|
| VipSheet | 三档会员 + 月期；道具商城 |
| 支付 | 微信 / 支付宝（国内渠道） |
| 道具 | 心动（Super Like）、曝光（Boost）、反悔（Rewind） |
| 会员权益 | 日配额加量、隐身、喜欢解锁等（以后端 entitlement 为准） |

---

## 10. 安全与合规

- 安全中心（紧急联系人、约会分享、SOS、屏蔽词）
- 真人认证
- 黑名单
- 隐身模式（会员）
- 数据导出 / 账号注销
- 用户协议 / 隐私政策 / 社区准则

---

## 11. 相对其他 APP 的差异要点

- 消息规则为 **QA 门控**，聊天室含完整问答审阅流
- **国内支付** + 微信登录为主
- 发现页有 **HomeBanner** 与 **每日推荐硬配额**
- 喜欢页无 Say Hi / Like all；无独立 `likes/sent` 分包
- VIP / 道具中文文案体系（会员 / 心动 / 曝光）
