# API 接口文档 v2（实测版）

> **后端：胡霖（FastAPI）| App：解金明（Kotlin + Retrofit）**  
> **更新：2026年7月1日** — 全部接口实测通过，JSON 数值类型已修复（Decimal → float）

---

## 重要：v2 vs v1 变更

| 变更 | 说明 |
|------|------|
| 🔧 **数值类型修复** | 所有价格/面积字段现在返回 `float`，不再是 `string`（之前 `"39.85"` → 现在 `39.85`） |
| 📊 **预测接口结构** | `data` 下包含 `models` / `feature_importance` / `charts` / `created_at`，与 v1 文档不同 |
| 📊 **聚类接口结构** | `data` 下包含 `clustering` / `charts` / `created_at`，cluster_stats 字段与 v1 不同 |
| 📊 **规则接口** | 包含 `association`（文本结论 + 规则数）和 `district_analysis`（TOP20 区县数据） |
| 🆕 **新增 quick-stats** | `/api/analysis/quick-stats` 快速统计摘要（实时计算） |
| 🆕 **update/status** | 返回 `last_crawl_log` 和 `last_db_update`，结构有变化 |
| 🆕 **update/history** | 返回爬取历史记录数组 |

---

## 一、服务器地址

| 场景 | 地址 |
|------|------|
| **公网（ngrok）** | `https://stallion-pointy-ensure.ngrok-free.dev` |
| Android 模拟器 | `http://10.0.2.2:8000` |
| 真机同 WiFi | `http://电脑局域网IP:8000` |
| 本机测试 | `http://localhost:8000` |
| Swagger 文档 | `http://localhost:8000/docs` |

---

## 二、统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "total": 54979
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | `Int` | 200=成功，404=无数据，500=服务器错误 |
| `message` | `String` | 提示信息 |
| `data` | `T?` | 实际数据，可能是对象、数组或 null |
| `total` | `Int?` | 列表接口的总数（用于分页），非列表接口为 null |

### Kotlin 数据类

```kotlin
data class ApiResponse<T>(
    val code: Int,
    val message: String,
    val data: T?,
    val total: Int? = null
)
```

---

## 三、接口速查表（共 13 个）

| # | 方法 | 路径 | 用途 | App 页面 |
|---|------|------|------|----------|
| 1 | GET | `/api/stats/overview` | 首页数据总览 | 首页卡片 + 区县列表 |
| 2 | GET | `/api/houses` | 房源搜索（筛选+分页） | 搜索/筛选页 |
| 3 | GET | `/api/houses/{id}` | 房源详情 | 房源详情页 |
| 4 | GET | `/api/stats/district/{name}` | 区县详细统计 | 区县详情页 |
| 5 | GET | `/api/stats/price-distribution` | 价格区间分布 | 分析/图表页 |
| 6 | GET | `/api/stats/layout-distribution` | 户型分布 | 分析/图表页 |
| 7 | GET | `/api/stats/area-distribution` | 面积区间分布 | 分析/图表页 |
| 8 | GET | `/api/analysis/prediction` | 🔥 房价预测模型 | AI 预测页 |
| 9 | GET | `/api/analysis/clustering` | 聚类分析 | 分析页 |
| 10 | GET | `/api/analysis/rules` | 关联规则结果 | 分析页 |
| 11 | GET | `/api/analysis/quick-stats` | 快速统计摘要 | 分析页 |
| 12 | POST | `/api/update` | 触发增量更新 | 设置页 |
| 13 | GET | `/api/update/status` | 更新状态 | 设置页 |
| 14 | GET | `/api/update/history` | 更新历史 | 设置页 |

---

## 四、接口详细定义（实测响应）

### 1. 数据总览 — `GET /api/stats/overview`

**用途**：App 首页顶部卡片 + 各区县排名列表

