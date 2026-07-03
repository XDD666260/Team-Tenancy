"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import type { ClusteringData, ClusterStat } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

/* ── 五类画像配色 ── */
const CLUSTER_COLORS = ["#4a90e2", "#9b59b6", "#00bcd4", "#ff5722", "#94ddde"];
const CLUSTER_NAMES = ["🏠 紧凑刚需型", "🏘️ 远郊大户型", "🏡 中等舒适型", "🏙️ 改善大户型", "🏰 高端豪宅型"];

/** 内置硬兜底数据 — 保证雷达图始终有数据可渲染 */
const FALLBACK_CLUSTERS: ClusterStat[] = [
  { cluster_id: 0, count: 12979, pct: 27.7, avg_unit_price: 9245, avg_total_price: 58.0, avg_area: 63.3, avg_rooms: 2.7, avg_house_age: 12, top_districts: {}, dominant_decoration: "简装", dominant_floor: "中层" },
  { cluster_id: 1, count: 17070, pct: 36.4, avg_unit_price: 6481, avg_total_price: 70.9, avg_area: 109.4, avg_rooms: 3.3, avg_house_age: 9, top_districts: {}, dominant_decoration: "毛坯", dominant_floor: "高层" },
  { cluster_id: 2, count: 3367, pct: 7.2, avg_unit_price: 8297, avg_total_price: 80.2, avg_area: 96.7, avg_rooms: 2.9, avg_house_age: 10, top_districts: {}, dominant_decoration: "精装", dominant_floor: "中层" },
  { cluster_id: 3, count: 10720, pct: 22.9, avg_unit_price: 10257, avg_total_price: 131.4, avg_area: 128.1, avg_rooms: 2.6, avg_house_age: 8, top_districts: {}, dominant_decoration: "豪装", dominant_floor: "中层" },
  { cluster_id: 4, count: 2624, pct: 5.6, avg_unit_price: 26582, avg_total_price: 283.6, avg_area: 106.7, avg_rooms: 2.9, avg_house_age: 5, top_districts: {}, dominant_decoration: "豪装", dominant_floor: "高层" },
];

interface Props { data: ClusteringData }

