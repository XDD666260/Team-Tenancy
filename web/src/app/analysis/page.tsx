import SmoothScroll from "@/components/SmoothScroll";
import StatsHero from "@/components/Dashboard/StatsHero";
import DistrictRanking from "@/components/Dashboard/DistrictRanking";
import PredictionSection from "@/components/Dashboard/PredictionSection";
import ClusteringSection from "@/components/Dashboard/ClusteringSection";
import AssociationSection from "@/components/Dashboard/AssociationSection";

export default function AnalysisPage() {
  const overview = {
    total_houses: 50507, avg_unit_price: 8042, avg_total_price: 82.3,
    max_unit_price: 26582, min_unit_price: 3240, district_count: 32,
    update_time: "2026-06-28",
    by_source: { "安居客": 32150, "链家": 18357 },
    by_district: [
      { district: "渝北区", count: 6842, avg_unit_price: 9520, avg_total_price: 98.5 },
      { district: "沙坪坝区", count: 5120, avg_unit_price: 7830, avg_total_price: 72.1 },
      { district: "南岸区", count: 4380, avg_unit_price: 8650, avg_total_price: 85.3 },
      { district: "江北区", count: 3910, avg_unit_price: 11200, avg_total_price: 118.2 },
      { district: "九龙坡区", count: 3520, avg_unit_price: 7420, avg_total_price: 68.9 },
      { district: "两江新区", count: 3280, avg_unit_price: 12450, avg_total_price: 135.6 },
      { district: "巴南区", count: 2950, avg_unit_price: 6210, avg_total_price: 58.3 },
      { district: "渝中区", count: 2680, avg_unit_price: 13800, avg_total_price: 152.7 },
      { district: "北碚区", count: 2340, avg_unit_price: 5890, avg_total_price: 55.2 },
      { district: "大渡口区", count: 1980, avg_unit_price: 6750, avg_total_price: 62.8 },
      { district: "璧山区", count: 1650, avg_unit_price: 5120, avg_total_price: 48.5 },
      { district: "江津区", count: 1420, avg_unit_price: 4680, avg_total_price: 45.1 },
      { district: "长寿区", count: 1280, avg_unit_price: 3850, avg_total_price: 36.8 },
      { district: "合川区", count: 1150, avg_unit_price: 3520, avg_total_price: 33.5 },
      { district: "永川区", count: 1020, avg_unit_price: 4210, avg_total_price: 40.2 },
    ],
  };

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
        <PredictionSection data={{ models: {}, feature_importance: {} }} />

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
        <ClusteringSection data={{ n_clusters: 5, inertia_: 0, silhouette_score: null, cluster_stats: [] }} />

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
        <AssociationSection data={{ rules: [], total_rules: 0 }} />

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
