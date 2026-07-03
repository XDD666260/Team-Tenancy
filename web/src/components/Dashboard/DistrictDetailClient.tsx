"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import type { DistrictDetail } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

const BAR_COLORS = ["#4a90e2", "#9b59b6", "#e91e63", "#ff5722", "#00bcd4", "#94ddde"];
const DONUT_COLORS = ["#4a90e2", "#9b59b6", "#e91e63", "#ff5722", "#00bcd4"];

export default function DistrictDetailClient({ detail }: { detail: DistrictDetail }) {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(".detail-section", { opacity: 0, y: 24 }, {
        opacity: 1, y: 0, duration: 0.7, ease: "power3.out", delay: 0.2,
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={sectionRef} className="mx-auto max-w-4xl px-6 pb-24 sm:px-8">
      <div className="detail-section space-y-8">

        {/* ═══ 区县头部 ═══ */}
        <div className="pt-8">
          <span className="tag mb-5">区县详情</span>
          <h1 className="h1 mt-4" style={{ color: "var(--text-primary)", fontSize: "clamp(32px,6vw,56px)" }}>
            {detail.district}
          </h1>
          <p className="lead mt-3">
            {detail.house_count.toLocaleString("zh-CN")} 套在售房源 · 均价{" "}
            <span style={{ color: "var(--accent-mint)" }}>
              ¥{detail.avg_unit_price.toLocaleString("zh-CN")}/㎡
            </span>
          </p>
          <hr className="hr mt-10" />
        </div>

        {/* ═══ KPI 行 ═══ */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MiniKpi label="均价" value={`¥${detail.avg_unit_price.toLocaleString("zh-CN")}`} unit="/㎡" accent="var(--accent-mint)" />
          <MiniKpi label="套均总价" value={`¥${detail.avg_total_price.toFixed(1)}`} unit="万" accent="var(--accent-pink)" />
          <MiniKpi label="平均面积" value={detail.avg_area.toFixed(0)} unit="㎡" accent="#4a90e2" />
          <MiniKpi label="价格跨度" value={`¥${detail.min_price}`} unit={`— ¥${detail.max_price}`} accent="#ff5722" />
        </div>

        {/* ═══ 总价分布 + 面积分布 ═══ */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <Card title={`${detail.district} 总价分布`}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={detail.price_distribution} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36}>
                  {detail.price_distribution.map((_, i) => <Cell key={i} fill={BAR_COLORS[i]} fillOpacity={0.8} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title={`${detail.district} 面积分布`}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={detail.area_distribution} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="range" axisLine={false} tickLine={false} tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36}>
                  {detail.area_distribution.map((_, i) => <Cell key={i} fill={BAR_COLORS[i]} fillOpacity={0.8} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* ═══ 装修 + 户型 ═══ */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <Card title="装修分布">
            <div className="flex items-center gap-4">
              <div className="h-52 w-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={detail.decoration_distribution.map((d) => ({ name: d.type, value: d.count }))}
                      cx="50%" cy="50%" innerRadius="52%" outerRadius="80%" paddingAngle={3}
                      dataKey="value" stroke="transparent">
                      {detail.decoration_distribution.map((_, i) => <Cell key={i} fill={DONUT_COLORS[i]} fillOpacity={0.8} />)}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-2">
                {detail.decoration_distribution.map((d, i) => (
                  <div key={d.type} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: DONUT_COLORS[i] }} />
                    <span className="text-xs" style={{ color: "#aaaaaa" }}>{d.type}</span>
                    <span className="font-mono-data text-xs" style={{ color: "#ffffff" }}>{d.count.toLocaleString("zh-CN")}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card title="户型分布">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={detail.layout_distribution} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="rooms" axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} tickFormatter={(v: number) => v + "室"} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {detail.layout_distribution.map((_, i) => <Cell key={i} fill={BAR_COLORS[i]} fillOpacity={0.8} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* ═══ TOP 小区 ═══ */}
        <Card title="热门小区 TOP 5">
          <div className="space-y-1">
            {detail.top_communities.map((c, i) => (
              <div key={c.name} className="flex items-center gap-3 rounded-lg px-4 py-3.5"
                style={{ background: i === 0 ? "rgba(74,144,226,0.06)" : "transparent" }}>
                <span className="font-mono-data text-sm" style={{ color: i === 0 ? "#4a90e2" : "#666666", minWidth: 20 }}>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="flex-1 text-sm" style={{ color: "#dddddd", fontWeight: i === 0 ? 500 : 300 }}>{c.name}</span>
                <span className="font-mono-data text-xs" style={{ color: "#888888" }}>{c.count} 套</span>
                <span className="font-mono-data text-sm" style={{ color: "var(--accent-mint)", minWidth: 80, textAlign: "right" }}>
                  ¥{c.avg_price.toLocaleString("zh-CN")}/㎡
                </span>
              </div>
            ))}
          </div>
        </Card>

      </div>
    </div>
  );
}

function MiniKpi({ label, value, unit, accent }: { label: string; value: string; unit: string; accent: string }) {
  return (
    <div className="card-dark" style={{ padding: 20 }}>
      <p className="stat-label mb-2" style={{ fontSize: 11 }}>{label}</p>
      <p className="font-mono-data text-xl" style={{ color: accent, fontWeight: 500 }}>{value}</p>
      <p className="caption mt-0.5">{unit}</p>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card-dark" style={{ padding: 24 }}>
      <h3 className="h3 mb-5" style={{ color: "var(--text-primary)" }}>{title}</h3>
      {children}
    </div>
  );
}