**实测响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_houses": 54979,
    "avg_unit_price": 8276.11,
    "avg_total_price": 81.71,
    "max_unit_price": 174824.45,
    "min_unit_price": 0.0,
    "district_count": 39,
    "update_time": "2026-06-28 00:55:43",
    "by_source": {
      "anjuke": 10133,
      "augmented": 44320,
      "lianjia": 526
    },
    "by_district": [
      {
        "district": "两江新区",
        "count": 15986,
        "avg_unit_price": 10176.08,
        "avg_total_price": 98.82
      }
    ]
  },
  "total": null
}
```

**Kotlin 数据类**：
```kotlin
data class OverviewData(
    val total_houses: Int,
    val avg_unit_price: Double,
    val avg_total_price: Double,
    val max_unit_price: Double,
    val min_unit_price: Double,
    val district_count: Int,
    val update_time: String,
    val by_source: Map<String, Int>,
    val by_district: List<DistrictStat>
)

data class DistrictStat(
    val district: String,
    val count: Int,
    val avg_unit_price: Double,
    val avg_total_price: Double
)
```

---

### 2. 房源列表 — `GET /api/houses`

**请求参数**（全部可选）：

| 参数 | 类型 | 示例 | 说明 |
|------|------|------|------|
| `district` | String | `两江新区` | 区县筛选 |
| `min_price` | Double | `80` | 最低总价（万） |
| `max_price` | Double | `200` | 最高总价（万） |
| `min_area` | Double | `60` | 最小面积（㎡） |
| `max_area` | Double | `120` | 最大面积（㎡） |
| `rooms` | Int | `3` | 户型-室 |
| `floor_type` | String | `中层` | 低层/中层/高层 |
| `decoration` | String | `精装` | 装修 |
| `orientation` | String | `南` | 朝向 |
| `source` | String | `lianjia` | lianjia / anjuke |
| `has_coords` | Bool | `true` | 仅返回有经纬度的房源（地图模式），13,199条 |
| `has_images` | Bool | `true` | 仅返回有真实CDN图片的房源，591条 |
| `page` | Int | `1` | 页码（默认1） |
| `page_size` | Int | `20` | 每页条数（默认20，最大50） |

**实测响应**（`GET /api/houses?page=1&page_size=2`）：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 275109,
      "title": "万中后门口3房，5楼，商圈成熟，户型视野好，免费停车，看房议",
      "district": "万州区",
      "community": "学府移民小区",
      "address": "五桥",
      "total_price": 39.85,
      "unit_price": 4538.19,
      "area": 87.8,
      "layout": "3室1厅",
      "rooms": 3,
      "halls": 1,
      "bathrooms": 2,
      "floor_desc": "",
      "floor_type": "",
      "total_floors": 0,
      "orientation": "南",
      "decoration": "",
      "build_year": 0,
      "lng": 0.0,
      "lat": 0.0,
      "source": "anjuke"
    }
  ],
  "total": 54979
}
```

> ⚠️ `total` 是**去筛选条件后**的总数，用于计算总页数 = `ceil(total / page_size)`

**Kotlin 数据类**：
```kotlin
data class HouseItem(
    val id: Int,
    val title: String?,
    val district: String?,
    val community: String?,
    val address: String?,
    val total_price: Double?,
    val unit_price: Double?,
    val area: Double?,
    val layout: String?,
    val rooms: Int?,
    val halls: Int?,
    val bathrooms: Int?,
    val floor_desc: String?,
    val floor_type: String?,
    val total_floors: Int?,
    val orientation: String?,
    val decoration: String?,
    val build_year: Int?,
    val lng: Double?,
    val lat: Double?,
    val source: String?
)
```

**Retrofit 示例**：
```kotlin
interface HouseApi {
    @GET("api/houses")
    suspend fun getHouses(
        @Query("district") district: String? = null,
        @Query("min_price") minPrice: Double? = null,
        @Query("max_price") maxPrice: Double? = null,
        @Query("min_area") minArea: Double? = null,
        @Query("max_area") maxArea: Double? = null,
        @Query("rooms") rooms: Int? = null,
        @Query("floor_type") floorType: String? = null,
        @Query("decoration") decoration: String? = null,
        @Query("orientation") orientation: String? = null,
        @Query("source") source: String? = null,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): ApiResponse<List<HouseItem>>
}
```

---

### 3. 房源详情 — `GET /api/houses/{id}`

