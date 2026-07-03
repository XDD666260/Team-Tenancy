# 重庆二手房房价分析网站（学年设计项目）
> 根据中期进度检查调整，网页展示主要是为了在答辩的时候展示数据可视化，比Android app更加清晰直观


## 技术栈
- Next.js 15 App Router + TypeScript
- Tailwind CSS
- GSAP + ScrollTrigger（苹果级平滑滚动）
- ECharts / Recharts（数据可视化）

## 配色规范（Design Token）
- 主色 --color-primary: #2b4b82（深蓝）
- 辅助 --color-deep-purple: #392752
- 点缀 --color-pink-light: #f7b4a7 / #f0abc1
- 点缀 --color-mint: #94ddde
- 脏紫 --color-dust-purple: #6e426a / #a0637f / #ce8992
- 背景深色渐变，卡片毛玻璃

## 交互要求
- Lenis 或 Locomotive Scroll 平滑滚动
- GSAP ScrollTrigger 区域吸顶 + 数字递增动画
- hover 微缩放 + glow，极简高级感

## 命令
- dev: npm run dev
- build: npm run build
- lint: npm run lint