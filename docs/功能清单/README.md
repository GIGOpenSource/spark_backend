# Spark 功能清单文档索引

本目录根据当前代码库盘点生成，覆盖三款客户端、统一服务端与运营后台。

| 文档 | 说明 |
|---|---|
| [APP-她说-matchup.md](./APP-matchup.md) | 客户端「她说」`mobile_matchup` |
| [APP-SPARK-spark.md](./APP-SPARK-spark.md) | 客户端 SPARK `mobile_spark` |
| [APP-bee-swipe.md](./APP-bee-swipe.md) | 客户端 bee `mobile_swipe` |
| [服务端-backend.md](./服务端-backend.md) | Django 服务端 `/api/` |
| [后台管理面板-admin.md](./后台管理面板-admin.md) | Vue3 运营后台 `frontend/admin` |

## 三端产品差异速览

| 维度 | 她说 (matchup) | SPARK | bee (swipe) |
|---|---|---|---|
| App ID | `matchup_main` | `spark_main` | `swipe_main` |
| 消息规则 | QA 门控 `qa_gate` | 随时互聊 `any` | 女性先开口 `women_first` |
| 支付 | 微信 / 支付宝 | IAP | IAP |
| 特色 | 女问男答、日配额、HomeBanner | Top Picks、Say Hi、Boost report | Compliment、Dating modes、Extend |

生成日期：2026-08-08