**实测响应**（`GET /api/houses/275109`）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 275109,
    "title": "万中后门口3房，5楼，商圈成熟，户型视野好，免费停车，看房议",
    "district": "万州区",
    "community": "学府移民小区",
    "address": "五桥",
    "total_price": 39.85,
    "unit_price": 4538.19,
    "area": 87.8,
    "layout": "3室1厅",
    "rooms": 3,
    "halls": 1,
    "bathrooms": 2,
    "floor_desc": "",
    "floor_type": "",
    "total_floors": 0,
    "orientation": "南",
    "decoration": "",
    "build_year": 0,
    "lng": 0.0,
    "lat": 0.0,
    "source": "anjuke"
  },
  "total": null
}
```
> 数据模型同 `HouseItem`。total 为 null 是正常的（非列表接口）。

---

### 4. 区县详细统计 — `GET /api/stats/district/{name}`

**实测响应**（`GET /api/stats/district/两江新区`）：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "district": "两江新区",
    "house_count": 15986,
    "avg_unit_price": 10176.08,
    "avg_total_price": 98.82,
    "avg_area": 97.05,
    "max_price": 991.05,
    "min_price": 0.1,
    "decoration_distribution": [
      {"type": "精装修", "count": 1280},
      {"type": "精装", "count": 351},
      {"type": "毛坯", "count": 217}
    ],
    "layout_distribution": [
      {"rooms": 1, "count": 824},
      {"rooms": 2, "count": 4032},
      {"rooms": 3, "count": 9195}
    ],
    "price_distribution": [
      {"range": "50万以下", "count": 3527},
      {"range": "50-80万", "count": 3563},
      {"range": "80-120万", "count": 4128}
    ],
    "area_distribution": [
      {"range": "60㎡以下", "count": 2460},
      {"range": "60-90㎡", "count": 4818},
      {"range": "90-120㎡", "count": 4619}
    ],
    "top_communities": [
      {"name": "金辉中央铭著D区", "count": 48, "avg_price": 13600.0}
    ]
  },
  "total": null
}
```

**Kotlin**：
```kotlin
data class DistrictDetail(
    val district: String,
    val house_count: Int,
    val avg_unit_price: Double,
    val avg_total_price: Double,
    val avg_area: Double,
    val max_price: Double,
    val min_price: Double,
    val decoration_distribution: List<TypeCount>,
    val layout_distribution: List<RoomCount>,
    val price_distribution: List<RangeCount>,
    val area_distribution: List<RangeCount>,
    val top_communities: List<CommunityStat>
)
data class TypeCount(val type: String, val count: Int)
data class RoomCount(val rooms: Int, val count: Int)
data class RangeCount(val range: String, val count: Int)
data class CommunityStat(val name: String, val count: Int, val avg_price: Double)
```

---

### 5. 价格分布 — `GET /api/stats/price-distribution`

```json
{
  "code": 200,
  "data": {
    "unit_price_bins": [
      {"range": "5000以下", "count": 15651},
      {"range": "5000-8000", "count": 15019},
      {"range": "8000-12000", "count": 13263},
      {"range": "12000-18000", "count": 6870},
      {"range": "18000-25000", "count": 2066},
      {"range": "25000以上", "count": 1186}
    ],
    "total_price_bins": [
      {"range": "50万以下", "count": 20658},
      {"range": "50-80万", "count": 12552},
      {"range": "80-120万", "count": 10923},
      {"range": "120-200万", "count": 7626},
      {"range": "200-300万", "count": 2211},
      {"range": "300万以上", "count": 1009}
    ]
  }
}
```

---

### 6. 户型分布 — `GET /api/stats/layout-distribution`

```json
{
  "code": 200,
  "data": {
    "rooms_distribution": [
      {"rooms": 1, "count": 2178},
      {"rooms": 2, "count": 10193},
      {"rooms": 3, "count": 28180},
      {"rooms": 4, "count": 8896},
      {"rooms": 5, "count": 857}
    ],
    "avg_price_by_rooms": [
      {"rooms": 1, "avg_unit_price": 9048.0},
      {"rooms": 2, "avg_unit_price": 8965.0},
      {"rooms": 3, "avg_unit_price": 8667.0},
      {"rooms": 4, "avg_unit_price": 8338.0},
      {"rooms": 5, "avg_unit_price": 8832.0}
    ]
  }
}
```

