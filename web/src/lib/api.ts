import type { OverviewData, PriceDistribution, QuickStats, PredictionData, ClusteringData, AssociationData, DistrictDetail } from "./types";

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

// ── 预测分析 API ──

export async function getPrediction(): Promise<PredictionData> {
  const data = await fetchAPI<PredictionData>("/api/analysis/prediction");
  return data ?? MOCK_PREDICTION;
}

export async function getClustering(): Promise<ClusteringData> {
  const data = await fetchAPI<ClusteringData>("/api/analysis/clustering");
  return data ?? MOCK_CLUSTERING;
}

export async function getAssociationRules(): Promise<AssociationData> {
  const data = await fetchAPI<AssociationData>("/api/analysis/association-rules");
  return data ?? MOCK_ASSOCIATION;
}

// ── Mock 预测数据 ──

const MOCK_PREDICTION: PredictionData = {
  models: {
    RandomForest_total: {
      model_type: "RandomForest",
      target: "total_price(万)",
      train_samples: 37408,
      test_samples: 9352,
      train_mae: 18.21,
      test_mae: 32.83,
      train_rmse: 28.56,
      test_rmse: 52.67,
      train_r2: 0.8321,
      test_r2: 0.5345,
      cv_r2_mean: 0.508,
      cv_r2_std: 0.02,
      features: [],
      unit: "万",
    },
    RandomForest_unit: {
      model_type: "RandomForest",
      target: "unit_price(元/㎡)",
      train_samples: 37408,
      test_samples: 9352,
      train_mae: 1850,
      test_mae: 3267,
      train_rmse: 2980,
      test_rmse: 5120,
      train_r2: 0.712,
      test_r2: 0.4023,
      cv_r2_mean: 0.391,
      cv_r2_std: 0.02,
      features: [],
      unit: "元/㎡",
    },
    GradientBoosting_total: {
      model_type: "GradientBoosting",
      target: "total_price(万)",
      train_samples: 37408,
      test_samples: 9352,
      train_mae: 19.5,
      test_mae: 33.03,
      train_rmse: 30.12,
      test_rmse: 53.45,
      train_r2: 0.815,
      test_r2: 0.5137,
      cv_r2_mean: 0.488,
      cv_r2_std: 0.03,
      features: [],
      unit: "万",
    },
    GradientBoosting_unit: {
      model_type: "GradientBoosting",
      target: "unit_price(元/㎡)",
      train_samples: 37408,
      test_samples: 9352,
      train_mae: 1910,
      test_mae: 3283,
      train_rmse: 3050,
      test_rmse: 5180,
      train_r2: 0.698,
      test_r2: 0.3797,
      cv_r2_mean: 0.369,
      cv_r2_std: 0.03,
      features: [],
      unit: "元/㎡",
    },
  },
  feature_importance: {
    RandomForest_total: [
      { rank: 1, feature: "area", feature_cn: "面积", importance: 0.337 },
      { rank: 2, feature: "community_encoded", feature_cn: "小区(均价编码)", importance: 0.255 },
      { rank: 3, feature: "district_encoded", feature_cn: "区县(均价编码)", importance: 0.255 },
      { rank: 4, feature: "avg_room_area", feature_cn: "户均面积", importance: 0.069 },
      { rank: 5, feature: "total_floors", feature_cn: "总楼层", importance: 0.043 },
      { rank: 6, feature: "bathrooms", feature_cn: "卫", importance: 0.012 },
      { rank: 7, feature: "rooms", feature_cn: "室", importance: 0.01 },
      { rank: 8, feature: "house_age", feature_cn: "房龄", importance: 0.008 },
      { rank: 9, feature: "halls", feature_cn: "厅", importance: 0.005 },
      { rank: 10, feature: "orientation_code", feature_cn: "朝向", importance: 0.003 },
      { rank: 11, feature: "decoration_code", feature_cn: "装修", importance: 0.002 },
      { rank: 12, feature: "floor_type_code", feature_cn: "楼层类型", importance: 0.001 },
    ],
    GradientBoosting_total: [
      { rank: 1, feature: "area", feature_cn: "面积", importance: 0.312 },
      { rank: 2, feature: "district_encoded", feature_cn: "区县(均价编码)", importance: 0.268 },
      { rank: 3, feature: "community_encoded", feature_cn: "小区(均价编码)", importance: 0.238 },
      { rank: 4, feature: "avg_room_area", feature_cn: "户均面积", importance: 0.078 },
      { rank: 5, feature: "total_floors", feature_cn: "总楼层", importance: 0.051 },
      { rank: 6, feature: "bathrooms", feature_cn: "卫", importance: 0.018 },
      { rank: 7, feature: "rooms", feature_cn: "室", importance: 0.014 },
      { rank: 8, feature: "house_age", feature_cn: "房龄", importance: 0.009 },
      { rank: 9, feature: "halls", feature_cn: "厅", importance: 0.006 },
      { rank: 10, feature: "decoration_code", feature_cn: "装修", importance: 0.003 },
      { rank: 11, feature: "orientation_code", feature_cn: "朝向", importance: 0.002 },
      { rank: 12, feature: "floor_type_code", feature_cn: "楼层类型", importance: 0.001 },
    ],
  },
};

