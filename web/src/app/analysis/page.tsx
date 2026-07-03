import SmoothScroll from "@/components/SmoothScroll";
import DashboardHero from "@/components/Dashboard/DashboardHero";
import KpiCards from "@/components/Dashboard/KpiCards";
import PriceChart from "@/components/Dashboard/PriceChart";
import DistrictRanking from "@/components/Dashboard/DistrictRanking";
import SourceChart from "@/components/Dashboard/SourceChart";
import PredictionSection from "@/components/Dashboard/PredictionSection";
import ClusteringSection from "@/components/Dashboard/ClusteringSection";
import { getOverview, getPriceDistribution, getPrediction, getClustering } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AnalysisPage() {
  const [overview, priceDist, prediction, clustering] = await Promise.all([
    getOverview(),
    getPriceDistribution(),
    getPrediction(),
    getClustering(),
  ]);

  return (
    <SmoothScroll>
      <main className="min-h-screen bg-bg-dark">
        {/* Hero Banner */}
        <DashboardHero updateTime={overview.update_time} />

        {/* KPI 指标卡片 */}
        <KpiCards
          totalHouses={overview.total_houses}
          avgUnitPrice={overview.avg_unit_price}
          avgTotalPrice={overview.avg_total_price}
          maxUnitPrice={overview.max_unit_price}
          minUnitPrice={overview.min_unit_price}
          districtCount={overview.district_count}
        />

        {/* 价格分布图 */}
        <PriceChart
          unitPriceBins={priceDist.unit_price_bins}
          totalPriceBins={priceDist.total_price_bins}
        />

        {/* 区县排名 */}
        <DistrictRanking districts={overview.by_district} />

        {/* 数据来源 */}
        <SourceChart bySource={overview.by_source} />

        {/* 房价预测分析 */}
        <PredictionSection data={prediction} />

        {/* KMeans 聚类画像 */}
        <ClusteringSection data={clustering} />
      </main>
    </SmoothScroll>
  );
}