---

### 7. 面积分布 — `GET /api/stats/area-distribution`

```json
{
  "code": 200,
  "data": {
    "bins": [
      {"range": "60㎡以下", "count": 9477},
      {"range": "60-90㎡", "count": 13477},
      {"range": "90-120㎡", "count": 18187},
      {"range": "120-150㎡", "count": 9662},
      {"range": "150㎡以上", "count": 3302}
    ]
  }
}
```

---

### 8. 🔥 房价预测 — `GET /api/analysis/prediction`

**实测响应结构**（⚠️ 与 v1 文档不同）：
```json
{
  "code": 200,
  "data": {
    "charts": {
      "prediction": ["prediction_RandomForest_total.png", "prediction_GradientBoosting_total.png", ...],
      "feature_importance": ["feature_importance_compare_总价.png", ...],
      "district": ["district_price_ranking.png", ...]
    },
    "models": {
      "RandomForest_total": {
        "unit": "万",
        "target": "total_price(万)",
        "model_type": "RandomForest",
        "test_r2": 0.488,
        "test_mae": 32.26,
        "test_rmse": 54.05,
        "train_r2": 0.7092,
        "cv_r2_mean": 0.4985,
        "test_samples": 9403,
        "train_samples": 37610,
        "features": ["area", "rooms", "halls", ...]
      },
      "RandomForest_unit": { ... },
      "GradientBoosting_total": { ... },
      "GradientBoosting_unit": { ... }
    },
    "feature_importance": {
      "RandomForest_total": [
        {"rank": 1, "feature": "area", "feature_cn": "面积", "importance": 0.376},
        {"rank": 2, "feature": "community_encoded", "feature_cn": "小区(均价编码)", "importance": 0.264}
      ],
      "RandomForest_unit": [...],
      "GradientBoosting_total": [...],
      "GradientBoosting_unit": [...]
    },
    "created_at": "2026-07-01 09:08:47"
  }
}
```

**Kotlin（只取 Android 需要的核心字段）**：
```kotlin
data class PredictionData(
    val models: Map<String, ModelInfo>,
    val feature_importance: Map<String, List<FeatureRank>>,
    val created_at: String?
)

data class ModelInfo(
    val unit: String?,
    val target: String?,
    val model_type: String?,
    val test_r2: Double?,
    val test_mae: Double?,
    val test_rmse: Double?,
    val cv_r2_mean: Double?
)

data class FeatureRank(
    val rank: Int,
    val feature: String,
    val feature_cn: String,
    val importance: Double
)
```

---

### 9. 聚类分析 — `GET /api/analysis/clustering`

**实测响应结构**（⚠️ 与 v1 文档不同）：
```json
{
  "code": 200,
  "data": {
    "clustering": {
      "n_clusters": 5,
      "silhouette_score": 0.122,
      "inertia_": 460434.34,
      "cluster_stats": [
        {
          "cluster_id": 0,
          "count": 16678,
          "pct": 35.5,
          "avg_unit_price": 6383.0,
          "avg_total_price": 69.2,
          "avg_area": 107.9,
          "avg_rooms": 3.3,
          "avg_house_age": 46.0,
          "dominant_floor": "",
          "dominant_decoration": "",
          "top_districts": {"两江新区": 4620, "忠县": 1885, "丰都县": 1602}
        }
      ]
    },
    "charts": {
      "pca": "clustering_pca.png",
      "elbow": "clustering_elbow.png",
      "radar": "clustering_radar.png",
      "district_distribution": "clustering_district_distribution.png"
    },
    "created_at": "2026-07-01 09:08:47"
  }
}
```

**Kotlin**：
```kotlin
data class ClusteringData(
    val clustering: ClusteringResult?,
    val created_at: String?
)

data class ClusteringResult(
    val n_clusters: Int,
    val silhouette_score: Double,
    val cluster_stats: List<ClusterStat>
)

data class ClusterStat(
    val cluster_id: Int,
    val count: Int,
    val pct: Double,
    val avg_unit_price: Double,
    val avg_total_price: Double,
    val avg_area: Double,
    val avg_rooms: Double,
    val avg_house_age: Double,
    val dominant_floor: String?,
    val dominant_decoration: String?,
    val top_districts: Map<String, Int>?
)
```

