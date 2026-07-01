# 房源图片模块 — 交付成员C

> 2026年7月1日 | 改动：胡霖 | 接收：成员C

---

## 一、改了什么

### 1. 数据库新增字段

`houses` 表新增 `image_urls` 列（TEXT，存 JSON 数组）：

```sql
ALTER TABLE houses ADD COLUMN image_urls TEXT;
```

存储格式：`["https://image1.ljcdn.com/...", "https://image1.ljcdn.com/...", ...]`

**当前数据分布**：

| 来源 | 总数 | 有图片 | 图片类型 |
|------|------|--------|----------|
| lianjia | 526 | 爬取 | 真实房源照片 |
| anjuke | 10,133 | 爬取 | 真实房源照片 |
| augmented | 44,320 | 44,320 (100%) | SVG 占位图 |

### 2. API 新增字段

**`GET /api/houses` 和 `GET /api/houses/{id}`** 返回中增加了 `image_urls`：

```json
{
  "id": 275109,
  "title": "万中后门口3房...",
  "total_price": 39.85,
  "image_urls": [
    "/api/images/placeholder/275109/0",
    "/api/images/placeholder/275109/1",
    "/api/images/placeholder/275109/2"
  ]
}
```

爬取真实图片后会是完整 CDN URL：
```json
{
  "image_urls": [
    "https://image1.ljcdn.com/110000-inspection/pc1_UqiPfvdg6.jpg",
    "https://image1.ljcdn.com/110000-inspection/pc0_QznXYz3Yb.jpg",
    "https://image1.ljcdn.com/hdic-resblock/4d68ac4c-a21b-4670-82c6-ed18c74bdfc1.jpg"
  ]
}
```

### 3. 新增占位图片接口

```
GET /api/images/placeholder/{house_id}/{index}
```

- 无需鉴权
- 返回 SVG 图片（Content-Type: `image/svg+xml`）
- `index`: 0=蓝(客厅), 1=紫(卧室), 2=绿(外观)
- SVG 内含真实房源信息（小区名、户型、面积、价格）

### 4. 新增图片爬虫脚本

文件：`crawler/scrape_images.py`

功能：
- 从链家/安居客详情页爬取真实房源照片
- 单线程慢爬，不用代理
- 支持断点续传（已有图片的自动跳过）
- 需要浏览器 Cookie（已内置在文件顶部）

---

## 二、改动涉及的文件

| 文件 | 改动 |
|------|------|
| `backend/database.py` | Decimal→float 类型转换器，`_convert_decimals` 辅助函数 |
| `backend/schemas.py` | `HouseItem` 新增 `image_urls: Optional[Any]` |
| `backend/routers/houses.py` | 查询加入 `image_urls`，新增占位图接口，新增 `_parse_image_urls` |
| `backend/main.py` | `json_encoders={Decimal: float}` 兜底 |
| `crawler/scrape_images.py` | **新文件** — 图片爬虫（含 Cookie 配置） |
| `docs/API接口文档_v2_实测版.md` | **新文件** — 全部接口实测文档 |
| `docs/素材_图片模块_交付成员C.md` | **本文件** |

---

## 三、Kotlin 端对接

```kotlin
data class HouseItem(
    val id: Int,
    val title: String?,
    // ... 其他字段不变
    val image_urls: List<String>?  // 新增
)
```

完整 URL 拼接：
```kotlin
// 占位图（所有 augmented 数据 + 未爬取的房源）
"${BASE_URL}api/images/placeholder/$houseId/$index"

// 真实图片（链家/安居客爬取后）
image_urls[index]  // 直接使用，已是完整 CDN URL
```

加载示例（Glide/Coil）：
```kotlin
// 如果图片以 /api/ 开头，拼 BASE_URL；否则直接用（CDN 地址）
fun resolveImageUrl(raw: String, baseUrl: String): String {
    return if (raw.startsWith("/api/")) baseUrl + raw.dropWhile { it == '/' }
    else raw
}
```

---

## 四、运行图片爬虫

### 前置条件

Cookie 已内置在 `crawler/scrape_images.py` 第 49-50 行。过期后从浏览器重新复制粘贴。

### 命令

```bash
cd D:\SWU\大二下\学年设计\chongqing-house-analysis

# 链家（526条，约40分钟）
python crawler/scrape_images.py --source lianjia

# 安居客（先试100条）
python crawler/scrape_images.py --source anjuke --limit 100

# 测试模式（不写数据库）
python crawler/scrape_images.py --source lianjia --limit 5 --dry-run

# 查看进度
python -c "from backend.database import query; r=query(\"SELECT source, COUNT(*) as cnt FROM houses WHERE image_urls IS NOT NULL AND image_urls != '' GROUP BY source\"); [print(f'{x[\"source\"]}: {x[\"cnt\"]}') for x in r]"
```

### 注意事项

- 必须后端正在运行（爬虫直接写数据库）
- 爬虫单线程，每个房源间隔 3-8 秒
- 触发验证码自动等 30-60 秒
- Ctrl+C 中断后重跑即可续传
- Cookie 有效约几小时，过期需更新

---

## 五、附：Decimal 类型修复

今天同时修复了 MySQL DECIMAL 字段序列化为字符串的问题。之前返回值：

```json
{ "total_price": "39.85", "area": "87.80" }   // 字符串 ❌
```

修复后：

```json
{ "total_price": 39.85, "area": 87.80 }        // 数字 ✅
```

影响所有接口的数值字段（价格、面积等）。Kotlin `Double` 类型现在能正确解析。
