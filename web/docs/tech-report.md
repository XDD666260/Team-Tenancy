# 重庆房价洞察 Web 前端 — 技术开发报告

> 学年设计Ⅱ｜成员A 胡霖｜2026年7月3日

---

## 一、项目概述

为弥补 Android App 在答辩展示时屏幕小、图表不清晰的问题，中期检查后决定开发 Web 版数据可视化平台。采用 **Next.js 15 + TypeScript + Tailwind CSS** 技术栈，配合 **Recharts** 交互图表和 **GSAP** 动画引擎，打造苹果官网级数据仪表盘。

**线上地址**：https://secondhousecq36.netlify.app

---

## 二、技术架构

```
┌────────────────────────────────────────────┐
│              部署层 (Netlify)                │
│        静态导出 · CDN 分发 · HTTPS          │
├────────────────────────────────────────────┤
│            框架层 (Next.js 15)              │
│  App Router · 静态导出 · 图片优化            │
├──────────────────┬─────────────────────────┤
│  组件层          │  数据可视化层             │
│  Hero/StatsHero  │  Recharts (柱状图/雷达图/ │
│  KpiCards/       │  热力图/环形图/散点图)     │
│  ChartImageBlock │  GSAP ScrollTrigger      │
├──────────────────┴─────────────────────────┤
│              样式层 (Tailwind CSS 3.4)       │
│  Design Token · card-dark · glass-card     │
│  PingFang SC Medium · Roboto Mono          │
└────────────────────────────────────────────┘
```

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 15.5 | App Router 框架，静态导出 |
| React | 19.0 | UI 组件库 |
| TypeScript | 5.7 | 类型安全 |
| Tailwind CSS | 3.4 | 原子化 CSS |
| Recharts | 3.9 | 交互式数据图表（柱状图/雷达图/散点图/环形图） |
| GSAP | 3.12 | 滚动动画引擎（ScrollTrigger） |
| Netlify | — | 静态托管 + CDN 分发 |

---

## 三、页面结构

| 路由 | 类型 | 说明 |
|------|------|------|
| `/` | 静态 | Hero 首页 + 数据预览区 |
| `/analysis` | 静态 | 数据仪表盘（7个分析区块） |
| `/analysis/district/[slug]` | SSG | 区县详情页（15个预生成，拼音URL） |

### /analysis 仪表盘布局

```
┌─ StatsHero ────────────────────────┐  5个大数字统计
├─ PredictionSection ────────────────┤  4个模型指标卡 + 特征重要性柱状图
├─ ClusteringSection ────────────────┤  5类画像卡片 + 雷达图 + 市场结构金字塔
├─ AssociationSection ───────────────┤  散点热力图 + TOP10规则表 + 关键发现
├─ DistrictRanking ──────────────────┤  TOP15区县横向柱状图（可点击钻取详情）
└─ 脚注 ─────────────────────────────┘  数据来源/更新时间
```

---

## 四、关键技术实现

### 4.1 响应式数据图表（Recharts）

所有图表使用 Recharts 库，通过内置 FALLBACK 数据确保后端离线时仍可渲染：

```tsx
// 每个组件内置兜底数据，静态导出时无需后端
const FALLBACK_CLUSTERS: ClusterStat[] = [ /* 5个聚类全量数据 */ ];
const clusters = data?.cluster_stats?.length ? data.cluster_stats : FALLBACK_CLUSTERS;
```

- **柱状图 (BarChart)**：价格分布、区县排名、特征重要性对比
- **雷达图 (RadarChart)**：五类画像四维归一化对比
- **散点图 (ScatterChart)**：关联规则热力图（支持度×置信度→提升度着色）
- **环形图 (PieChart)**：数据来源分布、装修分布
- **堆叠图**：市场结构金字塔

### 4.2 GSAP ScrollTrigger 动画

```tsx
// 入场动画 — 元素从下方淡入
gsap.fromTo(".cluster-section", { opacity: 0, y: 36 }, {
  opacity: 1, y: 0, duration: 0.8, ease: "power3.out",
  scrollTrigger: { trigger: sectionRef.current, start: "top 82%" },
});

// Hero 滚动淡出 — scrub 自动反向
gsap.to(contentRef.current, {
  scrollTrigger: { trigger: sectionRef.current, start: "top top", end: "bottom top", scrub: 0.5 },
  opacity: 0, y: -60,
});
```

### 4.3 雷达图归一化

