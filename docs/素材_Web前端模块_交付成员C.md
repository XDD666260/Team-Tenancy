# Web 前端模块 — 交付成员C（最终版）

> 2026年7月4日 | 改动：胡霖 | 接收：成员C（王宇）

---

## 一、模块概述

基于 Next.js 15 + React 19 + TypeScript + Recharts 构建的重庆二手房数据可视化仪表盘，支持 Netlify 静态部署和本地开发两种模式。**前端通过客户端 fetch 直连后端 FastAPI，实现数据实时展示和增量更新。**

| 项目 | 说明 |
|------|------|
| 框架 | Next.js 15 App Router + React 19 |
| 图表库 | Recharts 3.9（交互式图表） |
| 动画 | GSAP + ScrollTrigger（滚动入场动画） |
| 样式 | Tailwind CSS 3.4 + 自定义暗色主题 |
| 部署 | Netlify 静态导出（output: export） |
| 代码位置 | `web/` |

---

## 二、页面结构

```
/                          → Landing 落地页（Hero + 数据规模预览）
/analysis                  → 数据仪表盘（核心页面）
/analysis/district/[name]  → 区县详情页（16个子页面）
```

### Landing 页

- Hero 区域：标题 + 副标题
- 核心数据三列：数据规模（12,751真实 + 增强）、分析模型（4+）、覆盖区县（39）
- 进入仪表盘链接

### 数据仪表盘 `/analysis`

| 区块 | 组件 | 数据来源 |
|------|------|---------|
| 页面标题 + 数据总量 | 内联 | `/api/stats/overview` |
| KPI 数据带 | `StatsHero` | overview |
| 房价预测模型 | `PredictionSection` | `/api/analysis/prediction` |
| KMeans 聚类画像 | `ClusteringSection` | `/api/analysis/clustering` |
| 关联规则挖掘 | `AssociationSection` | `/api/analysis/association-rules` |
| 区县房源排名 | `DistrictRanking` | overview.by_district |

### 区县详情页 `/analysis/district/[name]`

- 基础统计（房源数、均价、总价、面积）
- 装修分布、户型分布、价格分布、面积分布
- TOP 10 热门小区

---

## 三、数据流架构

```
┌──────────────┐     fetch()      ┌──────────────┐     SQL      ┌──────────┐
│  Next.js Web │  ◄──────────►   │  FastAPI      │  ◄────────►  │  MySQL   │
│  (浏览器)     │    JSON over     │  :8000        │              │  :3306   │
│              │     HTTP         │              │              │          │
│  Netlify 静态 │                 │  本地运行      │              │ 54,993条 │
│  或 localhost │                 │              │              │          │
└──────────────┘                 └──────────────┘              └──────────┘
```

**关键设计：**
- 仪表盘页面为客户端组件（`"use client"`），通过 `useEffect` 在浏览器端调用后端 API
- 后端不可用时自动降级到内置 fallback 数据（展示静态演示效果）
- 顶部状态指示灯：● 绿色 = 已连接后端 · ◉ 橙色 = 离线演示模式
- **增量更新体现**：每次打开/刷新页面 → 实时 fetch 后端 → 后端从 MySQL 读最新数据 → 前端自动展示最新数据。爬虫更新数据后，前端无需重新构建部署即可看到变化

---

## 四、两种运行模式

### 模式 1：本地开发（答辩推荐）

```bash
# 终端 1：启动后端
cd chongqing-house-analysis
uvicorn backend.main:app --reload --port 8000

# 终端 2：启动前端
cd chongqing-house-analysis/web
npm install
npm run dev
# 浏览器访问 http://localhost:3000
```

前端自动连接 `http://localhost:8000` 后端，实时展示数据库最新数据。

### 模式 2：Netlify 生产部署

```bash
cd web
# 设置后端公网地址（如果有云服务器或 ngrok）
set NEXT_PUBLIC_API_URL=https://你的后端地址
npm run build
# 部署 out/ 目录到 Netlify
```

---

## 五、关键组件说明

