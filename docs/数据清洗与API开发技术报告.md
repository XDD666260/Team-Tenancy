# 数据清洗与后端API开发技术报告

> 2026年6月20日 | 学年设计Ⅱ — 重庆二手房分析系统

---

## 一、项目背景

爬虫阶段产出约91K条原始数据，分布在38个安居客CSV + 10个链家CSV + 3个合并文件中。数据存在三类严重问题：

1. **价格损坏**：50.4%的房源 `total_price` 和 `unit_price` 小数点丢失（如 `10812518.0` 应为 `108` 万）
2. **大面积重复**：爬虫翻页逻辑bug导致同一页重复采集12次以上，80K中仅5K+唯一标题
3. **字段缺失**：`lng=0, lat=0`（99.9%），`decoration`/`floor_desc`/`build_year` 几乎全空

本项目完成数据清洗、MySQL入库、FastAPI后端API开发全流程。

---

## 二、数据清洗

### 2.1 处理流程

```
data/raw/*.csv (91,240行)
    │
    ├─ 字段标准化 → 23个标准字段
    ├─ 价格修复    → 标题提取 + /100000 回退
    ├─ 文件分类    → 优先合并文件 > m_主数据 > 链家 > 其它
    ├─ 标题去重    → 同文件内相同标题只保留1条
    ├─ 跨文件去重  → title+community+district 匹配
    └─ 指纹生成    → 入库用唯一指纹
    │
    ▼
data/processed/houses_clean.csv (10,671行)
```

### 2.2 清洗前后对比

| 指标 | 清洗前 | 清洗后 |
|------|--------|--------|
| 总行数 | 91,240 | 10,671 |
| 唯一房源 | ~5,119 (实际) | 10,671 (含跨源) |
| 价格损坏行 | 40,788 (50.4%) | 0 |
| 安居客数据 | 80,948 | 8,276 |
| 链家数据 | 300 | 300 |
| 合并文件补充 | 5,252 | 352 |
| 有坐标(lng>0) | ~300 | 313 |
| 覆盖区县 | 39 | 39 |

### 2.3 价格修复详解

**损坏特征**：爬虫解析列表页时价格小数点丢失，形成"总价整数+单价前缀"的拼接值。

**修复策略**（两级回退）：
1. **标题提取**（优先级最高）：正则匹配 `(\d+\.?\d*)\s*万`，如标题含"108万" → `corrected=108.00`
2. **数学修复**（回退方案）：`total_price / 100000`，误差仅约0.1%
3. **单价重算**：`unit_price = corrected_total_price * 10000 / area`

**修复示例**：
```
原始: total=10812518.00, unit=1253189383.40, area=86.28
标题: "龙湖春森彼岸...108万"
修复: total=108.00万, unit=12518元/㎡
```

### 2.4 去重策略

- **同文件内**：标题完全一致视为重复（爬虫翻页bug导致同一页数据被重复采集12+次）
- **跨文件间**：`title[:80]|community|district|source` 相同视为同一房源
- **数据库层**：`fingerprint UNIQUE INDEX` 作为最后防线

### 2.5 各区县数据分布（TOP 10）

| 区县 | 数据量 |
|------|--------|
| 两江新区 | 2,955 |
| 武隆区 | 633 |
| 永川区 | 461 |
| 云阳县 | 460 |
| 忠县 | 432 |
| 丰都县 | 386 |
| 涪陵区 | 325 |
| 九龙坡区 | 237 |
| 渝中区 | 236 |
| 沙坪坝区 | 230 |

---

## 三、数据库设计

### 3.1 E-R图

```
┌─────────────────────────────────────────────────┐
│                    houses                        │
├─────────────────────────────────────────────────┤
│ PK  id          BIGINT       自增主键            │
│     title       VARCHAR(300) 房源标题            │
│     district    VARCHAR(50)  区县                │
│     community   VARCHAR(100) 小区名称            │
│     address     VARCHAR(300) 详细地址            │
│     total_price DECIMAL(12,2) 总价(万)           │
│     unit_price  DECIMAL(10,2) 单价(元/㎡)        │
│     area        DECIMAL(8,2)  面积(㎡)           │
│     layout      VARCHAR(20)  户型原文             │
│     rooms       INT         室                   │
│     halls       INT         厅                   │
│     bathrooms   INT         卫                   │
│     floor_desc  VARCHAR(50)  楼层描述            │
│     floor_type  VARCHAR(10)  楼层类型(低/中/高)  │
│     total_floors INT        总楼层               │
│     orientation VARCHAR(20)  朝向                │
│     decoration  VARCHAR(20)  装修                │
│     build_year  INT         建成年份             │
│     lng         DECIMAL(10,6) 经度              │
│     lat         DECIMAL(10,6) 纬度              │
│     followers   INT         关注人数             │
│     source      VARCHAR(20)  来源(lianjia/anjuke)│
│     source_id   VARCHAR(100) 原始ID              │
│     fingerprint VARCHAR(64)  去重指纹(UNIQUE)    │
│ UK  fingerprint                                      │
│ IDX district, total_price, unit_price, source, status│
│     status      VARCHAR(20)  状态(on_sale/...)   │
│     first_seen  DATETIME    首次发现             │
│     last_updated DATETIME   最后更新             │
└─────────────────────────────────────────────────┘

┌──────────────────────┐   ┌──────────────────────────┐
│      crawl_log       │   │    analysis_results      │
├──────────────────────┤   ├──────────────────────────┤
│ PK id    INT         │   │ PK id          INT       │
│    source VARCHAR(20)│   │    analysis_type VARCHAR │
│    district          │   │    result_data   JSON    │
│    page   INT        │   │    create_time  DATETIME │
│    houses_found INT  │   └──────────────────────────┘
│    new_added  INT    │
│    updated    INT    │
│    status VARCHAR(20)│
│    message TEXT      │
│    crawl_time        │
└──────────────────────┘
```

