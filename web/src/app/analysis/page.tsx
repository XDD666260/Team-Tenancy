import SmoothScroll from "@/components/SmoothScroll";
import StatsHero from "@/components/Dashboard/StatsHero";
import ChartImageBlock from "@/components/Dashboard/ChartImageBlock";
import DistrictRanking from "@/components/Dashboard/DistrictRanking";
import { getOverview } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AnalysisPage() {
  const overview = await getOverview();

  return (
    <SmoothScroll>
      {/* ══════════════════════════════════════════════
          Shift5 Black/White Layout — 数据叙事驱动
          ══════════════════════════════════════════════ */}

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

        {/* ═══ 1. 房价预测 — 左文右图 ═══ */}
        <ChartImageBlock
          layout="text-left"
          tag="机器学习"
          title="随机森林与梯度提升：房价预测模型"
          description="面积（33.7%）+ 小区地段（25.5%）+ 区县均价（25.5%）共同解释房价变化的 84.7%。装修、朝向等单因素影响微小，综合配置才有意义。"
          bulletPoints={[
            "RandomForest 测试 R² = 0.53，总价比单价更易预测",
            "面积是房价第一驱动力，重要性远超装修和朝向",
            "两江新区、江北区、渝中区位列高价位前三",
          ]}
          imgSrc="/charts/feature_importance_compare_总价.png"
          imgAlt="特征重要性对比"
          imgWidth={1200}
          imgHeight={700}
        />

        {/* ═══ 2. 预测效果 — 右文左图 ═══ */}
        <ChartImageBlock
          layout="text-right"
          tag="模型评估"
          title="预测效果可视化：实际 vs 预测"
          description="散点图展示模型在测试集（9,352 条）上的预测表现。数据点越靠近对角线，预测越准确。"
          bulletPoints={[
            "RF 总价预测 MAE = 32.83 万，对一套 120 万的房子误差约 27%",
            "单价预测难度更高（R² 仅 0.40），因极端豪宅拉大方差",
            "5 折交叉验证确认模型泛化能力稳定",
          ]}
          imgSrc="/charts/prediction_RandomForest_total.png"
          imgAlt="随机森林预测效果"
          imgWidth={1400}
          imgHeight={500}
        />

        {/* ═══ 3. KMeans 聚类 PCA — 左文右图 ═══ */}
        <ChartImageBlock
          layout="text-left"
          tag="无监督学习"
          title="KMeans 聚类：五类市场画像"
          description="PCA 降维至二维空间，将 50,507 条房源分为五类。轮廓系数 0.31，聚类结构清晰可见。"
          bulletPoints={[
            "聚类 1（36.4%）远郊大户型：均价 ¥6,481，面积 109㎡",
            "聚类 0（27.7%）紧凑刚需：均价 ¥9,245，面积 63㎡",
            "聚类 4（5.6%）高端豪宅：均价 ¥26,582，集中渝中/江北",
          ]}
          imgSrc="/charts/clustering_pca.png"
          imgAlt="聚类PCA降维可视化"
          imgWidth={1200}
          imgHeight={800}
        />

        {/* ═══ 4. 雷达图 — 右文左图 ═══ */}
        <ChartImageBlock
          layout="text-right"
          tag="多维对比"
          title="雷达图：五类画像全维度扫描"
          description="五种市场类型的单价、总价、面积、户型四维对比，形状差异直观反映市场分层。"
          bulletPoints={[
            "高端豪宅在所有维度均远超其他类别",
            "远郊大户型面积大但单价低，形成独特的扁平雷达形状",
            "紧凑刚需与中等舒适型在均价上差距不大，面积是主要区分维度",
          ]}
          imgSrc="/charts/clustering_radar.png"
          imgAlt="聚类雷达图"
          imgWidth={800}
          imgHeight={800}
        />

        {/* ═══ 5. 关联规则 — 左文右图 ═══ */}
        <ChartImageBlock
          layout="text-left"
          tag="关联挖掘"
          title="Apriori 关联规则：发现隐藏的市场规律"
          description="从 50,507 条数据中挖掘出 50 条高质量关联规则，揭示价格、面积、地段之间的隐含关系。"
          bulletPoints={[
            "两江新区 + 12000-18000元/㎡ → 总价 120-200 万（Lift=7.33）",
            "总价<50 万 → 面积<60㎡，置信度高达 99%",
            "90-120㎡ + 中高价位 → 改善型三房，是市场甜蜜点",
          ]}
          imgSrc="/charts/association_top20_rules.png"
          imgAlt="关联规则TOP20"
          imgWidth={1200}
          imgHeight={800}
        />

        {/* ═══ 6. 区县价格排名 — 全幅图像 ═══ */}
        <div className="mx-auto max-w-6xl px-6 py-16 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">地理分布</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              区县价格图谱
            </h2>
            <p className="lead mt-3 max-w-2xl">
              渝中区以均价 ¥13,800/㎡ 领跑全市，璧山、江津等远郊区县均价不足 ¥5,000。
              房价梯度清晰反映重庆"一核多极"的城市空间结构。
            </p>
          </div>
          <div className="overflow-hidden rounded-xl"
            style={{ border: "1px solid var(--border-subtle)", background: "var(--bg-secondary)" }}>
            <img
              src="/charts/district_price_ranking.png"
              alt="区县价格排名"
              className="h-auto w-full"
            />
          </div>
          <p className="caption mt-4">▲ 重庆各区县二手房均价排名（TOP 20）及房源数量分布</p>
          <hr className="hr mt-16" />
        </div>

        {/* ═══ 7. 交互式区县排行 — 可点击钻取 ═══ */}
        <div className="mx-auto max-w-6xl px-6 pb-12 sm:px-8 lg:px-10">
          <div className="card-dark" style={{ padding: 32 }}>
            <h3 className="h3 mb-6" style={{ color: "var(--text-primary)" }}>
              区县详情钻取
            </h3>
            <p className="lead mb-8" style={{ fontSize: 14 }}>
              点击下方柱状图中的任意区县，查看该区县详细的价格分布、户型构成、装修占比和热门小区。
            </p>
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
