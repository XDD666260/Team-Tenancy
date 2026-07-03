"use client";

import { useRef, useEffect, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, LabelList,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import type { PriceBin } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

/* [UI-OPTIMIZE] 高饱和渐变色柱状图 */
const VIBRANT_COLORS = [
  "#4a90e2", // 亮蓝
  "#9b59b6", // 紫
  "#e91e63", // 粉紫
  "#ff5722", // 橙红
  "#00bcd4", // 青
  "#94ddde", // 薄荷绿
];

interface Props {
  unitPriceBins: PriceBin[];
  totalPriceBins: PriceBin[];
}

export default function PriceChart({ unitPriceBins, totalPriceBins }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const [activeTab, setActiveTab] = useState<"unit" | "total">("unit");
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    const ctx = gsap.context(() => {
      gsap.fromTo(sectionRef.current, { opacity: 0, y: 30 }, {
        opacity: 1, y: 0, duration: 0.8, ease: "power3.out",
        scrollTrigger: { trigger: sectionRef.current, start: "top 85%" },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  const data = activeTab === "unit" ? unitPriceBins : totalPriceBins;

  return (
    <section ref={sectionRef} className="relative mx-auto max-w-6xl px-4 pb-[30px] sm:px-6 lg:px-8">
      {/* [UI-OPTIMIZE] 磨砂玻璃容器 */}
      <div className="glass-card">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="heading-md mb-1" style={{ color: "#ffffff" }}>
              {activeTab === "unit" ? "单价分布" : "总价分布"}
            </h2>
            <p className="body-text text-xs" style={{ color: "var(--color-text-hint)" }}>
              {activeTab === "unit" ? "各单价区间房源数量 (元/㎡)" : "各总价区间房源数量"}
            </p>
          </div>

          {/* [UI-OPTIMIZE] 胶囊 Tab */}
          <div className="inline-flex items-center rounded-full p-0.5"
            style={{ background: "rgba(255,255,255,0.05)" }}>
            {(["unit", "total"] as const).map((key) => {
              const isActive = activeTab === key;
              return (
                <button key={key} onClick={() => setActiveTab(key)}
                  className="rounded-full px-6 py-2 text-sm tracking-wider transition-all duration-300"
                  style={{
                    background: isActive ? "rgba(148,221,222,0.15)" : "transparent",
                    color: isActive ? "var(--color-mint)" : "var(--color-text-hint)",
                    fontWeight: isActive ? 500 : 300,
                  }}>
                  {key === "unit" ? "单价" : "总价"}
                </button>
              );
            })}
          </div>
        </div>

        <div className="h-72 sm:h-[360px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 20, right: 16, left: -16, bottom: 0 }}
              barCategoryGap="22%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="range" axisLine={false} tickLine={false}
                tick={{ fill: "var(--color-text-hint)", fontSize: 12, fontWeight: 300 }} />
              <YAxis axisLine={false} tickLine={false}
                tick={{ fill: "var(--color-text-hint)", fontSize: 12, fontWeight: 300 }}
                tickFormatter={(v: number) => v >= 10000 ? (v / 10000).toFixed(0) + "万" : String(v)} />
              <Tooltip content={<ChartTooltip />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={52}
                /* [UI-OPTIMIZE] hover 放大+阴影 */
                onMouseEnter={(_, idx) => {
                  const bars = document.querySelectorAll(".price-bar-rect");
                  bars.forEach((b, i) => {
                    const el = b as SVGElement;
                    el.style.filter = i === idx ? "brightness(1.25) drop-shadow(0 4px 14px rgba(0,0,0,0.5))" : "";
                    el.style.opacity = i === idx ? "1" : "0.45";
                  });
                }}
                onMouseLeave={() => {
                  document.querySelectorAll(".price-bar-rect").forEach((b) => {
                    const el = b as SVGElement;
                    el.style.filter = ""; el.style.opacity = "1";
                  });
                }}>
                {/* [UI-OPTIMIZE] 柱顶数据标签 */}
                <LabelList dataKey="count" position="top"
                  formatter={(v: unknown) => {
                    const n = Number(v);
                    return n >= 1000 ? (n / 1000).toFixed(1) + "k" : String(n);
                  }}
                  style={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }} />
                {data.map((_, i) => (
                  <Cell key={i} className="price-bar-rect"
                    fill={VIBRANT_COLORS[i % VIBRANT_COLORS.length]} fillOpacity={0.82} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
