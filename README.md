# SPARK 社交产品

Django + DRF 后端 · UniApp Vue3 客户端 · Vue3 Admin

## 开发规范（必读）

| 文档 | 用途 |
| --- | --- |
| [`开发规范/业务架构说明.md`](开发规范/业务架构说明.md) | 业务：一后端多壳、产品规则、域划分、API/模型地图 |
| [`开发规范/业务性能评估.md`](开发规范/业务性能评估.md) | 性能评估：热路径、容量粗估、SLO |
| [`开发规范/前后端性能优化建议.md`](开发规范/前后端性能优化建议.md) | 性能落地：Feed/Badges/会话、索引、前端减载、分阶段路线 |
| [`开发规范/工程规范化建议.md`](开发规范/工程规范化建议.md) | 工程纪律：多壳同步、租户/支付/RBAC、前后端与库约束补强 |
| [`开发规范/运维与维护手册.md`](开发规范/运维与维护手册.md) | 运维：启停、seed、maintenance、过审、支付值班、发版清单 |
| [`开发规范/可优化清单.md`](开发规范/可优化清单.md) | 优化落地清单：性能/正确性/安全缺口与阶段进度 |
| [`开发规范/Bug穷举清单.md`](开发规范/Bug穷举清单.md) | 缺陷 SoT：全栈静态审计条目 |
| [`开发规范/AI全栈开发SOP.md`](开发规范/AI全栈开发SOP.md) | 过程：阶段门禁、「继续完善只补洞」、人工物料分离 |
| [`开发规范/服务端规范.md`](开发规范/服务端规范.md) | 后端：ApiResponse、Redis+AES Token、`t_` 表、禁止 django.contrib.auth |
| [`开发规范/用户端规范.md`](开发规范/用户端规范.md) | 客户端：无 `src/`、禁止 `gap`/IIFE、勿改 `utils/http.js` 底层、接口走 `api/` |

业务规则以 `需求资料/` 为 SoT；工程约定以本 README + 上述规范为准。

前端静态门禁（禁 `gap` / 禁页面 `uni.request`）：

```bash
bash scripts/check-frontend-rules.sh
```

## 数据库约束（强制）

- 远程 PostgreSQL **只允许连接 `spark` 库**
- **禁止**连接或修改 `uivsbe` 及其它库
- Redis 使用独立 DB `15`

配置见 [`backend/.env`](backend/.env)（参考根目录 `(1).env` 主机/账号，库名固定为 `spark`）。

## 后端

```bash
cd backend
# Python 3.10+
python3.10 -m venv uivsbe_env
source uivsbe_env/bin/activate   # Windows: uivsbe_env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate models --settings=uivsbe_backend.settings.dev
# O-11: Campus 等表跨 0022/0023，禁止只迁一半；发版前 showmigrations 确认两者都已 apply
python manage.py seed_spark --settings=uivsbe_backend.settings.dev
python manage.py runserver 8000 --settings=uivsbe_backend.settings.dev
```

测试账号：
- App：`test@spark.app` / `SparkTest1`
- Admin：`spark_admin` / `SparkAdmin1`（或 `admin@spark.app`）

API 文档：http://127.0.0.1:8000/api/docs/

定时维护：`python manage.py spark_maintenance --settings=uivsbe_backend.settings.dev`

## 客户端（uni-app · JavaScript）

按产品拆成独立工程（`app_id` 不同，可独立发版）：

| 目录 | 产品 | APP_ID |
| --- | --- | --- |
| `frontend/mobile_spark` | Spark | `spark_main` |
| `frontend/mobile_swipe` | Swipe | `swipe_main` |
| `frontend/mobile_ember` | Ember | `ember_main` |
| `frontend/mobile_matchup` | MatchUp | `matchup_main` |
| `frontend/mobile_flick` | Flick | `flick_main` |

```bash
cd frontend/mobile_spark   # 或其他 mobile_*
npm install
npm run dev:h5
```

视觉：推荐页 / 资料详情按 `需求资料/Dating- UI` 1:1 还原。

## 管理后台

布局对齐 [Ant Design Pro](https://github.com/ant-design/ant-design-pro) 壳层（侧栏/顶栏/PageContainer），组件库仍为 Element Plus。

```bash
cd frontend/admin
npm install
npm run dev
```

打开 http://127.0.0.1:5174（端口以本地 Vite 实际为准；客户端 H5 通常为 5173）
