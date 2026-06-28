# 素材交付 — API模块

> 提供给成员C（王宇）用于撰写文档第6章"数据分析与可视化实现" | 更新于2026年6月21日

## 1. 功能说明

本模块基于 FastAPI 框架构建 RESTful API，为 Android App 提供重庆市二手房数据的查询、统计和分析接口。

**架构设计**：采用四层分离结构——`main.py` 负责应用入口和 CORS 跨域配置，`database.py` 封装 pymysql 连接池（上下文管理器自动关闭连接），`schemas.py` 定义 Pydantic 响应模型，`routers/` 下按功能分为 stats（统计）、houses（房源）、analysis（分析）、update（更新）四个路由模块。

**实现的 14 个接口**：数据总览接口输出 54,980 条房源的总览统计和 39 区县分布；房源列表接口支持 10 个可选筛选参数（区县/价格/面积/户型/楼层/装修/朝向/来源）+分页，动态构建 SQL WHERE 子句；5 个统计接口覆盖价格区间、户型、面积、区县详情等维度；3 个分析接口（prediction/clustering/rules）已接入分析模块产出，返回真实数据；`POST /api/update` 提供增量更新触发能力，含 status/history/schedule 查询接口。所有接口统一 `{code, message, data, total}` 响应格式，已配置 CORS 支持 Android 模拟器（10.0.2.2:8000）和公网（ngrok隧道）跨域访问。

**技术栈**：FastAPI + uvicorn + pymysql + Pydantic + MySQL 8.0。

---

## 2. 核心代码片段

### 2.1 动态 SQL 筛选 + 分页（房源列表）

```python
@router.get("/houses")
def get_houses(district=None, min_price=None, max_price=None,
               rooms=None, page=1, page_size=20):
    """房源列表 — 10个可选筛选参数 + 分页"""
    conditions = ["total_price > 0 AND total_price < 5000"]
    params = []

    # 动态拼接 WHERE 条件，只对传入参数生效
    if district:  conditions.append("district = %s"); params.append(district)
    if min_price: conditions.append("total_price >= %s"); params.append(min_price)
    if rooms:     conditions.append("rooms = %s"); params.append(rooms)

    # 先查总数用于分页
    total = query_one(f"SELECT COUNT(*) as total FROM houses WHERE {' AND '.join(conditions)}", params)['total']

    # 再查分页数据
    rows = query(f"SELECT * FROM houses WHERE {' AND '.join(conditions)} LIMIT %s OFFSET %s",
                 params + [page_size, (page-1)*page_size])
    return APIResponse(data=list(rows), total=total)
``` {data-source-line="42"}

### 2.2 区县详情聚合查询

```python
@router.get("/district/{name}")
def get_district_detail(name: str):
    """某区县全面统计 — 一次请求返回6类数据"""
    base = query_one("SELECT COUNT(*) house_count, AVG(unit_price) avg_price "
                     "FROM houses WHERE district=%s", (name,))

    # 装修/户型/价格/面积分布 + TOP10热门小区
    price_dist = query("""SELECT CASE WHEN total_price<50 THEN '50万以下'
        WHEN total_price<80 THEN '50-80万' ...
        END as `range`, COUNT(*) count
        FROM houses WHERE district=%s GROUP BY `range`""", (name,))

    top_comm = query("""SELECT community name, COUNT(*) count, AVG(unit_price) avg_price
        FROM houses WHERE district=%s GROUP BY community ORDER BY count DESC LIMIT 10""", (name,))
    return APIResponse(data={**base, "price_distribution": price_dist, "top_communities": top_comm})
``` {data-source-line="65"}

---

## 3. 系统架构图（需绘制）
https://my.feishu.cn/wiki/NNDXwP18DiEoQQkTnzIc0uRrnbf
飞书第5个

> 使用 draw.io / ProcessOn / Visio 绘制，建议导出为PNG插入文档第3章"系统设计"。

**架构图应包含四层**：

```
┌─────────────────────────────────────────────────┐
│              展示层 (Android App)                 │
│  Kotlin + Retrofit + MPAndroidChart / ECharts    │
│  数据总览 │ 地图热力图 │ 图表分析 │ 筛选查询 │ 分析结论 │
└────────────────────┬────────────────────────────┘
                     │ HTTP / JSON (Retrofit + OkHttp)
┌────────────────────▼────────────────────────────┐
│              API 网关层 (FastAPI)                 │
│  /api/stats/*  │  /api/houses/*  │  /api/analysis/*  │
│  统一响应: {code, message, data, total}          │
│  CORS 跨域  │  Swagger 自动文档                  │
└────────────────────┬────────────────────────────┘
                     │ pymysql
┌────────────────────▼────────────────────────────┐
│              数据层 (MySQL 8.0)                   │
│  houses (54,980条) │ crawl_log │ analysis_results │
│  6个索引 (district/price/source/status/fingerprint)│
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│            数据采集与分析层 (Python)               │
│  爬虫(安居客+链家) → 清洗去重 → 分析(预测+聚类)    │
└─────────────────────────────────────────────────┘
```

## 4. 运行截图（操作步骤）

### 截图1：FastAPI Swagger 自动文档页

chongqing-house-analysis/docs/截图/API文档页.png

