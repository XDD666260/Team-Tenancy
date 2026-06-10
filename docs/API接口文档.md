# API 接口文档

> 后端：胡霖（FastAPI） | App：解金明（Kotlin + Retrofit）
> 2026年6月9日

---

## 约定说明

### 服务器地址
- 模拟器访问本机：`http://10.0.2.2:8000`
- 真机同一WiFi访问：`http://电脑局域网IP:8000`

### 统一响应格式

```json
{
    "code": 200,
    "message": "success",
    "data": { ... },
    "total": 100
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 200=成功，404=没数据，500=服务器出错 |
| `message` | string | 提示信息 |
| `data` | object/array | 实际返回的数据 |
| `total` | int | 数据总数（列表接口用，方便翻页） |

---

## 接口列表总览

| 序号 | 方法 | 路径 | 说明 | 优先级 | A完成 | B确认 |
|------|------|------|------|--------|-------|-------|
| 1 | GET | `/api/stats/overview` | 首页数据总览 | 🔥高 | ☐ | ☐ |
| 2 | GET | `/api/houses` | 房源列表（筛选+分页） | 🔥高 | ☐ | ☐ |
| 3 | GET | `/api/stats/district/{name}` | 某区县详细统计 | 🔥高 | ☐ | ☐ |
| 4 | GET | `/api/stats/price-distribution` | 全市价格区间分布 | 中 | ☐ | ☐ |
| 5 | GET | `/api/stats/layout-distribution` | 户型分布统计 | 中 | ☐ | ☐ |
| 6 | GET | `/api/stats/area-distribution` | 面积区间分布 | 低 | ☐ | ☐ |
| 7 | GET | `/api/analysis/prediction` | 房价预测分析结果 | 中 | ☐ | ☐ |
| 8 | GET | `/api/analysis/clustering` | 聚类分析结果 | 低 | ☐ | ☐ |
| 9 | GET | `/api/analysis/rules` | 关联规则结果 | 低 | ☐ | ☐ |
| 10 | POST | `/api/update` | 触发增量数据更新 | 中 | ☐ | ☐ |

---

## 接口详细定义

### 1. 数据总览 — `GET /api/stats/overview`

**用途**：App 首页顶部卡片 + 各区县统计列表。

**请求**：无参数

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "total_houses": 52300,
        "avg_unit_price": 13200.50,
        "avg_total_price": 158.30,
        "max_unit_price": 45000.00,
        "min_unit_price": 2800.00,
        "district_count": 35,
        "update_time": "2026-06-15 14:30:00",
        "by_source": {
            "lianjia": 42000,
            "anjuke": 10300
        },
        "by_district": [
            {
                "district": "渝北区",
                "count": 8200,
                "avg_unit_price": 14500.00,
                "avg_total_price": 175.20,
                "biz_circle_count": 12
            },
            {
                "district": "江北区",
                "count": 6200,
                "avg_unit_price": 15800.00,
                "avg_total_price": 192.50,
                "biz_circle_count": 8
            }
        ]
    }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `by_source` | object | 按数据来源统计，`lianjia` + `anjuke` |
| `by_district[].biz_circle_count` | int | 该区县覆盖的商圈数量 |

---

### 2. 房源列表 — `GET /api/houses`

**用途**：App 筛选查询页面，支持多条件筛选 + 分页。

**请求参数**（全部可选）：

| 参数 | 类型 | 示例 | 说明 |
|------|------|------|------|
| `district` | string | `渝北区` | 区县筛选 |
| `biz_circle` | string | `观音桥` | 商圈筛选 |
| `min_price` | float | `80` | 最低总价（万） |
| `max_price` | float | `200` | 最高总价（万） |
| `min_area` | float | `60` | 最小面积（㎡） |
| `max_area` | float | `120` | 最大面积（㎡） |
| `rooms` | int | `3` | 户型-室 |
| `floor_type` | string | `中层` | 楼层类型：低层/中层/高层 |
| `decoration` | string | `精装` | 装修 |
| `orientation` | string | `南` | 朝向 |
| `source` | string | `lianjia` | 数据来源：lianjia / anjuke |
| `page` | int | `1` | 页码（默认1） |
| `page_size` | int | `20` | 每页条数（默认20，最大50） |

**请求示例**：
```
GET /api/houses?district=渝北区&biz_circle=观音桥&min_price=80&max_price=200&rooms=3&page=1&page_size=20
```

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": [
        {
            "id": 12345,
            "title": "龙湖春森彼岸 精装三房 南北通透",
            "district": "渝北区",
            "biz_circle": "观音桥",
            "community": "龙湖春森彼岸",
            "address": "北滨路258号",
            "total_price": 150.00,
            "unit_price": 12500,
            "area": 120.00,
            "layout": "3室2厅2卫",
            "rooms": 3,
            "halls": 2,
            "bathrooms": 2,
            "floor_desc": "中层(共32层)",
            "floor_type": "中层",
            "total_floors": 32,
            "orientation": "南",
            "decoration": "精装",
            "build_year": 2018,
            "lng": 106.540000,
            "lat": 29.570000,
            "followers": 128,
            "source": "lianjia",
            "crawl_time": "2026-06-15T14:30:00"
        }
    ],
    "total": 356
}
```

