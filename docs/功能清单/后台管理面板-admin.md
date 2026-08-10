# 功能清单 · 后台管理面板（Admin）

> 源码目录：`frontend/admin`  
> 技术栈：Vue 3 + Vite + Element Plus + vue-i18n  
> 开发代理：`5174 → :8000/api`  
> 性质：**自研运营后台**（未挂载 Django Admin）  
> 后端 API：`/api/admin/`（登录鉴权 / 成员角色）+ `/api/spark-admin/`（业务运营）

多产品工作台支持：`spark_main` / `swipe_main` / `matchup_main` 等；支持 App「全部」+ 地区筛选。

---

## 1. 登录与权限

### 1.1 登录

| 能力 | 说明 |
|---|---|
| 账号密码登录 | `POST /api/admin/login/` |
| Token 持久化 | `localStorage.admin_token`，请求头 `token` |
| 路由守卫 | 无 token → `/login`；按 `meta.perm` 校验菜单权限 |
| 语言 | 登录页 / 顶栏切换中 / 英 |
| 登录写入 | `token` / `username` / `role` / `permissions` / `admin_app_ids`，并设置 workspace |

### 1.2 角色（6 种）

| 角色 | 默认范围（概要） |
|---|---|
| `super_admin` | `*` 全部 |
| `operator` | 看板、用户、聊天、速配、群、社区、漏斗、订单、Firebase、广告、埋点、配置类（无 safety / review / 成员） |
| `support` | 看板、用户、聊天、速配、群、社区、内容安全 |
| `finance` | 看板、订单、Firebase |
| `analyst` | 看板、Analytics、Firebase |
| `reviewer` | 内容安全、发版审核、社区 |

- 权限可按 **App** 覆盖（`AdminRolePermission`）
- 成员可绑定 `admin_app_ids`
- 菜单与路由双重过滤；超管或空 permissions 视为全开

### 1.3 系统模块

| 模块 | 路由 | 能力 |
|---|---|---|
| 管理员 | `/admin-members` | 增改账号、角色、可访问 App、启停（仅超管写） |
| 权限管理 | `/admin-roles` | 按 App 勾选角色菜单权限并保存 |

---

## 2. 菜单结构

```
工作台
  └ 汇总统计 (/)

运营
  ├ 用户运营 (/users)
  ├ 聊天记录 (/chats)
  ├ 一键速配 (/quick-match)
  ├ 群聊管理 (/groups)
  ├ 社区内容 (/community)
  ├ 推荐漏斗 (/funnel)
  ├ 订单 / SKU (/orders)
  └ Firebase (/firebase)

增长与安全
  ├ 广告投放 (/ads)
  ├ 内容安全 (/safety)
  └ Analytics (/events)   ← /analytics 重定向到此

配置
  ├ App 基础配置 (/config)  ← /app-list 重定向
  ├ 三方配置 (/providers)
  ├ 系统通知 (/push-configs)
  ├ 国家与法律 (/country)
  └ 发版审核 (/review)

系统
  ├ 管理员 (/admin-members)
  └ 权限管理 (/admin-roles)
```

跨页通用：`WorkspaceFilter`（产品 / 地区）、中英 i18n、侧栏折叠、环境徽章（dev / prod）。

---

## 3. 各模块功能

### 3.1 汇总统计（Dashboard）`/`

| 能力 | 说明 |
|---|---|
| 筛选 | App、地区、平台、日期区间 |
| KPI | 今日注册、DAU、今日 GMV、付费次数、首购用户、付费率（含较昨日） |
| 图表 / 表 | 注册趋势、GMV 趋势、平台分布、VIP 等级分布 |
| 留存 | 注册队列 D0–D30 热力 |
| 列表 | 近期支付流水 |
| 操作 | 刷新（只读） |

### 3.2 用户运营 `/users`

| 能力 | 说明 |
|---|---|
| 筛选 | App + 邮箱 / 昵称搜索；分页 |
| 列表字段 | App、昵称、邮箱、登录方式、地区 / 语言 / 城市、ABC 评级、VIP、是否付费、状态、创建时间 |
| 详情抽屉 | 相册预览、资料、VIP 到期、消耗品余额等 |
| 操作 | 发放 VIP（Plus/Gold/Platinum × 天/月）；发放消耗品（Super Like / Boost / Rewind）；清除 VIP；封禁 / 解封 |