---

### 10. 关联规则 — `GET /api/analysis/rules`

```json
{
  "code": 200,
  "data": {
    "association": {
      "conclusions": "## 重庆二手房关联规则分析结论\n\n### 核心发现\n...",
      "total_rules": 50
    },
    "district_analysis": {
      "chart": "district_price_ranking.png",
      "top20_avg_price": {
        "count": {"两江新区": 15524, "渝中区": 930, ...},
        "avg_unit_price": {"渝中区": 22330.19, "南岸区": 16418.10, ...},
        "avg_total_price": {"渝中区": 239.83, "南岸区": 169.82, ...},
        "avg_area": {"两江新区": 97.05, ...}
      }
    },
    "created_at": "2026-07-01 09:08:47"
  }
}
```

> ⚠️ `conclusions` 是 Markdown 格式文本，App 可直接渲染。`top20_avg_price` 的 key 是区县名，value 是数值。

---

### 11. 快速统计 — `GET /api/analysis/quick-stats`

```json
{
  "code": 200,
  "data": {
    "total_listings": 54979,
    "avg_unit_price": 8276,
    "avg_total_price": 81.7,
    "avg_area": 93.1,
    "avg_build_year": 1732,
    "decoration_distribution": [
      {"name": "精装", "count": 3046},
      {"name": "毛坯", "count": 1765}
    ],
    "floor_distribution": [
      {"name": "高层", "count": 7905},
      {"name": "中层", "count": 7356},
      {"name": "低层", "count": 6653}
    ]
  }
}
```

---

### 12-14. 增量更新

**POST /api/update** — 触发后台增量更新（无请求体）

**GET /api/update/status** — 查询当前状态：
```json
{
  "code": 200,
  "data": {
    "running": false,
    "last_run": null,
    "last_result": null,
    "last_crawl_log": {
      "source": "anjuke",
      "district": "城口县",
      "houses_found": 0,
      "new_added": 0,
      "updated": 0,
      "status": "empty",
      "message": "",
      "crawl_time": "2026-06-21 15:52:08"
    },
    "last_db_update": "2026-06-28 00:55:43",
    "recent_24h": {"new": 0.0, "updated": 0.0}
  }
}
```

**GET /api/update/history** — 爬取历史（数组）：
```json
{
  "code": 200,
  "data": [
    {
      "id": 235,
      "source": "anjuke",
      "district": "城口县",
      "page": 3,
      "houses_found": 0,
      "new_added": 0,
      "updated": 0,
      "status": "empty",
      "message": "",
      "crawl_time": "2026-06-21T15:52:08"
    }
  ],
  "total": 20
}
```

---

## 五、数据注意事项

### 空值字段
以下字段在安居客数据中经常为空/0：
- `floor_desc`, `floor_type`: 大量空字符串
- `total_floors`: 大多为 0
- `decoration`: 大多为空字符串（链家数据较全）
- `build_year`: 大多为 0
- `bathrooms`: 部分为 0
- `lng`, `lat`: **仅 3.7% 房源有坐标**，其余为 `0.0`

App 端应对这些做优雅降级。

### 分页
- 默认 `page_size=20`，最大 50
- 响应 `total` 是筛选后的总数
- 总页数 = `ceil(total / page_size)`

### 错误处理
```kotlin
when (response.code) {
    200 -> // 正常，使用 response.data
    404 -> showEmptyState()  // 无数据
    500 -> showError()       // 服务器错误
}
```

### 数据来源
`by_source` 有三个值：
- `anjuke` — 安居客原始数据
- `lianjia` — 链家原始数据
- `augmented` — 数据增强生成（占大多数）

---

## 六、变更记录

| 日期 | 变更 |
|------|------|
| 7/1 | 新增 `image_urls` 字段、`/api/images/placeholder/{id}/{index}` 占位图接口、`has_coords`/`has_images` 筛选参数 |
| 7/1 | **v2 实测版**：全部接口用真实响应重写；修复 Decimal→float；分析接口结构按实际修正；新增 quick-stats/update-status/update-history |
| 6/12 | v1 初版 |