| 组件 | 文件路径 | 说明 |
|------|---------|------|
| `AnalysisPage` | `src/app/analysis/page.tsx` | 仪表盘主页面，客户端渲染，fetch 4个API |
| `PredictionSection` | `src/components/Dashboard/PredictionSection.tsx` | 房价预测：4模型卡片 + 特征重要性柱状图 |
| `ClusteringSection` | `src/components/Dashboard/ClusteringSection.tsx` | KMeans聚类：5类画像卡片 + 雷达图 + 金字塔 |
| `AssociationSection` | `src/components/Dashboard/AssociationSection.tsx` | 关联规则：热力散点图 + TOP10规则表格 |
| `DistrictRanking` | `src/components/Dashboard/DistrictRanking.tsx` | 区县排名柱状图（可点击钻取详情） |
| `StatsHero` | `src/components/Dashboard/StatsHero.tsx` | 顶部KPI数据带 |
| `DistrictDetailClient` | `src/components/Dashboard/DistrictDetailClient.tsx` | 区县详情客户端渲染 |

---

## 六、API 对接清单

前端调用的后端接口（全部 GET）：

| 接口 | 用途 | 返回关键字段 |
|------|------|-------------|
| `/health` | 探活 | `status`, `total_houses` |
| `/api/stats/overview` | 数据总览 | `total_houses`, `avg_unit_price`, `avg_total_price`, `district_count`, `by_source`, `by_district` |
| `/api/analysis/prediction` | 房价预测 | `models`, `feature_importance` |
| `/api/analysis/clustering` | 聚类分析 | `n_clusters`, `cluster_stats[]`, `silhouette_score` |
| `/api/analysis/association-rules` | 关联规则 | `rules[]`, `total_rules`, `conclusions` |
| `/api/stats/district/{name}` | 区县详情 | `house_count`, `avg_unit_price`, `price_distribution[]`, `area_distribution[]`, `top_communities[]` |

---

## 七、截图操作步骤

### 截图 A：Web 仪表盘全貌

**用途**：文档展示前端完整效果

**操作**：
1. 启动后端 + 前端（见第四节模式1）
2. 浏览器访问 `http://localhost:3000/analysis`
3. 等待数据加载完成（状态指示灯变绿）
4. 从上到下滚动截图，或分多屏截取：
   - 顶部 KPI 数据带
   - 房价预测模型 + 特征重要性图
   - KMeans 聚类画像 + 雷达图
   - 关联规则热力图 + TOP10 表格
   - 区县排名柱状图

### 截图 B：Landing 落地页

**用途**：展示项目首页

**操作**：
1. 浏览器访问 `http://localhost:3000/`
2. 截图 Hero 区域 + 三列数据

### 截图 C：Netlify 部署证明

**用途**：展示线上部署能力

**操作**：
1. 浏览器访问 Netlify 部署域名
2. 截图地址栏 + 页面

### 截图 D：响应式 / 移动端

**用途**：展示响应式设计

**操作**：
1. F12 → 切换设备工具栏 → 选择 iPhone 14 / iPad
2. 截图仪表盘在移动端的显示效果

---

## 八、涉及的源文件

| 文件 | 说明 |
|------|------|
| `web/src/app/page.tsx` | Landing 落地页 |
| `web/src/app/layout.tsx` | 全局布局 |
| `web/src/app/analysis/page.tsx` | 仪表盘主页面 ★ |
| `web/src/app/analysis/district/[name]/page.tsx` | 区县详情页 |
| `web/src/components/Dashboard/*.tsx` | 仪表盘子组件（8个） |
| `web/src/components/Hero/Hero.tsx` | Hero 区域组件 |
| `web/src/components/SmoothScroll/index.tsx` | 平滑滚动组件 |
| `web/src/lib/api.ts` | API 客户端（含 fallback） |
| `web/src/lib/types.ts` | TypeScript 类型定义 |
| `web/src/app/globals.css` | 全局样式 + 暗色主题变量 |
| `web/next.config.js` | Next.js 配置（static export） |
| `web/tailwind.config.js` | Tailwind 主题配置 |
| `web/netlify.toml` | Netlify 部署配置 |
| `web/package.json` | 依赖清单 |

---

> 📅 文档版本：v1.0 | 2026年7月4日 | 提供给成员C（王宇）