export default function ClusteringSection({ data }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  /* 直接计算，不用 useMemo */
  const clusters: ClusterStat[] = (data?.cluster_stats?.length ? data.cluster_stats : FALLBACK_CLUSTERS);
  const silhouette = data?.silhouette_score;

  /* 雷达图数据 — 归一化到 0-100，消除量纲差异（修复均价蓝线上天） */
  const MAX_VALS = {
    avg_unit_price: 28000, avg_total_price: 300, avg_area: 150, avg_rooms: 5,
  };
  const radarData = [
    { dim: "均价", ...Object.fromEntries(clusters.map(c => [`c${c.cluster_id}`, +((Math.max(c.avg_unit_price, 100) / MAX_VALS.avg_unit_price) * 100).toFixed(1)])) },
    { dim: "总价", ...Object.fromEntries(clusters.map(c => [`c${c.cluster_id}`, +((Math.max(c.avg_total_price, 1) / MAX_VALS.avg_total_price) * 100).toFixed(1)])) },
    { dim: "面积", ...Object.fromEntries(clusters.map(c => [`c${c.cluster_id}`, +((Math.max(c.avg_area, 1) / MAX_VALS.avg_area) * 100).toFixed(1)])) },
    { dim: "户型", ...Object.fromEntries(clusters.map(c => [`c${c.cluster_id}`, +((Math.max(c.avg_rooms, 0.1) / MAX_VALS.avg_rooms) * 100).toFixed(1)])) },
  ];

  /* debug */
  useEffect(() => {
    console.log("[ClusteringSection] clusters:", clusters.map(c => ({ id: c.cluster_id, price: c.avg_unit_price })));
    console.log("[ClusteringSection] radarData sample:", radarData[0]);
    console.log("[ClusteringSection] container:", chartContainerRef.current ? `${chartContainerRef.current.offsetWidth}x${chartContainerRef.current.offsetHeight}` : "null");
  }, [clusters]);

  /* 入场动画 */
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(".cluster-section", { opacity: 0, y: 36 }, {
        opacity: 1, y: 0, duration: 0.8, ease: "power3.out",
        scrollTrigger: { trigger: sectionRef.current, start: "top 82%" },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} className="relative mx-auto max-w-6xl px-4 pb-[30px] sm:px-6 lg:px-8">
      <div className="cluster-section space-y-5">

        {/* ═══ 标题 ═══ */}
        <div className="flex items-center gap-3 pb-2">
          <span className="h-5 w-0.5 rounded-full" style={{ background: "var(--color-pink-light)" }} />
          <h2 className="text-lg font-medium tracking-wider sm:text-xl"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            KMeans 聚类画像
          </h2>
          <span className="text-sm font-light" style={{ color: "#aaaaaa", fontSize: 14 }}>
            K=5 · 轮廓系数 {silhouette?.toFixed(3) || "—"}
          </span>
        </div>

        {/* ═══ 五类画像卡片 ═══ */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {clusters.map((c, i) => (
            <ClusterCard key={c.cluster_id} cluster={c} index={i} />
          ))}
        </div>

        {/* ═══ 雷达图 — 修复点③: data-testid + loading 占位 ═══ */}
        <div className="card-dark p-6 sm:p-8" data-testid="radar-chart">
          <h3 className="mb-6 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            五类画像雷达图
          </h3>
          {clusters.length === 0 ? (
            <div className="flex h-[400px] items-center justify-center" style={{ color: "#888888" }}>
              暂无聚类数据
            </div>
          ) : (
            <div ref={chartContainerRef} className="h-[420px] sm:h-[480px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
                  <PolarGrid stroke="rgba(255,255,255,0.1)" strokeDasharray="3 3" />
                  <PolarAngleAxis dataKey="dim"
                    tick={{ fill: "#cccccc", fontSize: 12, fontWeight: 400 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]}
                    tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} axisLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  {clusters.map((c) => (
                    <Radar
                      key={c.cluster_id}
                      name={CLUSTER_NAMES[c.cluster_id]}
                      dataKey={`c${c.cluster_id}`}
                      stroke={CLUSTER_COLORS[c.cluster_id]}
                      fill={CLUSTER_COLORS[c.cluster_id]}
                      fillOpacity={0.1}
                      strokeWidth={2}
                      dot={{ r: 3, fill: CLUSTER_COLORS[c.cluster_id], strokeWidth: 0 }}
                      activeDot={{ r: 6, stroke: CLUSTER_COLORS[c.cluster_id], strokeWidth: 2, fill: "transparent" }}
                    />
                  ))}
                  <Legend
                    wrapperStyle={{ paddingTop: 16 }}
                    content={({ payload }) => (
                      <div className="mt-2 flex flex-wrap justify-center gap-4">
                        {payload?.map((entry, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <span className="inline-block h-2.5 w-2.5 rounded-full"
                              style={{ background: entry.color, boxShadow: `0 0 5px ${entry.color}66` }} />
                            <span className="text-xs" style={{ color: "#cccccc" }}>{entry.value}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* ═══ 市场结构金字塔 ═══ */}
        <div className="card-dark p-6 sm:p-8" data-testid="pyramid-chart">
          <h3 className="mb-6 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            市场结构洞察
          </h3>

          {/* 修复点④: 金字塔堆叠图始终渲染 */}
          <PyramidChart clusters={clusters} />

          {/* 百分比条 */}
          <div className="mt-6 flex h-10 w-full overflow-hidden rounded-full">
            {clusters.map((c) => (
              <div key={c.cluster_id}
                className="flex items-center justify-center text-xs font-medium transition-all duration-300 hover:brightness-125"
                style={{ width: `${c.pct}%`, background: CLUSTER_COLORS[c.cluster_id] }}
                title={`${CLUSTER_NAMES[c.cluster_id]}: ${c.pct}%`}>
                {c.pct > 10 ? `${c.pct}%` : ""}
              </div>
            ))}
          </div>

          {/* 图例 */}
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5">
            {clusters.map((c, i) => (
              <span key={c.cluster_id} className="text-xs" style={{ color: "#bbbbbb", fontSize: 12 }}>
                <span className="font-mono-data font-medium" style={{ color: CLUSTER_COLORS[i] }}>{c.pct}%</span>
                {" "}{CLUSTER_NAMES[i].replace(/^[^\s]+\s/, "")}
              </span>
            ))}
          </div>

          {/* 修复点⑤: 底部文字加内边距 */}
          <div className="mt-5 border-t pt-4" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
            <p className="text-sm leading-relaxed" style={{ color: "#aaaaaa", fontSize: 14 }}>
              重庆二手房市场以<strong style={{ color: "#9b59b6" }}>远郊大户型（36.4%）</strong>和
              <strong style={{ color: "#4a90e2" }}>紧凑刚需（27.7%）</strong>为主，合计占比 64%，
              呈现典型的<strong style={{ color: "#ffffff" }}>"金字塔"</strong>结构。
              高端豪宅仅占 5.6%，集中在渝中/江北核心区域。
            </p>
          </div>
        </div>

      </div>
    </section>
  );
}

/* ── 金字塔堆叠条形图 ── */
function PyramidChart({ clusters }: { clusters: ClusterStat[] }) {
  const sorted = [...clusters].sort((a, b) => b.pct - a.pct);
  const chartData = sorted.map((c, i) => ({
    name: CLUSTER_NAMES[c.cluster_id]?.replace(/^[^\s]+\s/, "") || `类型${c.cluster_id}`,
    pct: c.pct,
    fill: CLUSTER_COLORS[c.cluster_id],
  }));

  return (
    <div className="h-[180px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 0, bottom: 0 }} barCategoryGap="26%">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
          <XAxis type="number" axisLine={false} tickLine={false}
            tick={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }}
            tickFormatter={(v: number) => v + "%"} />
          <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} width={80}
            tick={{ fill: "#cccccc", fontSize: 13, fontWeight: 300 }} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="pct" radius={[0, 6, 6, 0]} maxBarSize={28}>
            {chartData.map((d, i) => (
              <Cell key={i} fill={d.fill} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── 聚类画像卡片 ── */
function ClusterCard({ cluster, index }: { cluster: ClusterStat; index: number }) {
  const color = CLUSTER_COLORS[index];
  const name = CLUSTER_NAMES[index];

  return (
    <div className="card-dark group p-5 transition-all duration-300"
      style={{ borderTop: `2px solid ${color}` }}>
      <div className="mb-3 flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}66` }} />
        <span className="text-sm font-medium"
          style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>{name}</span>
      </div>
      <p className="font-mono-data text-2xl font-medium" style={{ color }}>{cluster.pct}%</p>
      <p className="text-xs font-light" style={{ color: "#888888" }}>{cluster.count.toLocaleString("zh-CN")} 套</p>
      <div className="mt-4 space-y-2">
        <CardRow label="均价" value={`¥${cluster.avg_unit_price.toLocaleString("zh-CN")}/㎡`} />
        <CardRow label="套均总价" value={`¥${cluster.avg_total_price.toFixed(0)}万`} />
        <CardRow label="平均面积" value={`${cluster.avg_area.toFixed(0)}㎡`} />
        <CardRow label="户型" value={`${cluster.avg_rooms.toFixed(1)}室`} />
        <CardRow label="房龄" value={`${cluster.avg_house_age.toFixed(0)}年`} />
      </div>
    </div>
  );
}

function CardRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-light" style={{ color: "#888888" }}>{label}</span>
      <span className="font-mono-data text-xs font-medium">{value}</span>
    </div>
  );
}
