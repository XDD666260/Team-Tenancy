import SmoothScroll from "@/components/SmoothScroll";
import StatsHero from "@/components/Dashboard/StatsHero";
import DistrictRanking from "@/components/Dashboard/DistrictRanking";
import PredictionSection from "@/components/Dashboard/PredictionSection";
import ClusteringSection from "@/components/Dashboard/ClusteringSection";
import AssociationSection from "@/components/Dashboard/AssociationSection";
import {
  getOverview,
  getPrediction,
  getClustering,
  getAssociationRules,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AnalysisPage() {
  // 独立 fetch，单个失败不影响其他模块
  const overview = await getOverview().catch(() => null);
  const prediction = await getPrediction().catch(() => null);
  const clustering = await getClustering().catch(() => null);
  const assocRules = await getAssociationRules().catch(() => null);

  if (!overview) {
    return (
      <main style={{ background: "var(--bg-primary)", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p className="lead">数据加载失败，请刷新重试</p>
      </main>
    );
  }

  return (
    <SmoothScroll>
      <main style={{ background: "var(--bg-primary)" }}>

        {/* ── 页面标题 ── */}
        <div className="mx-auto max-w-6xl px-6 pt-28 sm:px-8 lg:px-10">
          <span className="tag mb-6">Dashboard</span>
          <h1 className="h1 mb-4" style={{ color: "var(--text-primary)" }}>
            重庆二手房<br />数据洞察
          </h1>
          <p className="lead max-w-2xl">
            基于 <span style={{ color: "var(--accent-pink)" }}>50,507</span> 条真实在售房源数据，
            覆盖重庆 <span style={{ color: "var(--accent-mint)" }}>30+</span> 个区县，
            运用机器学习方法深度剖析市场结构与价格规律。
          </p>
        </div>

        {/* ── 核心数据带 ── */}
        <StatsHero stats={[
          { value: "50,507", label: "在售房源 / 条" },
          { value: "8,042", label: "均价 / 元/㎡" },
          { value: "32", label: "覆盖区县 / 个" },
          { value: "0.53", label: "预测模型 R²" },
          { value: "5", label: "市场细分 / 类" },
        ]} />

        {/* ── 房价预测分析 — 交互式 Recharts ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">机器学习</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              房价预测模型
            </h2>
            <p className="lead mt-3 max-w-2xl">
              面积（33.7%）+ 小区地段（25.5%）+ 区县均价（25.5%）共同解释房价变化的 84.7%。
            </p>
          </div>
        </div>
        <PredictionSection data={prediction ?? { models: {}, feature_importance: {} }} />

        {/* ── KMeans 聚类 — 交互式雷达图 ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">无监督学习</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              KMeans 聚类画像
            </h2>
            <p className="lead mt-3 max-w-2xl">
              五类市场画像：高端豪宅仅 5.6%，远郊大户 + 紧凑刚需占 64%。
            </p>
          </div>
        </div>
        <ClusteringSection data={clustering ?? { n_clusters: 5, inertia_: 0, silhouette_score: null, cluster_stats: [] }} />

        {/* ── 关联规则 — 交互式热力图 + 表格 ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">关联挖掘</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              关联规则挖掘
            </h2>
            <p className="lead mt-3 max-w-2xl">
              Apriori 算法发现 50 条高质量规则，最高提升度 7.33。
            </p>
          </div>
        </div>
        <AssociationSection data={assocRules ?? { rules: [], total_rules: 0 }} />

        {/* ── 区县排名 — 交互式可点击钻取 ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">地理分布</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              区县房源排名
            </h2>
            <p className="lead mt-3 max-w-2xl">
              渝中区均价 ¥13,800/㎡ 领跑全市。点击柱状图查看区县详情。
            </p>
          </div>
          <div className="card-dark" style={{ padding: 32 }}>
            <DistrictRanking districts={overview.by_district} />
          </div>
        </div>

        {/* ── 底部 ── */}
        <div className="mx-auto max-w-6xl px-6 pb-32 pt-8 sm:px-8 lg:px-10">
          <hr className="hr mb-10" />
          <p className="caption text-center">
            数据来源：安居客 · 链家 | 更新时间：{overview.update_time || "2026-06-28"} |
            分析框架：RandomForest · GradientBoosting · KMeans · Apriori
          </p>
        </div>

      </main>
    </SmoothScroll>
  );
}