// ── Mock 聚类数据 ──

const MOCK_CLUSTERING: ClusteringData = {
  n_clusters: 5,
  inertia_: 284723.5,
  silhouette_score: 0.312,
  cluster_stats: [
    {
      cluster_id: 0, count: 12979, pct: 27.7,
      avg_unit_price: 9245, avg_total_price: 58.0, avg_area: 63.3,
      avg_rooms: 2.7, avg_house_age: 12,
      top_districts: { "渝北区": 3210, "沙坪坝区": 2580, "南岸区": 1920 },
      dominant_decoration: "简装", dominant_floor: "中层",
    },
    {
      cluster_id: 1, count: 17070, pct: 36.4,
      avg_unit_price: 6481, avg_total_price: 70.9, avg_area: 109.4,
      avg_rooms: 3.3, avg_house_age: 9,
      top_districts: { "巴南区": 4120, "北碚区": 3850, "璧山区": 2980 },
      dominant_decoration: "毛坯", dominant_floor: "高层",
    },
    {
      cluster_id: 2, count: 3367, pct: 7.2,
      avg_unit_price: 8297, avg_total_price: 80.2, avg_area: 96.7,
      avg_rooms: 2.9, avg_house_age: 10,
      top_districts: { "九龙坡区": 890, "大渡口区": 720, "沙坪坝区": 650 },
      dominant_decoration: "精装", dominant_floor: "中层",
    },
    {
      cluster_id: 3, count: 10720, pct: 22.9,
      avg_unit_price: 10257, avg_total_price: 131.4, avg_area: 128.1,
      avg_rooms: 2.6, avg_house_age: 8,
      top_districts: { "两江新区": 2890, "江北区": 2450, "南岸区": 2100 },
      dominant_decoration: "豪装", dominant_floor: "中层",
    },
    {
      cluster_id: 4, count: 2624, pct: 5.6,
      avg_unit_price: 26582, avg_total_price: 283.6, avg_area: 106.7,
      avg_rooms: 2.9, avg_house_age: 5,
      top_districts: { "渝中区": 980, "江北区": 720, "两江新区": 450 },
      dominant_decoration: "豪装", dominant_floor: "高层",
    },
  ],
};

// ── Mock 关联规则数据 ──