### 3.3 聊天记录 `/chats`

| 能力 | 说明 |
|---|---|
| 搜索 | 用户 ID / 邮箱 / 昵称 |
| 列表 | 双方信息、最后消息、消息数、时间 |
| 抽屉 | 文本 / 图 / 语音 + 译文 |
| 权限 | **只读**（无删改） |

### 3.4 一键速配 `/quick-match`

| 能力 | 说明 |
|---|---|
| 状态筛选 | 进行中 / 已结束 |
| 排队 | 排队人数 + 排队票列表；取消排队 |
| 配对 | 配对列表；结束进行中配对 |
| 说明 | 独立匹配池（不写交友 Match） |

### 3.5 群聊管理 `/groups`

| 能力 | 说明 |
|---|---|
| 搜索 | 群名 / 群主 |
| 状态 | active / muted / dissolved |
| 详情 | 成员角色 + 最近消息 |
| 操作 | 禁言 / 解除 / 解散 |

### 3.6 社区内容 `/community`

| 能力 | 说明 |
|---|---|
| 帖子审核 | 类型 moment / community / video；状态 visible / hidden / deleted；下架 / 恢复 / 删除 |
| 话题管理 | 新建 / 编辑（标题、排序、启用、封面 URL） |

### 3.7 推荐漏斗 `/funnel`（三 Tab）

| Tab | 能力 |
|---|---|
| 机器人卡片 | 新增、启用 / 禁用、删除；**下载 Excel 模板**；**Excel 导入** |
| 机器人推荐列表 | 按 App × 地区 × 语言配置机器人集合与优先级；增删改 |
| 真实用户推荐 | ABC 占比规则（A+B+C=100）；优先级；增删改 |

> 后端另有 `funnel-recompute`，前端当前未必暴露按钮。

### 3.8 订单 / SKU `/orders`

| 能力 | 说明 |
|---|---|
| 订单 | 只读列表（用户、商品、金额、状态、时间） |
| SKU | 新增 / 编辑 / 启停；类型 subscription / consumable；tier 含 VIP 与消耗品 |

### 3.9 Firebase `/firebase`

三 Tab **只读**：注册用户 / 订单 / 支付成功（mock store 文案）。

### 3.10 广告投放 `/ads`（四 Tab）

1. **广告链接**：名称、Deep Link、Tag、Campaign ID、来源；新增  
2. **Google 广告系列**：同步 API、展示指标、填入链接  
3. **Facebook 广告系列**：同上  
4. **广告归因**：状态 / 渠道筛选；自动匹配、批量匹配、人工解算、丢弃  

凭证依赖「三方配置」中的 Google / Facebook Ads。

### 3.11 内容安全 `/safety`（四 Tab）

| Tab | 操作 |
|---|---|
| 照片人审 | 通过 / 拒绝 |
| 举报 | 标记已处理 |
| 敏感词 | 按地区添加 |
| 域名白名单 | 添加域名 |

### 3.12 Analytics `/events`

| 能力 | 说明 |
|---|---|
| 筛选 | 日期 + App |
| 总览 | 事件量 / 活跃 / 种类 / 人均 KPI；趋势；热门事件；语言 / 版本分布 |
| 事件排行 | 按事件统计 |
| 转化漏斗 | 自定义事件步骤计算转化率 |
| 事件流 | 按事件名 / 关键词；翻页 |

### 3.13 App 基础配置 `/config`

| 能力 | 说明 |
|---|---|
| App 列表 | CRUD（不删用户数据） |
| 基础 Tab | App ID、名称、包名、TOS / 隐私、功能模块开关 |
| 产品规则 | 开聊模式、时限、同端推荐、延长匹配、夸夸、QA 门禁、日推荐上限、VIP 展示名 |
| 发现参数 | 按地区日右滑 / 匹配过期 / Say Hi 等 |
| 地图 SDK | 高德 / Google Key 记录 |

