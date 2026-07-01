# 房源图片模块 — 交付成员C（最终版）

> 2026年7月1日 | 改动：胡霖 | 接收：成员C

---

## 一、改动概述

新增房源图片功能：数据库存图片URL、API返回图片数组、爬虫从链家/安居客抓真实照片。

---

## 二、数据库变更

`houses` 表新增 `image_urls TEXT` 列，存 JSON 数组：

```sql
ALTER TABLE houses ADD COLUMN image_urls TEXT;
```

存储格式：
```json
["https://image1.ljcdn.com/110000-inspection/pc1_xxx.jpg", ...]
```

**当前数据状态**：

| 来源 | 总数 | 真实图片 | 占位图 |
|------|------|---------|--------|
| lianjia | 526 | 509 (97%) | 0 |
| anjuke | 10,133 | 155 | 0 |
| augmented | 44,320 | 0 | 44,320 |

---

## 三、API 变更

### 1. 返回字段新增 `image_urls`

`GET /api/houses` 和 `GET /api/houses/{id}` 每条房源增加 `image_urls: ["url1","url2",...]`

### 2. 新增占位图接口

```
GET /api/images/placeholder/{house_id}/{index}
```

返回 SVG（Content-Type: image/svg+xml），含真实房源信息。index: 0=蓝 1=紫 2=绿。

### 3. 新增筛选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `has_coords` | bool | 仅返回有经纬度的房源（地图模式），13,199条 |
| `has_images` | bool | 仅返回有真实CDN图片的房源，591条 |

可与 `source`、`district` 等自由组合。

---

## 四、新增图片爬虫

文件：`crawler/scrape_images.py`

- 从链家移动站 + 安居客桌面站详情页提取真实照片
- 单线程慢爬（3-8秒/条），直连不用代理
- 支持断点续传
- Cookie 已内置在文件顶部（过期后从浏览器重取）

用法：
```bash
python crawler/scrape_images.py --source lianjia          # 链家全量
python crawler/scrape_images.py --source anjuke           # 安居客全量
python crawler/scrape_images.py --source lianjia --limit 5 --dry-run  # 测试
```

---

## 五、涉及文件

| 文件 | 改动类型 |
|------|---------|
| `backend/database.py` | 修改 — Decimal→float 转换器 |
| `backend/schemas.py` | 修改 — HouseItem 新增 image_urls |
| `backend/routers/houses.py` | 修改 — 查询含 image_urls，新增占位图接口，新增 has_coords/has_images 参数 |
| `backend/main.py` | 修改 — json_encoders Decimal 兜底 |
| `crawler/scrape_images.py` | **新文件** — 图片爬虫 |
| `docs/API接口文档_v2_实测版.md` | 新文件 — 实测 API 文档 |
| `docs/素材_图片模块_交付成员C.md` | 本文件 |

---

## 六、Kotlin 端对接

```kotlin
data class HouseItem(
    // ... 原有字段不变
    val image_urls: List<String>?  // 新增：图片URL数组
)

// 请求示例
api.getHouses(hasImages = true)      // 有真实图片
api.getHouses(hasCoords = true)      // 地图模式（有经纬度）
api.getHouses(source = "lianjia", hasImages = true)  // 链家有图

// URL 拼接
fun resolveUrl(raw: String, baseUrl: String): String {
    return if (raw.startsWith("http")) raw           // CDN地址直接用
    else baseUrl.trimEnd('/') + "/" + raw.trimStart('/')  // 占位图拼BASE_URL
}
```

---

## 七、附：Decimal 类型修复

MySQL DECIMAL → pymysql Decimal → FastAPI JSON 字符串 的问题已修复。

修复前：`"total_price": "39.85"`（字符串）
修复后：`"total_price": 39.85`（数字）

影响所有数值字段。Kotlin `Double`/`Int` 现在能正确解析。
