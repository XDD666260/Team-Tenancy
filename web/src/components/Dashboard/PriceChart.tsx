"use client";

import { useRef, useEffect, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import type { PriceBin } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

/* 高饱和渐变色 — 每个区间不同色彩 */
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
      gsap.fromTo(
        sectionRef.current,
        { opacity: 0, y: 36 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          ease: "power3.out",
          scrollTrigger: { trigger: sectionRef.current, start: "top 82%" },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  const data = activeTab === "unit" ? unitPriceBins : totalPriceBins;
  const title =
    activeTab === "unit" ? "单价分布" : "总价分布";

  return (
    <section ref={sectionRef} className="relative mx-auto max-w-6xl px-4 pb-[30px] sm:px-6 lg:px-8">
      <div className="glass-card p-6 sm:p-8">
        {/* 标题行 + 胶囊切换 */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2
            className="text-lg font-medium tracking-wider sm:text-xl"
            style={{
              fontFamily: '"PingFang SC", "Noto Sans SC", sans-serif',
              fontWeight: 500,
              color: "#ffffff",
            }}
          >
            {title}
            <span
              className="ml-3 text-sm font-light"
              style={{ color: "#aaaaaa", fontSize: 14 }}
            >
              (元/㎡)
            </span>
          </h2>

          {/* 胶囊型切换按钮 */}
          <div
            className="inline-flex items-center rounded-full p-0.5"
            style={{ background: "rgba(255,255,255,0.05)" }}
          >
            {[
              { key: "unit" as const, label: "单价" },
              { key: "total" as const, label: "总价" },
            ].map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className="rounded-full px-6 py-2 text-sm font-light tracking-wider transition-all duration-300"
                  style={{
                    background: isActive
                      ? "rgba(148,221,222,0.18)"
                      : "transparent",
                    color: isActive ? "var(--color-mint)" : "#aaaaaa",
                    fontWeight: isActive ? 500 : 300,
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 图表 */}
        <div className="h-72 sm:h-[340px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              margin={{ top: 8, right: 12, left: -16, bottom: 0 }}
              barCategoryGap="22%"
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.05)"
                vertical={false}
              />
              <XAxis
                dataKey="range"
                axisLine={false}
                tickLine={false}
                tick={{
                  fill: "#aaaaaa",
                  fontSize: 12,
                  fontWeight: 300,
                }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{
                  fill: "#aaaaaa",
                  fontSize: 12,
                  fontWeight: 300,
                }}
                tickFormatter={(v: number) =>
                  v >= 10000 ? (v / 10000).toFixed(0) + "万" : String(v)
                }
              />
              <Tooltip
                content={<ChartTooltip />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar
                dataKey="count"
                radius={[6, 6, 0, 0]}
                maxBarSize={52}
                // 悬停动画
                onMouseEnter={(_, index) => {
                  const bars = document.querySelectorAll(
                    ".recharts-bar-rectangle"
                  );
                  bars.forEach((bar, i) => {
                    const el = bar as HTMLElement;
                    if (i === index) {
                      el.style.filter = "brightness(1.3) drop-shadow(0 4px 12px rgba(0,0,0,0.5))";
                      el.style.transform = "scaleY(1.04)";
                      el.style.transformOrigin = "bottom";
                    } else {
                      el.style.opacity = "0.5";
                    }
                  });
                }}
                onMouseLeave={() => {
                  const bars = document.querySelectorAll(
                    ".recharts-bar-rectangle"
                  );
                  bars.forEach((bar) => {
                    const el = bar as HTMLElement;
                    el.style.filter = "";
                    el.style.transform = "";
                    el.style.opacity = "1";
                  });
                }}
              >
                {data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={VIBRANT_COLORS[i % VIBRANT_COLORS.length]}
                    fillOpacity={0.82}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
