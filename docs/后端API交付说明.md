# 后端API交付说明

> 2026年6月20日 | 数据清洗与入库全部完成，API已就绪

---

## 一、数据库信息

### 连接信息
```
Host: localhost
Port: 3306
User: root
Password: 123456
Database: secondhouse_cq
Charset: utf8mb4
```

### E-R图

```
┌────────────────────────────────────────────────────┐
│                      houses                         │
│  主房源表 — 8,576条，覆盖39个区县                    │
├────────────┬───────────────┬───────────────────────┤
│ id         │ BIGINT (PK)   │ 自增主键              │
│ title      │ VARCHAR(300)  │ 房源标题              │
│ district   │ VARCHAR(50)   │ 区县 [IDX]            │
│ community  │ VARCHAR(100)  │ 小区名称              │
│ address    │ VARCHAR(300)  │ 详细地址/商圈         │
│ total_price│ DECIMAL(12,2) │ 总价(万) [IDX]        │
│ unit_price │ DECIMAL(10,2) │ 单价(元/㎡) [IDX]     │
│ area       │ DECIMAL(8,2)  │ 面积(㎡)              │
│ layout     │ VARCHAR(20)   │ 户型原文 e.g.3室2厅2卫│
│ rooms      │ INT           │ 室                    │
│ halls      │ INT           │ 厅                    │
│ bathrooms  │ INT           │ 卫                    │
│ floor_desc │ VARCHAR(50)   │ 楼层描述原文          │
│ floor_type │ VARCHAR(10)   │ 低层/中层/高层        │
│ total_floors│ INT          │ 总楼层                │
│ orientation│ VARCHAR(20)   │ 朝向                  │
│ decoration │ VARCHAR(20)   │ 装修                  │
│ build_year │ INT           │ 建成年份              │
│ lng        │ DECIMAL(10,6) │ 经度                  │
│ lat        │ DECIMAL(10,6) │ 纬度                  │
│ followers  │ INT           │ 关注人数(暂为0)       │
│ source     │ VARCHAR(20)   │ 来源 [IDX]            │
│ source_id  │ VARCHAR(100)  │ 原始来源ID            │
│ fingerprint│ VARCHAR(64)   │ 去重指纹 [UK]         │
│ status     │ VARCHAR(20)   │ on_sale/sold/offline  │
│ first_seen │ DATETIME      │ 首次发现(AUTO)        │
│ last_updated│ DATETIME     │ 最后更新(AUTO)        │
└────────────┴───────────────┴───────────────────────┘

┌──────────────────────┐  ┌──────────────────────────┐
│      crawl_log       │  │    analysis_results      │
├──────────────────────┤  ├──────────────────────────┤
│ id (PK)              │  │ id (PK)                  │
│ source               │  │ analysis_type            │
│ district             │  │   prediction/clustering  │
│ page                 │  │   /rules                 │
│ houses_found         │  │ result_data (JSON)       │
│ new_added            │  │ create_time              │
│ updated              │  └──────────────────────────┘
│ status               │
│ message              │
│ crawl_time           │
└──────────────────────┘
```

### 入库结果一览

```sql
-- 总房源数
SELECT COUNT(*) FROM houses;              -- 8,576

-- 按来源
SELECT source, COUNT(*) FROM houses GROUP BY source;
-- anjuke: 8,276
-- lianjia: 300

-- 区县覆盖
SELECT COUNT(DISTINCT district) FROM houses;  -- 39

-- 有坐标的
SELECT COUNT(*) FROM houses WHERE lng > 0;     -- 313

-- 价格统计
SELECT
  ROUND(MIN(total_price),1) as min_万,
  ROUND(MAX(total_price),1) as max_万,
  ROUND(AVG(total_price),1) as avg_万,
  ROUND(AVG(unit_price),0) as avg_单价
FROM houses WHERE total_price > 0 AND total_price < 5000;
-- min: 0.0万, max: 888.0万, avg: 74.4万, avg单价: 6063元/㎡
```

---

## 二、项目文件结构

```
backend/
├── main.py                    # FastAPI 入口 + CORS配置
├── database.py                # pymysql 连接上下文管理器
├── schemas.py                 # Pydantic 响应模型
├── setup_database.py          # 建库建表脚本
├── import_csv_to_mysql.py     # 数据批量入库(500条/批)
├── data_cleaner.py            # 数据清洗引擎(价格修复+去重)
├── update_listings.py         # 增量更新逻辑(预留)
├── routers/
│   ├── __init__.py
│   ├── stats.py               # 统计接口 ×5
│   ├── houses.py              # 房源列表+详情接口
│   ├── analysis.py            # 分析结果+快速统计接口
│   └── update.py              # 增量更新触发接口
└── __pycache__/

data/processed/
└── houses_clean.csv           # 清洗后数据 (10,671行)
```

---

## 三、API接口详细说明

### 统一响应格式

```json
{
  "code": 200,        // 200=成功 404=无数据 500=错误
  "message": "success",
  "data": { ... },    // 实际数据
  "total": 8576       // 总数(列表接口带此字段)
}
```

### 接口清单

#### 1. 数据总览 — `GET /api/stats/overview`

**请求**: 无参数

**响应**:
```json
{
  "code": 200,
  "data": {
    "total_houses": 8576,
    "avg_unit_price": 6063.35,
    "avg_total_price": 74.35,
    "max_unit_price": 25000.00,
    "min_unit_price": 1000.00,
    "district_count": 39,
    "update_time": "2026-06-20 ...",
    "by_source": {"anjuke": 8276, "lianjia": 300},
    "by_district": [
      {"district": "两江新区", "count": 2955, "avg_unit_price": 9839.62, "avg_total_price": 93.45},
      ...
    ]
  }
}
```

