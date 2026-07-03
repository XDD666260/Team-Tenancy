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

/** 房价预测 — /api/analysis/prediction */
export interface ModelResult {
  model_type: "RandomForest" | "GradientBoosting";
  target: string;
  train_samples: number;
  test_samples: number;
  train_mae: number;
  test_mae: number;
  train_rmse: number;
  test_rmse: number;
  train_r2: number;
  test_r2: number;
  cv_r2_mean: number;
  cv_r2_std: number;
  features: string[];
  unit: string;
}

export interface FeatureImportanceItem {
  rank: number;
  feature: string;
  feature_cn: string;
  importance: number;
}

export interface PredictionData {
  models: Record<string, ModelResult>;
  feature_importance: Record<string, FeatureImportanceItem[]>;
}

/** 聚类分析 — /api/analysis/clustering */
export interface ClusterStat {
  cluster_id: number;
  count: number;
  pct: number;
  avg_unit_price: number;
  avg_total_price: number;
  avg_area: number;
  avg_rooms: number;
  avg_house_age: number;
  top_districts: Record<string, number>;
  dominant_decoration: string;
  dominant_floor: string;
}

export interface ClusteringData {
  n_clusters: number;
  inertia_: number;
  silhouette_score: number | null;
  cluster_stats: ClusterStat[];
}

/** 关联规则 — /api/analysis/association-rules */
export interface AssociationRule {
  antecedents: string;
  consequents: string;
  support: number;
  confidence: number;
  lift: number;
}

export interface AssociationData {
  rules: AssociationRule[];
  total_rules: number;
  conclusions?: string;
}