**问题**：均价量纲（6000-26000）碾压面积（60-130）和户型（2-4），雷达图只呈现一根粗蓝线。

**解决**：四维归一化到 0-100 百分比：
```tsx
const MAX_VALS = { avg_unit_price: 28000, avg_total_price: 300, avg_area: 150, avg_rooms: 5 };
// 每个维度值 = (原始值 / 最大值) * 100, domain = [0, 100]
```

### 4.4 区县路由（中文→拼音）

**问题**：中文区县名在 Netlify CDN 上 URL 编码异常，导致点击区县后 404。

**解决**：URL 改用拼音 slug：
```tsx
const DISTRICT_SLUG = {
  "两江新区": "liangjiang", "渝北区": "yubei", "江北区": "jiangbei", // 共15个
};
// URL: /analysis/district/liangjiang
```

### 4.5 静态导出策略

舍弃 SSR，改用纯静态导出以兼容 Netlify：
```js
// next.config.js
output: "export",
images: { unoptimized: true },
```

动态路由用 `generateStaticParams` 预生成 15 个区县页面。

---

## 五、设计系统

### 5.1 色彩体系（Shift5 风格）

| Token | 色值 | 用途 |
|-------|------|------|
| `--bg-primary` | `#000000` | 主背景 |
| `--bg-card` | `#0d0d0d` | 卡片背景 |
| `--text-primary` | `#ffffff` | 主文字 |
| `--text-secondary` | `#cccccc` | 次文字 |
| `--accent-mint` | `#94ddde` | 薄荷绿（数据高亮、边框发光） |
| `--accent-pink` | `#f7b4a7` | 粉色高亮（关键数字、标签） |
| `--accent-blue` | `#2b4b82` | 深蓝主色 |

### 5.2 排版层级

| 类名 | 规格 | 用途 |
|------|------|------|
| `.h1` | 64px / 300wt | 页面主标题 |
| `.h2` | 40px / 400wt | 区块标题 |
| `.h3` | 18px / 500wt | 卡片标题 |
| `.stat-number` | 72px / 300wt | 大数字统计 |
| `.lead` | 18px / 300wt | 引导段落 |
| `.body` | 15px | 正文 |
| `.caption` | 12px | 脚注/图注 |

---

## 六、遇到的问题与解决方案

### 6.1 Lenis 平滑滚动失效

**现象**：首页 100vh Hero 完全无法滚动。

**原因**：Lenis 拦截浏览器 `wheel` 事件，在 `overflow: hidden` 页面滚动计算异常。

**解决**：移除 Lenis，改用 CSS `scroll-behavior: smooth` + 原生 `scroll` 事件监听 + `ScrollTrigger.update()`。

### 6.2 useMemo SSR Hydration 导致数据丢失

**现象**：关联规则表格所有行显示"(无前提)(无结论)"。

**原因**：`useMemo` 在 SSR 和客户端 hydration 之间依赖引用变化，缓存了空数组。

**解决**：去掉 `useMemo`，改用纯函数每次渲染实时计算，并过滤有效数据项。

### 6.3 Recharts Tooltip 黑色文字

**现象**：鼠标悬停图表时 Tooltip 文字全黑，深色背景上不可读。

**解决**：创建 `ChartTooltip` 自定义组件，所有文字强制白色 + 全局 CSS 覆盖 `.recharts-tooltip-*`。

### 6.4 SVG 属性不支持 CSS 变量

**现象**：`stroke="var(--color-mint)"` 渲染为黑色。

**原因**：SVG 1.1 属性不支持 CSS `var()`。

**解决**：改为 `stroke="#94ddde"` + `style={{ stroke: "#94ddde" }}` 双保险。

### 6.5 Vercel/Netlify 部署适配

**过程**：
1. Vercel CLI → 需登录 → 无法获取账号
2. Netlify CLI → `@netlify/plugin-nextjs` → `MissingBlobsEnvironmentError`
3. **最终方案**：`output: 'export'` 静态导出 + Netlify 纯静态托管 → ✅ 成功

---

## 七、部署方式

```bash
cd chongqing-house-analysis/web
npm install --registry=https://registry.npmmirror.com
npm run build          # → out/ 目录
netlify deploy --prod  # → secondhousecq36.netlify.app
```

---

> 📅 开发时间：2026年7月2日-3日｜🛠 Next.js 15 + React 19 + TypeScript + Recharts + GSAP
> 🌐 https://secondhousecq36.netlify.app