#### 2. 房源列表 — `GET /api/houses`

**参数**（全部可选）:

| 参数 | 类型 | 示例 | 说明 |
|------|------|------|------|
| district | string | 两江新区 | 区县 |
| min_price | float | 80 | 最低总价(万) |
| max_price | float | 200 | 最高总价(万) |
| min_area | float | 60 | 最小面积(㎡) |
| max_area | float | 120 | 最大面积(㎡) |
| rooms | int | 3 | 室数 |
| floor_type | string | 中层 | 低层/中层/高层 |
| decoration | string | 精装 | 装修 |
| orientation | string | 南 | 朝向 |
| source | string | lianjia | 数据来源 |
| page | int | 1 | 页码(默认1) |
| page_size | int | 20 | 每页条数(默认20,最大50) |

**请求示例**:
```
GET /api/houses?district=两江新区&min_price=80&max_price=200&rooms=3&page=1&page_size=20
```

**响应字段**:
```json
{
  "code": 200,
  "total": 1066,
  "data": [{
    "id": 123,
    "title": "龙湖春森彼岸 精装三房 108万",
    "district": "两江新区",
    "community": "龙湖春森彼岸",
    "address": "北滨路",
    "total_price": 108.00,
    "unit_price": 12518.00,
    "area": 86.28,
    "layout": "3室2厅2卫",
    "rooms": 3, "halls": 2, "bathrooms": 2,
    "floor_desc": "中层(共32层)",
    "floor_type": "中层", "total_floors": 32,
    "orientation": "南",
    "decoration": "精装",
    "build_year": 2018,
    "lng": 106.540000, "lat": 29.570000,
    "source": "anjuke"
  }]
}
```

#### 3. 房源详情 — `GET /api/houses/{id}`

**路径参数**: `id` — 房源ID

#### 4. 区县详细统计 — `GET /api/stats/district/{name}`

**路径参数**: `name` — 区县名称(如"两江新区")

**响应**: 含装修分布、户型分布、价格区间分布、面积分布、TOP10热门小区

#### 5. 价格区间分布 — `GET /api/stats/price-distribution`

**响应**: `unit_price_bins`(6级 5000以下~25000以上) + `total_price_bins`(6级 50万以下~300万以上)

#### 6. 户型分布 — `GET /api/stats/layout-distribution`

**响应**: 1-9室分布 + 各户型均价

#### 7. 面积区间分布 — `GET /api/stats/area-distribution`

**响应**: 5级(60以下~150以上)

#### 8-10. 分析接口 — `GET /api/analysis/{prediction|clustering|rules}`

**状态**: 当前返回404 "暂无分析结果"。需在`analysis/`目录开发分析脚本，将JSON结果写入`analysis_results`表。

#### 11. 快速统计 — `GET /api/analysis/quick-stats`

**响应**: 总房源数、均价、均价面积、装修分布、楼层分布（基于现有数据实时计算）

#### 12. 增量更新 — `POST /api/update`

**状态**: 手动模式。需接入`crawler/update.py`实现自动增量。

---

## 四、启动指南

```bash
# 安装依赖
pip install fastapi uvicorn pymysql pandas

# 初始化数据库
python backend/setup_database.py

# 清洗并入库（仅首次）
python backend/data_cleaner.py
python backend/import_csv_to_mysql.py

# 启动API
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

启动后访问：
- **Swagger文档**: http://localhost:8000/docs （自动生成的交互式API文档）
- **OpenAPI Schema**: http://localhost:8000/openapi.json （已导出至 `docs/openapi_schema.json`）
- **健康检查**: http://localhost:8000/health

---

## 五、数据处理说明

### 清洗前后对比

| 阶段 | 数量 | 说明 |
|------|------|------|
| 原始CSV读取 | 91,240行 | 38 anjuke_m_ + 1 anjuke_ + 10 lianjia + 2 merged |
| 价格修复 | 40,788行修复 | 标题提取优先，/100000回退 |
| 标题去重(同文件) | -75,824行 | 爬虫翻页bug，同一页重复采了12+次 |
| 跨文件去重 | -3,066行 | all_listings_merged 与 m_ 文件大量重叠 |
| 最终入库 | **8,576行** | INSERT IGNORE 消除指纹碰撞 |

### 已知数据限制

| 字段 | 填充率 | 原因 |
|------|--------|------|
| lng/lat | 3.7% | 仅`anjuke_两江新区.csv`有坐标 |
| decoration | ~5% | 大部分由快速爬虫采集，未进详情页 |
| floor_desc/floor_type | ~5% | 同上 |
| build_year | ~3% | 同上 |
| bathrooms | ~10% | 链家数据齐全，安居客仅部分有 |

**后续补充方案**: 配置代理后运行 `python crawler/anjuke_backfill.py` 可从详情页回填缺失字段。

---

## 六、Swagger文档截图说明

启动API后访问 `http://localhost:8000/docs` 可以看到 FastAPI 自动生成的 Swagger UI，包含：

1. **所有14个接口的完整列表**，按 tags 分组(stats/houses/analysis/update)
2. **每个接口的请求参数**、类型、是否必填、示例值
3. **Try it out 功能** — 可直接在页面上填入参数测试接口
4. **响应示例** — JSON格式的返回数据预览

OpenAPI Schema 文件已导出至 `docs/openapi_schema.json`，可用 Swagger Editor 或 Postman 导入。
