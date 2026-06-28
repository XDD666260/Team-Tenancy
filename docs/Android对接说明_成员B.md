# Android App 后端对接说明 — 成员B（解金明）

> 2026年6月20日 | API已完成，可直接对接

---

## 一、服务器地址

| 场景 | 地址 |
|------|------|
| **🚀 公网地址（推荐）** | **`https://stallion-pointy-ensure.ngrok-free.dev`** |
| Android模拟器 | `http://10.0.2.2:8000` |
| 真机(同一WiFi) | `http://电脑局域网IP:8000` |
| 电脑本机测试 | `http://localhost:8000` |
| API文档页 | `https://stallion-pointy-ensure.ngrok-free.dev/docs` |

> **重要**：公网地址通过 ngrok 隧道暴露，后端服务运行在本地8000端口。Android App 中使用 `BASE_URL = "https://stallion-pointy-ensure.ngrok-free.dev"` 即可在任何网络环境下访问API，无需连接同一WiFi。

**获取电脑IP**（仅局域网场景使用）: 终端执行 `ipconfig`，查看 `无线局域网适配器 WLAN` 的 IPv4 地址。

---

## 二、统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "total": 8576
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 200=成功，404=没数据，500=服务器错误 |
| message | string | 提示信息 |
| data | object/array | 实际返回的数据 |
| total | int | 数据总数（列表接口用） |

**Kotlin数据类建议**:
```kotlin
data class ApiResponse<T>(
    val code: Int,
    val message: String,
    val data: T?,
    val total: Int? = null
)
```

---

## 三、接口速查表

| # | 方法 | 路径 | 用途 | App页面 |
|---|------|------|------|---------|
| 1 | GET | `/api/stats/overview` | 首页数据总览 | 首页卡片+区县列表 |
| 2 | GET | `/api/houses` | 房源搜索列表 | 搜索/筛选页 |
| 3 | GET | `/api/houses/{id}` | 房源详情 | 房源详情页 |
| 4 | GET | `/api/stats/district/{name}` | 区县统计 | 区县详情页 |
| 5 | GET | `/api/stats/price-distribution` | 价格分布 | 分析/图表页 |
| 6 | GET | `/api/stats/layout-distribution` | 户型分布 | 分析/图表页 |
| 7 | GET | `/api/stats/area-distribution` | 面积分布 | 分析/图表页 |
| 8 | GET | `/api/analysis/prediction` | 🔥房价预测 | AI预测页 |
| 9 | GET | `/api/analysis/clustering` | 聚类分析 | 分析页 |
| 10 | GET | `/api/analysis/rules` | 关联规则 | 分析页 |
| 11 | POST | `/api/update` | 触发增量更新 | 设置页 |
| 12 | GET | `/api/update/status` | 更新状态查询 | 设置页 |
| 13 | GET | `/api/update/history` | 更新历史 | 设置页 |

---

## 四、核心接口详细说明

### 接口1：首页数据总览

```
GET /api/stats/overview
```

**响应数据模型**:
```kotlin
data class OverviewData(
    val total_houses: Int,         // 总房源数: 8576
    val avg_unit_price: Double,    // 平均单价: 6063.35
    val avg_total_price: Double,   // 平均总价: 74.35
    val max_unit_price: Double,
    val min_unit_price: Double,
    val district_count: Int,       // 覆盖区县: 39
    val update_time: String,
    val by_source: Map<String, Int>,  // {"anjuke":8276, "lianjia":300}
    val by_district: List<DistrictStat>
)

data class DistrictStat(
    val district: String,          // 区县名
    val count: Int,                // 房源数
    val avg_unit_price: Double,    // 均价
    val avg_total_price: Double    // 平均总价
)
```

---

### 接口2：房源搜索列表（最重要）

```
GET /api/houses?district={区县}&min_price={最低总价万}&max_price={最高总价万}
    &min_area={最小面积}&max_area={最大面积}&rooms={室数}
    &floor_type={楼层类型}&decoration={装修}&orientation={朝向}
    &source={来源}&page={页码}&page_size={每页条数}
```