### 3.2 入库统计

| 来源 | 数量 | 均价(元/㎡) | 平均总价(万) |
|------|------|-------------|--------------|
| anjuke | 8,276 | 5,903 | 74.3 |
| lianjia | 300 | 7,660 | 77.1 |
| **合计** | **8,576** | — | — |

---

## 四、API接口设计

### 4.1 技术栈

- **框架**: FastAPI (Python)
- **数据库**: MySQL 8.0 + pymysql
- **统一响应格式**: `{code, message, data, total}`
- **跨域**: CORS已配置，支持Android模拟器(10.0.2.2:8000)

### 4.2 接口总览

| # | 方法 | 路径 | 说明 | 状态 |
|---|------|------|------|------|
| 1 | GET | `/api/stats/overview` | 首页数据总览 | ✅ |
| 2 | GET | `/api/houses` | 房源列表(筛选+分页) | ✅ |
| 3 | GET | `/api/houses/{id}` | 房源详情 | ✅ |
| 4 | GET | `/api/stats/district/{name}` | 区县详细统计 | ✅ |
| 5 | GET | `/api/stats/price-distribution` | 全市价格区间分布 | ✅ |
| 6 | GET | `/api/stats/layout-distribution` | 户型分布统计 | ✅ |
| 7 | GET | `/api/stats/area-distribution` | 面积区间分布 | ✅ |
| 8 | GET | `/api/analysis/prediction` | 房价预测分析 | ⏳ |
| 9 | GET | `/api/analysis/clustering` | 聚类分析结果 | ⏳ |
| 10 | GET | `/api/analysis/rules` | 关联规则结果 | ⏳ |
| 11 | GET | `/api/analysis/quick-stats` | 快速统计摘要 | ✅ |
| 12 | POST | `/api/update` | 触发增量更新 | ✅ |
| 13 | GET | `/health` | 健康检查 | ✅ |
| 14 | GET | `/docs` | Swagger文档页 | ✅ |

### 4.3 关键接口测试结果

```
GET /api/stats/overview
→ {total_houses: 8576, district_count: 39, avg_unit_price: 6063.35}

GET /api/houses?district=两江新区&min_price=80&max_price=200&rooms=3
→ {total: 1066, data: [...]}

GET /api/stats/district/渝中区
→ {house_count: 151, avg_unit_price: 10165.39}

GET /api/houses?decoration=精装
→ {total: 350}

GET /api/stats/price-distribution
→ {unit_price_bins: 6级, total_price_bins: 6级}
```

---

## 五、文件清单与部署

### 5.1 新增文件

```
backend/
  data_cleaner.py          # 数据清洗引擎
  main.py                  # FastAPI 应用入口
  database.py              # 数据库连接管理
  schemas.py               # Pydantic 数据模型
  routers/
    __init__.py
    stats.py               # 5个统计接口
    houses.py              # 房源列表+详情接口
    analysis.py            # 分析结果接口+快速统计
    update.py              # 增量更新触发接口
data/
  processed/
    houses_clean.csv       # 清洗后完整数据 (10,671行)
docs/
  openapi_schema.json      # OpenAPI规范文件
  数据清洗与API开发技术报告.md  # 本报告
  后端API交付说明_成员C.md
  Android对接说明_成员B.md
```

### 5.2 启动方式

```bash
cd chongqing-house-analysis

# 1. 初始化数据库（首次运行）
python backend/setup_database.py

# 2. 清洗并导入数据
python backend/data_cleaner.py
python backend/import_csv_to_mysql.py

# 3. 启动API服务
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 访问
# API文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/health
# Android模拟器: http://10.0.2.2:8000
```

### 5.3 已知限制与后续建议

| 问题 | 现状 | 建议 |
|------|------|------|
| 坐标缺失(97.1%) | 仅313条有坐标 | 后续可用高德/百度地图API批量地理编码 |
| 装修/楼层/年代为空 | 爬虫未进详情页 | 配置代理后运行 `anjuke_backfill.py` 补充 |
| 价格50%需修复 | 已通过标题+数学方法修复 | 增量更新时直接从详情页获取精确价格 |
| 分析模块为空 | prediction/clustering/rules 返回404 | 在 `analysis/` 目录补充sklearn分析脚本 |
| 增量更新为手动模式 | POST /api/update 需配合爬虫 | 后续接入 `crawler/update.py` 自动化 |