**房源对象字段对照**（与数据源分析笔记23个字段一一对应）：

| API字段 | 变量名 | 说明 |
|---------|--------|------|
| `title` | title | 房源标题 |
| `total_price` | total_price | 总价（万） |
| `unit_price` | unit_price | 单价（元/㎡） |
| `area` | area | 面积（㎡） |
| `layout` | layout | 户型原文 |
| `rooms` | rooms | 室 |
| `halls` | halls | 厅 |
| `bathrooms` | bathrooms | 卫 |
| `floor_desc` | floor_desc | 楼层描述原文 |
| `floor_type` | floor_type | 楼层类型 |
| `total_floors` | total_floors | 总楼层 |
| `orientation` | orientation | 朝向 |
| `decoration` | decoration | 装修 |
| `build_year` | build_year | 建成年代 |
| `community` | community | 小区名称 |
| `biz_circle` | biz_circle | 商圈 |
| `district` | district | 区县 |
| `address` | address | 详细地址 |
| `lng` | lng | 经度 |
| `lat` | lat | 纬度 |
| `followers` | followers | 关注人数 |
| `source` | source | 数据来源（lianjia / anjuke） |
| `crawl_time` | crawl_time | 爬取时间 |

---

### 3. 区县详细统计 — `GET /api/stats/district/{name}`

**用途**：App 点击某个区县后，显示该区县的详细统计。