**所有参数都是可选的**，不传则不做该条件筛选。

**常用请求示例**:

```kotlin
// 1. 查某区县所有房源
"/api/houses?district=两江新区&page=1&page_size=20"

// 2. 组合筛选
"/api/houses?district=两江新区&min_price=80&max_price=200&rooms=3&decoration=精装&page=1"

// 3. 只看链家数据
"/api/houses?source=lianjia&page=1"

// 4. 地图模式(获取全部坐标，page_size设大一点)
"/api/houses?district=两江新区&page_size=200"
```

**房源对象模型**:
```kotlin
data class HouseItem(
    val id: Int,
    val title: String?,           // 标题
    val district: String?,        // 区县
    val community: String?,       // 小区
    val address: String?,         // 地址
    val total_price: Double?,     // 总价(万)
    val unit_price: Double?,      // 单价(元/㎡)
    val area: Double?,            // 面积(㎡)
    val layout: String?,          // 户型原文 e.g."3室2厅2卫"
    val rooms: Int?,              // 室
    val halls: Int?,              // 厅
    val bathrooms: Int?,          // 卫
    val floor_desc: String?,      // 楼层描述原文
    val floor_type: String?,      // 低层/中层/高层
    val total_floors: Int?,       // 总楼层
    val orientation: String?,     // 朝向
    val decoration: String?,      // 装修
    val build_year: Int?,         // 建成年份
    val lng: Double?,             // 经度 (注意:仅3.7%房源有值)
    val lat: Double?,             // 纬度
    val source: String?           // 来源: anjuke/lianjia
)
```

**BASE_URL 配置**:
```kotlin
// 在 RetrofitClient 或 NetworkModule 中设置
object ApiConfig {
    const val BASE_URL = "https://stallion-pointy-ensure.ngrok-free.dev/"
    // 本地开发备选:
    // const val BASE_URL = "http://10.0.2.2:8000/"  // Android模拟器
}
```