**操作步骤**：
1. 启动后端服务：
   ```bash
   cd D:\SWU\大二下\学年设计\chongqing-house-analysis
   venv\Scripts\activate
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
2. 打开浏览器，访问 `http://localhost:8000/docs`
3. 截取完整的 Swagger UI 页面，应包含：
   - 页面标题"重庆二手房数据 API"
   - stats / houses / analysis / update 四个分组
   - 展开 `/api/stats/overview` 显示响应示例
4. 可选：再截一张 `http://localhost:8000/redoc` 的备用文档页

### 截图2：API 接口测试（浏览器直接访问）
接口测试所有图片都在截图文件夹下面对应
![首页总览](API关联规则overview.png)

**操作步骤**：
1. 确保后端服务已启动（步骤同上）
2. 浏览器打开以下URL，逐个截取JSON响应：
   - 首页总览：`http://localhost:8000/api/stats/overview`（应返回 total_houses=54980、district_count=39）
   - 房源筛选：`http://localhost:8000/api/houses?district=两江新区&min_price=80&max_price=200&rooms=3&page=1`
   - 区县详情：`http://localhost:8000/api/stats/district/渝中区`
   - 分析结果：`http://localhost:8000/api/analysis/prediction`
3. 截取浏览器窗口，展示完整的JSON响应

### 截图3：POST /api/update 测试
查看截图文件夹
API截图3

**操作步骤**：
1. 打开另一个终端，执行：
   ```bash
   curl -X POST http://localhost:8000/api/update
   curl http://localhost:8000/api/update/status
   ```
2. 或在浏览器中直接访问 `http://localhost:8000/api/update/status`
3. 截取返回的JSON结果（应显示 running 状态和 last_result）

---

## 4. 技术要点/难点

### 难点1：动态 SQL 构建与参数化查询的安全性

**问题**：房源列表接口 `/api/houses` 需要支持 10 个可选筛选参数，每个参数都可能为 null（不筛选）。如果使用 ORM 框架（如 SQLAlchemy），动态条件拼接比较方便；但本项目选择原生 pymysql 以保持轻量，这就需要手动构建安全的动态 SQL。

**解决方案**：采用"条件数组 + 参数数组"的配对模式。每个传入的筛选参数检查非空后，将 `"column = %s"` 推入 `conditions` 数组，同时将值推入 `params` 数组。最后用 `" AND ".join(conditions)` 拼接 WHERE 子句，`params` 顺序与 `%s` 占位符一一对应。所有用户输入都通过 `%s` 传递，由 pymysql 底层做转义，杜绝 SQL 注入。分页的 `LIMIT %s OFFSET %s` 追加在 `params` 末尾。这种方式比字符串拼接（f-string）安全，比 ORM 灵活，10 个条件任意组合都能生成合法 SQL。

### 难点2：跨域 CORS 与 Android 模拟器网络配置

**问题**：Android 模拟器访问本机服务需要使用特殊 IP `10.0.2.2` 而非 `localhost`，且浏览器/WebView 的跨域策略会阻止来自不同源的 API 请求。真机在同一 WiFi 下则需要电脑局域网 IP。

**解决方案**：在 FastAPI 的 `main.py` 中添加 CORS 中间件，`allow_origins=["*"]` 允许所有来源（开发阶段），`allow_methods=["*"]` 开放 GET/POST 等方法，`allow_headers=["*"]` 允许所有请求头。同时服务器绑定 `--host 0.0.0.0` 而非 `127.0.0.1`，使得局域网内其他设备可以通过电脑 IP 访问。Android 端的 Retrofit base URL 配置为 `http://10.0.2.2:8000`（模拟器）或 `http://192.168.x.x:8000`（真机），即可正常调用全部接口。

---

## 5. 接口速查卡

| # | 方法 | 路径 | 用途 | 测试命令 |
|---|------|------|------|---------|
| 1 | GET | `/api/stats/overview` | 首页总览 | `curl localhost:8000/api/stats/overview` |
| 2 | GET | `/api/houses` | 房源搜索 | `curl "localhost:8000/api/houses?district=两江新区&page=1"` |
| 3 | GET | `/api/houses/{id}` | 房源详情 | `curl localhost:8000/api/houses/100` |
| 4 | GET | `/api/stats/district/{name}` | 区县统计 | `curl localhost:8000/api/stats/district/渝中区` |
| 5 | GET | `/api/stats/price-distribution` | 价格分布 | `curl localhost:8000/api/stats/price-distribution` |
| 6 | GET | `/api/stats/layout-distribution` | 户型分布 | `curl localhost:8000/api/stats/layout-distribution` |
| 7 | GET | `/api/stats/area-distribution` | 面积分布 | `curl localhost:8000/api/stats/area-distribution` |
| 8 | POST | `/api/update` | 触发更新 | `curl -X POST localhost:8000/api/update` |

### 启动方式

```bash
# 1. 安装依赖
pip install fastapi uvicorn pymysql pandas

# 2. 初始化（首次）
python backend/setup_database.py
python backend/data_cleaner.py
python backend/import_csv_to_mysql.py
python backend/data_augmenter.py       # 数据增强至5万+
python analysis/run_analysis.py        # 运行分析模块

# 3. 启动服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 访问
# API 文档页:  http://localhost:8000/docs
# Android 端:  http://10.0.2.2:8000 (模拟器)
# 公网地址:    https://stallion-pointy-ensure.ngrok-free.dev (ngrok隧道)
```
