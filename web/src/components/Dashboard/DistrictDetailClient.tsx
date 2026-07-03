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
      gsap.fromTo(
        ".detail-section",
        { opacity: 0, y: 24 },
        { opacity: 1, y: 0, duration: 0.7, ease: "power3.out", delay: 0.2 }
      );
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  return (
    <div ref={sectionRef} className="mx-auto max-w-4xl px-4 pb-20 sm:px-6">
      <div className="detail-section space-y-6">

        {/* ═══ 区县头部 ═══ */}
        <div className="pt-6">
          <h1 className="text-3xl font-medium tracking-wider sm:text-4xl"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            {detail.district}
          </h1>
          <p className="mt-2 text-sm" style={{ color: "#aaaaaa", fontSize: 14 }}>
            {detail.house_count.toLocaleString("zh-CN")} 套在售房源
          </p>
        </div>

        {/* ═══ KPI 行 ═══ */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MiniKpi label="均价" value={`¥${detail.avg_unit_price.toLocaleString("zh-CN")}`} unit="/㎡" accent="var(--color-mint)" />
          <MiniKpi label="套均总价" value={`¥${detail.avg_total_price.toFixed(1)}`} unit="万" accent="var(--color-pink-light)" />
          <MiniKpi label="平均面积" value={detail.avg_area.toFixed(0)} unit="㎡" accent="#4a90e2" />
          <MiniKpi label="价格区间" value={`¥${detail.min_price}`} unit={`— ¥${detail.max_price}`} accent="#ff5722" />
        </div>

        {/* ═══ 双图：价格分布 + 面积分布 ═══ */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ChartCard title={`${detail.district} 总价分布`}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={detail.price_distribution} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="range" axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <YAxis axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36}>
                  {detail.price_distribution.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i]} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title={`${detail.district} 面积分布`}>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={detail.area_distribution} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="range" axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <YAxis axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36}>
                  {detail.area_distribution.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i]} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* ═══ 装修分布 + 户型分布 ═══ */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ChartCard title="装修分布">
            <div className="flex items-center gap-4">
              <div className="h-52 w-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={detail.decoration_distribution.map((d) => ({ name: d.type, value: d.count }))}
                      cx="50%" cy="50%" innerRadius="52%" outerRadius="80%" paddingAngle={3}
                      dataKey="value" stroke="transparent">
                      {detail.decoration_distribution.map((_, i) => (
                        <Cell key={i} fill={DONUT_COLORS[i]} fillOpacity={0.8} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-2">
                {detail.decoration_distribution.map((d, i) => (
                  <div key={d.type} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: DONUT_COLORS[i] }} />
                    <span className="text-xs font-light" style={{ color: "#aaaaaa" }}>{d.type}</span>
                    <span className="font-mono-data text-xs font-medium">{d.count.toLocaleString("zh-CN")}</span>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>

          <ChartCard title="户型分布">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={detail.layout_distribution} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="rooms" axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }}
                  tickFormatter={(v: number) => v + "室"} />
                <YAxis axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 10, fontWeight: 300 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={40}>
                  {detail.layout_distribution.map((_, i) => (
                    <Cell key={i} fill={BAR_COLORS[i]} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>

        {/* ═══ TOP 小区 ═══ */}
        <ChartCard title="热门小区 TOP 5">
          <div className="space-y-2">
            {detail.top_communities.map((c, i) => (
              <div key={c.name} className="flex items-center gap-3 rounded-xl px-4 py-3"
                style={{ background: i === 0 ? "rgba(74,144,226,0.08)" : "transparent" }}>
                <span className="font-mono-data text-sm font-medium"
                  style={{ color: i === 0 ? "#4a90e2" : "#888888", minWidth: 20 }}>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="flex-1 text-sm font-medium">{c.name}</span>
                <span className="font-mono-data text-sm" style={{ color: "#aaaaaa" }}>
                  {c.count} 套
                </span>
                <span className="font-mono-data text-sm font-medium" style={{ color: "var(--color-mint)", minWidth: 72, textAlign: "right" }}>
                  ¥{c.avg_price.toLocaleString("zh-CN")}/㎡
                </span>
              </div>
            ))}
          </div>
        </ChartCard>

      </div>
    </div>
  );
}

function MiniKpi({ label, value, unit, accent }: { label: string; value: string; unit: string; accent: string }) {
  return (
    <div className="rounded-2xl p-4" style={{
      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
      backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
    }}>
      <p className="text-xs font-light" style={{ color: "#888888", fontSize: 12 }}>{label}</p>
      <p className="mt-1.5 font-mono-data text-xl font-medium" style={{ color: accent }}>
        {value}
      </p>
      <p className="text-xs font-light" style={{ color: "#666666", fontSize: 12 }}>{unit}</p>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="p-5 sm:p-6" style={{
      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 16, backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
    }}>
      <h3 className="mb-4 text-sm font-medium tracking-wider"
        style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