### 3.14 三方配置 `/providers`

按官方字段可视化配置（密钥脱敏），支持 App 级 / 全局；未配回退 `.env`。

| 类别 | Provider |
|---|---|
| 支付 | Apple IAP、Google Play |
| 登录 | Google OAuth |
| 地图 | Amap、Google Maps |
| 推送 | UniPush |
| 广告 | Google Ads、Facebook Ads |
| 分析 | GA4 |
| 翻译 | Google Translate（可测连通） |
| 实名 | Persona |

### 3.15 系统通知 `/push-configs`

| 能力 | 说明 |
|---|---|
| 筛选 | 语言、事件类型 |
| CRUD | 标题 / 正文模板、Deep Link、日上限、延迟区间、启用 |
| 事件 | `new_like` / `new_match` / `new_message` / `silent_recall`（含 D1/D3/D7） |

### 3.16 国家与法律 `/country`

按地区保存：最低年龄、货币、商店审核备注；列表展示 JSON config（合并到 bootstrap）。

### 3.17 发版审核 `/review`

| 能力 | 说明 |
|---|---|
| 配置 | 按 platform + package + version 开关 Review Mode |
| 效果 | 开启后该版本推荐 Feed 返回空列表 |
| 列表 | 快捷启停 |

---

## 4. 操作能力矩阵

| 模块 | 查 / 筛 | 增 | 改 | 删 / 禁 | 导入 / 导出 |
|---|---|---|---|---|---|
| Dashboard | App / 地区 / 平台 / 日期 | — | — | — | — |
| 用户 | App + 关键词 | — | VIP / 额度 / 封禁 | 清 VIP | — |
| 聊天 | App + 关键词 | — | — | — | — |
| 速配 | App + 状态 | — | 取消排队 / 结束 | — | — |
| 群聊 | App + 状态 + 搜索 | — | 禁言 / 解散 | — | — |
| 社区 | 类型 / 状态 / 搜索 | 话题 | 帖状态 / 话题 | 帖删除 | — |
| 漏斗 | App / 地区 | 机器人 / 列表 / 规则 | 启停 / 编辑 | 删除 | **Excel 模板 + 导入** |
| 订单 / SKU | App | SKU | SKU | SKU 启停 | — |
| Firebase | App | — | — | — | — |
| 广告 | App / 地区 + 归因筛 | 链接 | 解算 / 匹配 | 丢弃 | 同步第三方 |
| 安全 | App / 地区 | 词 / 域名 | 审图 / 结案 | — | — |
| Analytics | App / 日期 / 事件 | — | — | — | — |
| App 配置 | — | App | 全配置 | 删配置 | — |
| Providers | App | — | 保存 / 测试 | — | — |
| Push | App / 语言 / 事件 | ✓ | ✓ | ✓ | — |
| 国家法律 | App | / 改配置 | ✓ | — | — |
| 发版审核 | App | / 改 | ✓ | 快捷关 | — |
| 管理员 | — | ✓ | ✓ | 启停 | — |
| 角色权限 | App | — | 勾选保存 | — | — |

---

## 5. 关键文件索引

| 类型 | 路径 |
|---|---|
| 路由 | `frontend/admin/src/router.js` |
| 菜单 / 布局 | `frontend/admin/src/views/Layout.vue` |
| API | `frontend/admin/src/api.js` |
| 工作台 | `frontend/admin/src/workspace.js` |
| 中文文案 | `frontend/admin/src/i18n/locales/zh-CN.js` |
| 页面 | `frontend/admin/src/views/*.vue` |
| 业务 Admin API | `backend/Apps/views/spark_admin/view.py` |
| 登录 / RBAC API | `backend/Apps/views/admin/view.py` |
| RBAC 定义 | `backend/tools/admin_rbac.py` |

---

## 6. 小结

面向多 App 交友产品的运营控制台，覆盖用户 / 内容 / 匹配 / 商业化 / 增长归因 / 配置与权限。  
VIP 能力分散在「用户发放」与「订单 SKU」，无独立 VIP 一级菜单；导入导出目前主要在推荐漏斗 Excel。
