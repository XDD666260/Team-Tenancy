# Web 前端技术文档

> 重庆二手房数据分析系统 · 学年设计第36小组 | 2026年7月4日

---

## 一、技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 框架 | Next.js (App Router) | 15.x |
| UI 库 | React | 19.x |
| 语言 | TypeScript | 5.7 |
| 图表 | Recharts | 3.9 |
| 动画 | GSAP + ScrollTrigger | 3.12 |
| 平滑滚动 | Lenis | 1.1 |
| 样式 | Tailwind CSS | 3.4 |
| 部署 | Netlify (静态导出) | — |
| 后端通信 | fetch API (客户端) | — |

---

## 二、项目结构

```
web/
├── next.config.js           # output: "export"（静态导出）
├── netlify.toml             # Netlify 部署配置
├── tailwind.config.js       # 自定义暗色主题
├── tsconfig.json
├── package.json
├── public/                  # 静态资源
└── src/
    ├── app/
    │   ├── layout.tsx        # 全局布局（字体、元数据）
    │   ├── page.tsx          # Landing 落地页
    │   ├── globals.css       # 全局样式 + CSS 变量
    │   └── analysis/
    │       ├── page.tsx      # 数据仪表盘（客户端渲染）
    │       └── district/
    │           └── [name]/
    │               └── page.tsx  # 区县详情页
    ├── components/
    │   ├── Hero/Hero.tsx     # 首页 Hero 区域
    │   ├── SmoothScroll/index.tsx  # 平滑滚动容器
    │   └── Dashboard/
    │       ├── StatsHero.tsx          # KPI 数据带
    │       ├── KpiCards.tsx
    │       ├── PredictionSection.tsx  # 房价预测
    │       ├── ClusteringSection.tsx  # 聚类画像
    │       ├── AssociationSection.tsx # 关联规则
    │       ├── DistrictRanking.tsx    # 区县排名
    │       ├── PriceChart.tsx
    │       ├── SourceChart.tsx
    │       ├── DistrictDetailClient.tsx
    │       ├── ChartTooltip.tsx
    │       └── ChartImageBlock.tsx
    └── lib/
        ├── api.ts            # API 客户端（fetch + fallback）
        └── types.ts          # TypeScript 类型定义
```

---

## 三、数据流架构

```
┌──────────────────────────────────────────────────┐
│                    浏览器                          │
│  ┌─────────────┐    fetch()     ┌──────────────┐ │
│  │ Next.js 静态 │  ◄──────────► │ FastAPI :8000 │ │
│  │ HTML + JS   │   JSON/HTTP    │ 本地 / 云服务器 │ │
│  │ (Netlify)   │               └──────┬───────┘ │
│  └─────────────┘                      │         │
│                                       │ SQL     │
│                                ┌──────┴───────┐ │
│                                │ MySQL :3306  │ │
│                                │ 54,993 条    │ │
│                                └──────────────┘ │
└──────────────────────────────────────────────────┘
```

**关键设计决策：**

1. **静态导出 + 客户端渲染** — `next.config.js` 设 `output: "export"`，Netlify 部署纯静态 HTML。数据通过浏览器端 `useEffect` → `fetch()` 获取，不依赖服务端渲染。

2. **渐进增强** — 后端在线时展示实时数据，后端离线时自动降级到内置 fallback 数据，页面不会白屏。

3. **增量更新天然支持** — 爬虫更新 MySQL → 后端 API 读到新数据 → 用户刷新页面 → 前端 fetch 到最新数据。无需重新构建部署。

---

## 四、页面说明

### 4.1 Landing 落地页 (`/`)

- 纯静态组件，无需 API
- Hero 区域展示项目标题和简介
- 三列数据预览：数据规模、分析模型、覆盖区县
- 链接指向仪表盘

### 4.2 数据仪表盘 (`/analysis`)

**客户端渲染页面**，初始化流程：

```
页面加载 → 骨架屏 → fetch /health（探活）
  → 并行 fetch 4 个 API
  → 更新 state → 渲染图表
  → 失败则使用 FALLBACK 数据
```

| 区块 | 数据来源 | 组件 |
|------|---------|------|
| 页面标题 + 数据总量 | `/api/stats/overview` | 内联 |
| KPI 数据带 | overview | `StatsHero` |
| 房价预测模型 | `/api/analysis/prediction` | `PredictionSection` |
| KMeans 聚类 | `/api/analysis/clustering` | `ClusteringSection` |
| 关联规则 | `/api/analysis/association-rules` | `AssociationSection` |
| 区县排名 | overview.by_district | `DistrictRanking` |

**状态指示灯：**
- ● 绿色 + "已连接后端 API · 数据更新时间：xxx" — 后端在线
- ◉ 橙色 + "后端未连接，展示静态演示数据" — 后端离线

### 4.3 区县详情页 (`/analysis/district/[name]`)

- 静态生成（`generateStaticParams`）+ 客户端数据获取
- 展示：基础统计、装修分布、户型分布、价格分布、面积分布、TOP 10 小区

---

## 五、API 对接

### 前端 → 后端接口

| 接口 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | 探活 + 数据总量 |
| `/api/stats/overview` | GET | KPI 总览 |
| `/api/stats/district/{name}` | GET | 区县详情 |
| `/api/stats/price-distribution` | GET | 全市价格分布 |
| `/api/analysis/prediction` | GET | 预测模型结果 |
| `/api/analysis/clustering` | GET | 聚类分析结果 |
| `/api/analysis/association-rules` | GET | 关联规则结果 |
| `/api/analysis/quick-stats` | GET | 快速统计摘要 |

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | 后端 API 地址 |

本地开发无需设置，生产环境需指向公网可访问的后端地址。

---

## 六、开发与部署

### 本地开发

```bash
cd web
npm install
npm run dev          # http://localhost:3000
```

后端需先启动：`uvicorn backend.main:app --port 8000`

### 生产构建

```bash
npm run build        # 生成 out/ 目录
```

### Netlify 部署

`netlify.toml` 已配置：
- 构建命令：`npm run build`
- 发布目录：`out/`
- SPA 路由重定向：`/* → /index.html`

---

## 七、当前数据状态

| 来源 | 数量 | 说明 |
|------|------|------|
| 安居客爬取 | 12,225 | 38 区县真实爬取，列表页字段 |
| 链家爬取 | 526 | 12 区县真实爬取 |
| 数据增强 | 42,242 | 基于真实分布生成（source='augmented'） |
| **合计** | **54,993** | 覆盖 39 个区县 |

均价约 8,400 元/㎡，总价均值约 84.5 万。有经纬度坐标的约 12,117 条（22%）。

---

## 八、截图清单（供文档使用）

| 编号 | 截图内容 | 操作 |
|------|---------|------|
| 1 | 仪表盘全貌（上） | 浏览器打开 `/analysis`，截取 KPI + 预测模型 |
| 2 | 仪表盘全貌（下） | 继续下滚，截取聚类 + 关联规则 + 区县排名 |
| 3 | Landing 落地页 | 浏览器打开 `/`，截取 Hero + 三列数据 |
| 4 | 后端连接状态指示灯 | 截取页面顶部的绿色/橙色状态条 |
| 5 | 区县详情页 | 浏览器打开 `/analysis/district/渝中区`，截图 |
| 6 | Netlify 部署证明 | 截取浏览器地址栏显示的 Netlify 域名 |
| 7 | API 返回 JSON | 浏览器直接访问 `http://localhost:8000/api/stats/overview` |
