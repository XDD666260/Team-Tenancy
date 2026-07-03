"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, Tooltip, ResponsiveContainer, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import type { ClusteringData, ClusterStat } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

/* ── 五类画像配色 ── */
const CLUSTER_COLORS = ["#4a90e2", "#9b59b6", "#00bcd4", "#ff5722", "#94ddde"];
const CLUSTER_NAMES = ["🏠 紧凑刚需型", "🏘️ 远郊大户型", "🏡 中等舒适型", "🏙️ 改善大户型", "🏰 高端豪宅型"];

/* 雷达图维度 */
const RADAR_DIMS = [
  { key: "avg_unit_price", label: "均价", max: 30000 },
  { key: "avg_total_price", label: "总价(万)", max: 300 },
  { key: "avg_area", label: "面积(㎡)", max: 150 },
  { key: "avg_rooms", label: "户型(室)", max: 5 },
];

interface Props {
  data: ClusteringData;
}

export default function ClusteringSection({ data }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);

  const clusters = data?.cluster_stats || [];

  /* ── 雷达图数据 ── */
  const radarData = RADAR_DIMS.map((dim) => {
    const entry: Record<string, number | string> = { dimension: dim.label };
    clusters.forEach((c) => {
      const raw = +(c as unknown as Record<string, number>)[dim.key] || 0;
      entry[`聚类${c.cluster_id}`] = Math.min(raw, dim.max);
    });
    return entry;
  });

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
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
            K=5 · 轮廓系数 {data.silhouette_score?.toFixed(3) || "—"}
          </span>
        </div>

        {/* ═══ 五类画像卡片 ═══ */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {clusters.map((c, i) => (
            <ClusterCard key={c.cluster_id} cluster={c} index={i} />
          ))}
        </div>

        {/* ═══ 雷达图 ═══ */}
        <div className="glass-card p-6 sm:p-8">
          <h3 className="mb-6 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            五类画像雷达图
          </h3>
          <div className="h-[420px] sm:h-[480px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fill: "#aaaaaa", fontSize: 13, fontWeight: 300 }}
                />
                <PolarRadiusAxis
                  angle={30}
                  domain={[0, "auto"]}
                  tick={{ fill: "rgba(255,255,255,0.25)", fontSize: 10 }}
                  axisLine={false}
                />
                <Tooltip content={<ChartTooltip />} />
                {clusters.map((c) => (
                  <Radar
                    key={c.cluster_id}
                    name={CLUSTER_NAMES[c.cluster_id]}
                    dataKey={`聚类${c.cluster_id}`}
                    stroke={CLUSTER_COLORS[c.cluster_id]}
                    fill={CLUSTER_COLORS[c.cluster_id]}
                    fillOpacity={0.08}
                    strokeWidth={2}
                    strokeOpacity={0.9}
                  />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          </div>
          {/* 图例 */}
          <div className="mt-2 flex flex-wrap justify-center gap-5">
            {clusters.map((c) => (
              <div key={c.cluster_id} className="flex items-center gap-2">
                <span className="inline-block h-3 w-3 rounded-full"
                  style={{ background: CLUSTER_COLORS[c.cluster_id], boxShadow: `0 0 6px ${CLUSTER_COLORS[c.cluster_id]}66` }} />
                <span className="text-xs font-light" style={{ color: "#cccccc" }}>
                  {CLUSTER_NAMES[c.cluster_id]}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ 市场结构：金字塔 + 洞察 ═══ */}
        <div className="glass-card p-6 sm:p-8">
          <h3 className="mb-6 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            市场结构洞察
          </h3>

          {/* 金字塔堆叠条 */}
          <div className="mb-6">
            <PyramidChart clusters={clusters} />
          </div>

          {/* 占比条 */}
          <div className="flex h-10 w-full overflow-hidden rounded-full">
            {clusters.map((c) => (
              <div
                key={c.cluster_id}
                className="flex items-center justify-center text-xs font-medium transition-all duration-300 hover:brightness-125"
                style={{ width: `${c.pct}%`, background: CLUSTER_COLORS[c.cluster_id] }}
                title={`${CLUSTER_NAMES[c.cluster_id]}: ${c.pct}%`}
              >
                {c.pct > 10 ? `${c.pct}%` : ""}
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-4">
            {clusters.map((c) => (
              <span key={c.cluster_id} className="text-xs font-light" style={{ color: "#aaaaaa", fontSize: 12 }}>
                <span className="font-mono-data font-medium" style={{ color: CLUSTER_COLORS[c.cluster_id] }}>
                  {c.pct}%
                </span>
                {" "}{CLUSTER_NAMES[c.cluster_id].replace(/^[^\s]+\s/, "")}
              </span>
            ))}
          </div>
          <p className="mt-4 text-sm leading-relaxed" style={{ color: "#888888", fontSize: 14 }}>
            重庆二手房市场以<strong style={{ color: "#9b59b6" }}>远郊大户型（36.4%）</strong>和
            <strong style={{ color: "#4a90e2" }}>紧凑刚需（27.7%）</strong>为主，合计占比 64%，
            呈现典型的"金字塔"结构。高端豪宅仅占 5.6%，集中在渝中/江北核心区域。
          </p>
        </div>
      </div>
    </section>
  );
}

/* ── 金字塔堆叠条形图 ── */
function PyramidChart({ clusters }: { clusters: ClusterStat[] }) {
  /* 从大到小排列，打造金字塔视觉效果 */
  const sorted = [...clusters].sort((a, b) => b.pct - a.pct);
  const data = sorted.map((c, i) => ({
    name: CLUSTER_NAMES[c.cluster_id].replace(/^[^\s]+\s/, ""),
    pct: c.pct,
    count: c.count,
    fill: CLUSTER_COLORS[c.cluster_id],
  }));

  return (
    <div className="h-[180px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 40, left: 0, bottom: 0 }}
          barCategoryGap="30%">
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
          <XAxis type="number" axisLine={false} tickLine={false}
            tick={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }}
            tickFormatter={(v: number) => v + "%"} />
          <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} width={80}
            tick={{ fill: "#cccccc", fontSize: 12, fontWeight: 300 }} />
          <Tooltip content={<ChartTooltip />} />
          <Bar dataKey="pct" radius={[0, 6, 6, 0]} maxBarSize={28}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.fill} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── 单张聚类画像卡 ── */
function ClusterCard({ cluster, index }: { cluster: ClusterStat; index: number }) {
  const color = CLUSTER_COLORS[index];
  const name = CLUSTER_NAMES[index];

  return (
    <div
      className="group p-5 transition-all duration-300"
      style={{
        background: "rgba(255,255,255,0.04)", border: `1px solid ${color}22`,
        borderRadius: 16, backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)",
        borderTop: `2px solid ${color}`,
      }}
    >
      <div className="mb-3 flex items-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}66` }} />
        <span className="text-sm font-medium" style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
          {name}
        </span>
      </div>
      <p className="font-mono-data text-2xl font-medium" style={{ color }}>
        {cluster.pct}%
      </p>
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
