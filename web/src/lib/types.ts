/** 数据总览 — /api/stats/overview */
export interface OverviewData {
  total_houses: number;
  avg_unit_price: number;
  avg_total_price: number;
  max_unit_price: number;
  min_unit_price: number;
  district_count: number;
  update_time: string;
  by_source: Record<string, number>;
  by_district: DistrictStat[];
}

export interface DistrictStat {
  district: string;
  count: number;
  avg_unit_price: number;
  avg_total_price: number;
}

/** 价格分布 — /api/stats/price-distribution */
export interface PriceBin {
  range: string;
  count: number;
}

export interface PriceDistribution {
  unit_price_bins: PriceBin[];
  total_price_bins: PriceBin[];
}

/** 快速统计 — /api/analysis/quick-stats */
export interface QuickStats {
  total_listings: number;
  avg_unit_price: number;
  avg_total_price: number;
  avg_area: number;
  avg_build_year: number;
  decoration_distribution: { name: string; count: number }[];
  floor_distribution: { name: string; count: number }[];
}