const MOCK_ASSOCIATION: AssociationData = {
  total_rules: 50,
  rules: [
    { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "两江新区 + 总价120-200万", support: 0.023, confidence: 0.53, lift: 7.33 },
    { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万 + 3室", support: 0.024, confidence: 0.56, lift: 7.12 },
    { antecedents: "单价8000-12000 + 总价<50万", consequents: "面积<60㎡", support: 0.024, confidence: 0.99, lift: 6.82 },
    { antecedents: "区县=武隆区 + 总价<50万", consequents: "南向 + 面积<60㎡", support: 0.027, confidence: 0.66, lift: 6.72 },
    { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万", support: 0.039, confidence: 0.92, lift: 6.34 },
    { antecedents: "两江新区 + 单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万", support: 0.023, confidence: 0.91, lift: 6.31 },
    { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万 + 南向", support: 0.029, confidence: 0.68, lift: 6.16 },
    { antecedents: "总价120-200万 + 面积90-120㎡", consequents: "单价12000-18000 + 3室", support: 0.024, confidence: 0.45, lift: 5.97 },
    { antecedents: "房龄5-10年", consequents: "南向 + anjuke来源", support: 0.026, confidence: 0.86, lift: 5.92 },
    { antecedents: "面积60-90㎡", consequents: "单价8000-12000", support: 0.079, confidence: 0.31, lift: 2.86 },
  ],
  conclusions: "面积+地段解释房价84.7%变化；两江新区是12000-18000元/㎡核心区域；低价必小面积(置信度99%)",
};

// ── 区县详情 API ──

export async function getDistrictDetail(name: string): Promise<DistrictDetail> {
  const data = await fetchAPI<DistrictDetail>(`/api/stats/district/${encodeURIComponent(name)}`);
  return data ?? getMockDistrict(name);
}

function getMockDistrict(name: string): DistrictDetail {
  const base: Record<string, Partial<DistrictDetail>> = {
    "渝北区": { house_count: 6842, avg_unit_price: 9520, avg_total_price: 98.5, avg_area: 103.5, max_price: 380, min_price: 22 },
    "两江新区": { house_count: 3280, avg_unit_price: 12450, avg_total_price: 135.6, avg_area: 108.9, max_price: 520, min_price: 35 },
    "渝中区": { house_count: 2680, avg_unit_price: 13800, avg_total_price: 152.7, avg_area: 110.6, max_price: 680, min_price: 40 },
    "江北区": { house_count: 3910, avg_unit_price: 11200, avg_total_price: 118.2, avg_area: 105.2, max_price: 450, min_price: 30 },
    "沙坪坝区": { house_count: 5120, avg_unit_price: 7830, avg_total_price: 72.1, avg_area: 92.3, max_price: 280, min_price: 18 },
    "南岸区": { house_count: 4380, avg_unit_price: 8650, avg_total_price: 85.3, avg_area: 98.5, max_price: 320, min_price: 20 },
    "九龙坡区": { house_count: 3520, avg_unit_price: 7420, avg_total_price: 68.9, avg_area: 93.1, max_price: 260, min_price: 15 },
    "巴南区": { house_count: 2950, avg_unit_price: 6210, avg_total_price: 58.3, avg_area: 106.5, max_price: 200, min_price: 12 },
  };

  const d = base[name] || {
    house_count: 1500, avg_unit_price: 7000, avg_total_price: 70, avg_area: 95,
    max_price: 250, min_price: 15,
  };

  return {
    district: name,
    house_count: d.house_count!,
    avg_unit_price: d.avg_unit_price!,
    avg_total_price: d.avg_total_price!,
    avg_area: d.avg_area!,
    max_price: d.max_price!,
    min_price: d.min_price!,
    decoration_distribution: [
      { type: "精装", count: Math.floor(d.house_count! * 0.38) },
      { type: "简装", count: Math.floor(d.house_count! * 0.28) },
      { type: "毛坯", count: Math.floor(d.house_count! * 0.18) },
      { type: "豪装", count: Math.floor(d.house_count! * 0.10) },
      { type: "中装", count: Math.floor(d.house_count! * 0.06) },
    ],
    layout_distribution: [
      { rooms: 1, count: Math.floor(d.house_count! * 0.08) },
      { rooms: 2, count: Math.floor(d.house_count! * 0.28) },
      { rooms: 3, count: Math.floor(d.house_count! * 0.42) },
      { rooms: 4, count: Math.floor(d.house_count! * 0.16) },
      { rooms: 5, count: Math.floor(d.house_count! * 0.06) },
    ],
    price_distribution: [
      { range: "50万以下", count: Math.floor(d.house_count! * 0.24) },
      { range: "50-80万", count: Math.floor(d.house_count! * 0.30) },
      { range: "80-120万", count: Math.floor(d.house_count! * 0.22) },
      { range: "120-200万", count: Math.floor(d.house_count! * 0.15) },
      { range: "200-300万", count: Math.floor(d.house_count! * 0.06) },
      { range: "300万以上", count: Math.floor(d.house_count! * 0.03) },
    ],
    area_distribution: [
      { range: "60㎡以下", count: Math.floor(d.house_count! * 0.12) },
      { range: "60-90㎡", count: Math.floor(d.house_count! * 0.32) },
      { range: "90-120㎡", count: Math.floor(d.house_count! * 0.30) },
      { range: "120-150㎡", count: Math.floor(d.house_count! * 0.18) },
      { range: "150㎡以上", count: Math.floor(d.house_count! * 0.08) },
    ],
    top_communities: [
      { name: name + "花园一期", count: 320, avg_price: d.avg_unit_price! * 1.1 },
      { name: name + "新城国际", count: 280, avg_price: d.avg_unit_price! * 1.3 },
      { name: "龙湖" + name + "项目", count: 250, avg_price: d.avg_unit_price! * 1.5 },
      { name: "万科" + name + "中心", count: 210, avg_price: d.avg_unit_price! * 0.9 },
      { name: "保利" + name + "公馆", count: 180, avg_price: d.avg_unit_price! * 1.2 },
    ],
  };
}