**路径参数**：
| 参数 | 类型 | 示例 |
|------|------|------|
| `name` | string | `渝北区` |

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "district": "渝北区",
        "house_count": 8200,
        "avg_unit_price": 14500.00,
        "avg_total_price": 175.20,
        "avg_area": 108.50,
        "max_price": 2800.00,
        "min_price": 28.00,
        "biz_circle_count": 12,
        "decoration_distribution": [
            {"type": "精装", "count": 3500},
            {"type": "简装", "count": 2800},
            {"type": "毛坯", "count": 1900}
        ],
        "layout_distribution": [
            {"rooms": 1, "count": 500},
            {"rooms": 2, "count": 2200},
            {"rooms": 3, "count": 3800},
            {"rooms": 4, "count": 1500},
            {"rooms": 5, "count": 200}
        ],
        "price_distribution": [
            {"range": "50万以下", "count": 800},
            {"range": "50-80万", "count": 1500},
            {"range": "80-120万", "count": 2200},
            {"range": "120-200万", "count": 2500},
            {"range": "200-300万", "count": 900},
            {"range": "300万以上", "count": 300}
        ],
        "area_distribution": [
            {"range": "60㎡以下", "count": 1200},
            {"range": "60-90㎡", "count": 2800},
            {"range": "90-120㎡", "count": 2400},
            {"range": "120-150㎡", "count": 1200},
            {"range": "150㎡以上", "count": 600}
        ],
        "top_communities": [
            {"name": "龙湖春森彼岸", "count": 180, "avg_price": 15800},
            {"name": "招商江湾城", "count": 150, "avg_price": 14200}
        ],
        "top_biz_circles": [
            {"name": "观音桥", "count": 1200, "avg_price": 15200},
            {"name": "照母山", "count": 980, "avg_price": 16800}
        ]
    }
}
```

> 相比旧版新增：`biz_circle_count`、`top_biz_circles`

---

### 4. 价格区间分布 — `GET /api/stats/price-distribution`

**响应**：
```json
{
    "code": 200,
    "data": {
        "unit_price_bins": [
            {"range": "5000以下", "count": 3200},
            {"range": "5000-8000", "count": 8500},
            {"range": "8000-12000", "count": 15000},
            {"range": "12000-18000", "count": 16000},
            {"range": "18000-25000", "count": 7000},
            {"range": "25000以上", "count": 2600}
        ],
        "total_price_bins": [
            {"range": "50万以下", "count": 5000},
            {"range": "50-80万", "count": 9000},
            {"range": "80-120万", "count": 14000},
            {"range": "120-200万", "count": 15000},
            {"range": "200-300万", "count": 6000},
            {"range": "300万以上", "count": 3300}
        ]
    }
}
```

---

### 5. 户型分布 — `GET /api/stats/layout-distribution`

**响应**：
```json
{
    "code": 200,
    "data": {
        "rooms_distribution": [
            {"rooms": 1, "count": 3000},
            {"rooms": 2, "count": 12000},
            {"rooms": 3, "count": 25000},
            {"rooms": 4, "count": 9000},
            {"rooms": 5, "count": 2300}
        ],
        "avg_price_by_rooms": [
            {"rooms": 1, "avg_unit_price": 16500},
            {"rooms": 2, "avg_unit_price": 14200},
            {"rooms": 3, "avg_unit_price": 12800},
            {"rooms": 4, "avg_unit_price": 13500},
            {"rooms": 5, "avg_unit_price": 15200}
        ]
    }
}
```

---

### 6. 面积区间分布 — `GET /api/stats/area-distribution`

**响应**：
```json
{
    "code": 200,
    "data": {
        "bins": [
            {"range": "60㎡以下", "count": 6000},
            {"range": "60-90㎡", "count": 18000},
            {"range": "90-120㎡", "count": 15000},
            {"range": "120-150㎡", "count": 8000},
            {"range": "150㎡以上", "count": 5300}
        ]
    }
}
```

---

### 7. 预测分析结果 — `GET /api/analysis/prediction`

**响应**：
```json
{
    "code": 200,
    "data": {
        "model": "随机森林",
        "r2_score": 0.8234,
        "mae": 1520.50,
        "feature_importance": [
            {"feature": "面积", "importance": 0.35},
            {"feature": "区县/地段", "importance": 0.28},
            {"feature": "房龄", "importance": 0.15},
            {"feature": "楼层", "importance": 0.10},
            {"feature": "朝向", "importance": 0.07},
            {"feature": "装修", "importance": 0.05}
        ],
        "model_accuracy": "MAE=1520元/㎡，R²=0.82，平均预测误差约11.5%"
    }
}
```

---

### 8. 聚类分析结果 — `GET /api/analysis/clustering`

```json
{
    "code": 200,
    "data": {
        "cluster_count": 4,
        "clusters": [
            {
                "id": 0,
                "name": "刚需低价型",
                "count": 18000,
                "avg_unit_price": 7200,
                "avg_area": 75.5,
                "avg_rooms": 2.1,
                "typical_districts": ["巴南区", "大渡口区", "北碚区"],
                "typical_biz_circles": ["鱼洞", "九宫庙", "北碚老城"],
                "description": "小面积、低总价、远郊区域，适合首次置业"
            },
            {
                "id": 1,
                "name": "改善中价型",
                "count": 20000,
                "avg_unit_price": 12000,
                "avg_area": 105.0,
                "avg_rooms": 2.9,
                "typical_districts": ["渝北区", "沙坪坝区", "南岸区"],
                "typical_biz_circles": ["照母山", "大学城", "南坪"],
                "description": "中等面积、中等价格、近郊成熟区域"
            },
            {
                "id": 2,
                "name": "高端高价型",
                "count": 8000,
                "avg_unit_price": 22000,
                "avg_area": 145.0,
                "avg_rooms": 3.8,
                "typical_districts": ["江北区", "渝中区"],
                "typical_biz_circles": ["江北嘴", "解放碑"],
                "description": "大面积、高总价、核心地段"
            },
            {
                "id": 3,
                "name": "投资紧凑型",
                "count": 6300,
                "avg_unit_price": 15500,
                "avg_area": 55.0,
                "avg_rooms": 1.5,
                "typical_districts": ["江北区", "渝中区"],
                "typical_biz_circles": ["观音桥", "解放碑"],
                "description": "小户型、高单价、核心区，适合投资"
            }
        ]
    }
}
```

> 每个聚类新增 `typical_biz_circles` 字段

---

### 9. 关联规则结果 — `GET /api/analysis/rules`

```json
{
    "code": 200,
    "data": {
        "top_rules": [
            {
                "antecedent": ["精装", "南朝向", "中层"],
                "consequent": ["高单价"],
                "confidence": 0.72,
                "lift": 2.3,
                "support": 0.12
            },
            {
                "antecedent": ["毛坯", "北朝向"],
                "consequent": ["低单价"],
                "confidence": 0.65,
                "lift": 1.9,
                "support": 0.08
            }
        ]
    }
}
```

> 每条规则新增 `support` 字段

---

### 10. 增量数据更新 — `POST /api/update`

**用途**：手动触发一次增量数据更新。答辩时演示系统能更新数据。

**请求**：无参数

**响应**：
```json
{
    "code": 200,
    "message": "增量更新完成",
    "data": {
        "new_count": 156,
        "updated_count": 23,
        "total_before": 52100,
        "total_after": 52256,
        "update_time": "2026-07-06 10:30:00",
        "sources_updated": {
            "lianjia": {"new": 120, "updated": 18},
            "anjuke": {"new": 36, "updated": 5}
        }
    }
}
```

| 字段 | 说明 |
|------|------|
| `new_count` | 本次新增房源数 |
| `updated_count` | 本次更新的房源数（价格变动等） |
| `total_before` | 更新前总数 |
| `total_after` | 更新后总数 |
| `sources_updated` | 按数据源分别统计 |
| `update_time` | 更新时间 |

---

## 变更记录

| 日期 | 变更内容 | 原因 |
|------|---------|------|
| 6/9 | 房源对象新增 `biz_circle`、`source`、`address`、`lng`、`lat`、`followers`、`crawl_time` | 对齐数据源分析笔记的23个字段 |
| 6/9 | overview 新增 `by_source` 统计 | 区分链家/安居客数据占比 |
| 6/9 | district 详情新增 `top_biz_circles` | 商圈维度的可视化展示 |
| 6/9 | 聚类结果新增 `typical_biz_circles` | 每个聚类类别的典型商圈 |
| 6/9 | 关联规则新增 `support` | 支撑度指标，分析更完整 |
| 6/9 | 新增 `POST /api/update` 接口 | 增量更新功能，答辩演示用 |
| 6/9 | 筛选参数新增 `biz_circle`、`floor_type`、`source` | 数据源笔记中确认的筛选维度 |
