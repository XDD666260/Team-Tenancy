import type { OverviewData, PriceDistribution, QuickStats } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.data as T;
  } catch {
    return null; // 后端未启动时静默降级
  }
}

/** 获取数据总览（KPI + 区县排行） */
export async function getOverview(): Promise<OverviewData> {
  const data = await fetchAPI<OverviewData>("/api/stats/overview");
  return data ?? MOCK_OVERVIEW;
}

/** 获取价格分布 */
export async function getPriceDistribution(): Promise<PriceDistribution> {
  const data = await fetchAPI<PriceDistribution>("/api/stats/price-distribution");
  return data ?? MOCK_PRICE_DIST;
}

/** 获取快速统计 */
export async function getQuickStats(): Promise<QuickStats> {
  const data = await fetchAPI<QuickStats>("/api/analysis/quick-stats");
  return data ?? MOCK_QUICK_STATS;
}

// ── Mock 数据（后端离线时使用） ──

const MOCK_OVERVIEW: OverviewData = {
  total_houses: 50507,
  avg_unit_price: 8042,
  avg_total_price: 82.3,
  max_unit_price: 26582,
  min_unit_price: 3240,
  district_count: 32,
  update_time: "2026-06-28",
  by_source: { 安居客: 32150, 链家: 18357 },
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

const MOCK_PRICE_DIST: PriceDistribution = {
  unit_price_bins: [
    { range: "5000以下", count: 8200 },
    { range: "5000-8000", count: 18500 },
    { range: "8000-12000", count: 15200 },
    { range: "12000-18000", count: 6200 },
    { range: "18000-25000", count: 1850 },
    { range: "25000以上", count: 557 },
  ],
  total_price_bins: [
    { range: "50万以下", count: 14200 },
    { range: "50-80万", count: 16300 },
    { range: "80-120万", count: 10500 },
    { range: "120-200万", count: 6800 },
    { range: "200-300万", count: 1850 },
    { range: "300万以上", count: 857 },
  ],
};

const MOCK_QUICK_STATS: QuickStats = {
  total_listings: 50507,
  avg_unit_price: 8042,
  avg_total_price: 82.3,
  avg_area: 92.5,
  avg_build_year: 2012,
  decoration_distribution: [
    { name: "精装", count: 18500 },
    { name: "简装", count: 15200 },
    { name: "毛坯", count: 9800 },
    { name: "豪装", count: 4200 },
    { name: "中装", count: 2807 },
  ],
  floor_distribution: [
    { name: "中层", count: 18200 },
    { name: "低层", count: 16500 },
    { name: "高层", count: 15807 },
  ],
};
