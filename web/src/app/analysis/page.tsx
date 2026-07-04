"use client";

import { useState, useEffect } from "react";
import SmoothScroll from "@/components/SmoothScroll";
import StatsHero from "@/components/Dashboard/StatsHero";
import DistrictRanking from "@/components/Dashboard/DistrictRanking";
import PredictionSection from "@/components/Dashboard/PredictionSection";
import ClusteringSection from "@/components/Dashboard/ClusteringSection";
import AssociationSection from "@/components/Dashboard/AssociationSection";
import type { OverviewData, PredictionData, ClusteringData } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── 兜底数据（后端不可用时展示） ── */
const FALLBACK_OVERVIEW: OverviewData = {
  total_houses: 54993,
  avg_unit_price: 8426,
  avg_total_price: 84.5,
  max_unit_price: 26582,
  min_unit_price: 3240,
  district_count: 39,
  update_time: "2026-07",
  by_source: { anjuke: 12225, lianjia: 526, augmented: 42242 },
  by_district: [],
};

export default function AnalysisPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [clustering, setClustering] = useState<ClusteringData | null>(null);
  const [association, setAssociation] = useState<{ rules: any[]; total_rules: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiOnline, setApiOnline] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      // 先探活
      try {
        const hc = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
        if (hc.ok) setApiOnline(true);
      } catch { /* 后端离线，用 fallback */ }

      // 并行拉取
      const fetchJSON = async (path: string) => {
        try {
          const res = await fetch(`${API_BASE}${path}`, { signal: AbortSignal.timeout(8000) });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const json = await res.json();
          return json.data ?? json;
        } catch { return null; }
      };

      const [ov, pr, cl, as] = await Promise.all([
        fetchJSON("/api/stats/overview"),
        fetchJSON("/api/analysis/prediction"),
        fetchJSON("/api/analysis/clustering"),
        fetchJSON("/api/analysis/association-rules"),
      ]);

      if (cancelled) return;

      setOverview(ov || FALLBACK_OVERVIEW);
      setPrediction(pr || { models: {}, feature_importance: {} });
      setClustering(cl || { n_clusters: 5, inertia_: 0, silhouette_score: null, cluster_stats: [] });
      setAssociation(as || { rules: [], total_rules: 0 });
      setLoading(false);
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const ov = overview || FALLBACK_OVERVIEW;

  return (
    <SmoothScroll>
      <main style={{ background: "var(--bg-primary)" }}>

        {/* ── 页面标题 ── */}
        <div className="mx-auto max-w-6xl px-6 pt-28 sm:px-8 lg:px-10">
          <span className="tag mb-6">Dashboard</span>
          <h1 className="h1 mb-4" style={{ color: "var(--text-primary)" }}>
            2026重庆二手房<br />数据洞察
          </h1>
          <p className="lead max-w-2xl">
            基于{" "}
            <span style={{ color: "var(--accent-pink)" }}>
              {loading ? "..." : ov.total_houses.toLocaleString("zh-CN")}
            </span>{" "}
            条房源数据，覆盖重庆{" "}
            <span style={{ color: "var(--accent-mint)" }}>{ov.district_count}+</span> 个区县，
            运用机器学习方法深度剖析市场结构与价格规律。
          </p>
          <p className="lead teamNumber">
            学年设计第36小组：胡霖、王宇、解金明
          </p>
          {apiOnline && (
            <p className="text-xs mt-2" style={{ color: "var(--color-mint)" }}>
              ● 已连接后端 API · 数据更新时间：{ov.update_time || "—"}
            </p>
          )}
          {!apiOnline && !loading && (
            <p className="text-xs mt-2" style={{ color: "#ff8a65" }}>
              ◉ 后端未连接，展示静态演示数据
            </p>
          )}
        </div>

        {/* ── 核心数据带 ── */}
        <StatsHero stats={[
          { value: loading ? "..." : ov.total_houses.toLocaleString("zh-CN"), label: "在售房源 / 条" },
          { value: loading ? "..." : ov.avg_unit_price.toLocaleString("zh-CN"), label: "均价 / 元/㎡" },
          { value: String(ov.district_count), label: "覆盖区县 / 个" },
          { value: loading ? "..." : "0.49", label: "预测模型 R²" },
          { value: "5", label: "市场细分 / 类" },
        ]} />

        {/* ── 房价预测分析 ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">机器学习</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              房价预测模型
            </h2>
            <p className="lead mt-3 max-w-2xl">
              面积 + 地段（小区/区县）解释房价变化，总价预测 R²=0.49、MAE=29.7万。
            </p>
          </div>
        </div>
        {loading ? <Skeleton height={500} /> : <PredictionSection data={prediction!} />}

        {/* ── KMeans 聚类 ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">无监督学习</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              KMeans 聚类画像
            </h2>
            <p className="lead mt-3 max-w-2xl">
              五类市场画像：刚需（小户型28% + 紧凑11%）+ 远郊大户型29% + 改善17% + 高端15%。
            </p>
          </div>
        </div>
        {loading ? <Skeleton height={500} /> : <ClusteringSection data={clustering!} />}

        {/* ── 关联规则 ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">关联挖掘</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              关联规则挖掘
            </h2>
            <p className="lead mt-3 max-w-2xl">
              Apriori 算法发现高质量关联规则。
            </p>
          </div>
        </div>
        {loading ? <Skeleton height={400} /> : <AssociationSection data={association!} />}

        {/* ── 区县排名 ── */}
        <div className="mx-auto max-w-6xl px-6 py-4 sm:px-8 lg:px-10">
          <hr className="hr mb-16" />
          <div className="mb-10">
            <span className="tag mb-5">地理分布</span>
            <h2 className="h2 mt-4" style={{ color: "var(--text-primary)" }}>
              区县房源排名
            </h2>
            <p className="lead mt-3 max-w-2xl">
              渝中区均价领跑全市。点击柱状图查看区县详情。
            </p>
          </div>
          <div className="card-dark" style={{ padding: 32 }}>
            <DistrictRanking districts={ov.by_district} />
          </div>
        </div>

        {/* ── 底部 ── */}
        <div className="mx-auto max-w-6xl px-6 pb-32 pt-8 sm:px-8 lg:px-10">
          <hr className="hr mb-10" />
          <p className="caption text-center">
            数据来源：安居客 · 链家 | 更新时间：{ov.update_time || "—"} |
            分析框架：RandomForest · GradientBoosting · KMeans · Apriori
          </p>
        </div>

      </main>
    </SmoothScroll>
  );
}

/** 加载骨架屏 */
function Skeleton({ height }: { height: number }) {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-8 sm:px-6 lg:px-8">
      <div
        className="animate-pulse rounded-2xl"
        style={{
          height,
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.05)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span style={{ color: "#888888", fontSize: 14 }}>加载中...</span>
      </div>
    </section>
  );
}