**Kotlin Retrofit 示例**:
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
        @Query("page_size") pageSize: Int = 20,
    ): ApiResponse<List<HouseItem>>
}
```

---

### 接口3：房源详情

```
GET /api/houses/{id}
```

传入列表接口返回的 `id` 字段即可获取单条房源完整信息。返回数据模型同 `HouseItem`。

---

### 接口4：区县详细统计

```
GET /api/stats/district/{name}
```

**name**: 区县名（如 `两江新区`、`渝中区`）

**响应包含**:
- 基础统计: house_count, avg_unit_price, avg_total_price, avg_area, max_price, min_price
- `decoration_distribution`: 装修分布 `[{type, count}]`
- `layout_distribution`: 户型分布 `[{rooms, count}]`
- `price_distribution`: 价格区间 `[{range, count}]`
- `area_distribution`: 面积区间 `[{range, count}]`
- `top_communities`: TOP10热门小区 `[{name, count, avg_price}]`

---

### 接口5-7：统计分布

| 接口 | 返回内容 |
|------|---------|
| `/api/stats/price-distribution` | `unit_price_bins`(6级) + `total_price_bins`(6级) |
| `/api/stats/layout-distribution` | `rooms_distribution`(1-9室) + `avg_price_by_rooms` |
| `/api/stats/area-distribution` | `bins`(5级: 60以下~150以上) |

---

### 接口8-10：AI分析

**当前状态**: ✅ 已完成，返回真实分析数据。

```
GET /api/analysis/prediction   → 房价预测模型结果
GET /api/analysis/clustering    → KMeans聚类分析结果
GET /api/analysis/rules         → 区县分析关联结果
```

**预测接口响应示例**:
```json
{
  "code": 200,
  "data": {
    "models": {
      "RandomForest_total": {
        "target": "total_price(万)",
        "test_r2": 0.6917,
        "test_mae": 16.53,
        "test_rmse": 31.05,
        "cv_r2_mean": 0.6938
      }
    },
    "feature_importance": {
      "RandomForest_total": [
        {"rank": 1, "feature_cn": "面积", "importance": 0.558},
        {"rank": 2, "feature_cn": "小区(均价编码)", "importance": 0.291}
      ]
    },
    "created_at": "2026-06-21 15:12:48"
  }
}
```

**聚类接口响应示例**:
```json
{
  "code": 200,
  "data": {
    "clustering": {
      "n_clusters": 5,
      "silhouette_score": 0.1461,
      "cluster_stats": [
        {
          "cluster_id": 0, "count": 1157,
          "avg_unit_price": 7915, "avg_total_price": 51.1,
          "avg_area": 64.6, "avg_rooms": 1.9
        },
        {
          "cluster_id": 1, "count": 2441,
          "avg_unit_price": 9687, "avg_total_price": 90.6,
          "avg_area": 94.1, "avg_rooms": 2.9
        }
      ]
    }
  }
}
```

> 建议App处理：解析 `cluster_stats` 数组展示各聚类特征卡片，解析 `feature_importance` 展示关键影响因素。

---

### 接口11：增量更新

```
POST /api/update          → 触发增量更新（后台执行）
GET  /api/update/status   → 查询更新状态
GET  /api/update/history  → 查询更新历史
```

**POST /api/update 响应**:
```json
{
  "code": 200,
  "message": "增量更新已触发，正在后台执行",
  "data": {
    "running": true,
    "total_before": 8576,
    "update_time": "2026-06-21 15:30:00"
  }
}
```

**GET /api/update/status 响应**:
```json
{
  "code": 200,
  "data": {
    "running": false,
    "last_run": "2026-06-21 15:12:14",
    "last_result": {
      "success": true,
      "new_count": 156,
      "updated_count": 48
    },
    "recent_24h": {"new": 12, "updated": 5}
  }
}
```

> **建议**：App 设置页面增加"刷新数据"按钮，调用 POST /api/update 触发，然后轮询 GET /api/update/status 显示进度。

---

## 五、重要注意事项

### 1. 坐标缺失
- 仅 **3.7%** 房源（313条）有经纬度，其余 `lng=0, lat=0`
- 地图页面需过滤 `lng > 0` 的房源，或仅在地图模式下做此过滤
- 后续会通过地址地理编码补充

### 2. 部分字段可能为空
以下字段在大部分安居客房源中为空字符串或0:
- `floor_desc`, `floor_type`, `total_floors`: ~5%填充率
- `decoration`: ~5%填充率（链家数据齐全）
- `build_year`: ~3%填充率
- `bathrooms`: ~10%填充率

App UI应对空/0值做优雅降级处理。

### 3. 分页
- 默认 `page_size=20`，最大50
- 响应中的 `total` 字段是去筛选条件后的总数，用于计算总页数
- 总页数 = `ceil(total / page_size)`

### 4. 错误处理
```kotlin
when (response.code) {
    200 -> // 正常
    404 -> showEmptyState()  // 无数据
    500 -> showError()       // 服务器错误
}
```

---

## 六、数据总览（供UI设计参考）

| 指标 | 数值 |
|------|------|
| 总房源 | 8,576条 |
| 覆盖区县 | 39个 |
| 平均单价 | 5,964 元/㎡ |
| 平均总价 | 74.4 万 |
| 价格范围 | 5 ~ 888 万 |
| 链家数据 | 300条 |
| 安居客数据 | 8,276条 |
| 有坐标房源 | 313条(3.7%) |
| 房价预测模型 | ✅ 已训练 (R²≈0.70) |
| 聚类分析 | ✅ 已完成 (5类) |

**各区县TOP5**:
| 区县 | 房源数 | 均价(元/㎡) |
|------|--------|-------------|
| 两江新区 | 2,955 | 9,840 |
| 武隆区 | 633 | — |
| 永川区 | 461 | — |
| 云阳县 | 460 | — |
| 忠县 | 432 | — |


