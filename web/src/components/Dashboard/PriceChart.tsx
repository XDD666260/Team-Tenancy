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
import type { PriceBin } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

const BAR_COLORS = [
  "#2b4b82",
  "#392752",
  "#6e426a",
  "#a0637f",
  "#ce8992",
  "#94ddde",
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
        { opacity: 0, y: 30 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          ease: "power3.out",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top 80%",
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  const data = activeTab === "unit" ? unitPriceBins : totalPriceBins;
  const xKey = "range";
  const title =
    activeTab === "unit" ? "单价分布 (元/㎡)" : "总价分布 (万元)";

  return (
    <section
      ref={sectionRef}
      className="relative mx-auto max-w-6xl px-4 pb-16 sm:px-6 lg:px-8"
    >
      <div className="glass-card p-6 sm:p-8">
        {/* 标题行 */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2
            className="text-lg font-light tracking-wider sm:text-xl"
            style={{ color: "var(--color-text)" }}
          >
            {title}
          </h2>

          {/* Tab 切换 */}
          <div
            className="inline-flex rounded-full p-0.5"
            style={{ background: "rgba(255,255,255,0.06)" }}
          >
            {[
              { key: "unit", label: "单价" },
              { key: "total", label: "总价" },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as "unit" | "total")}
                className="rounded-full px-5 py-2 text-xs font-light tracking-wider transition-all duration-300"
                style={
                  activeTab === tab.key
                    ? {
                        background: "rgba(148,221,222,0.15)",
                        color: "var(--color-mint)",
                      }
                    : {
                        background: "transparent",
                        color: "var(--color-text-hint)",
                      }
                }
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* 图表 */}
        <div className="h-72 sm:h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
              barCategoryGap="20%"
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />
              <XAxis
                dataKey={xKey}
                axisLine={false}
                tickLine={false}
                tick={{
                  fill: "rgba(255,255,255,0.4)",
                  fontSize: 11,
                  fontWeight: 300,
                }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{
                  fill: "rgba(255,255,255,0.4)",
                  fontSize: 11,
                  fontWeight: 300,
                }}
                tickFormatter={(v: number) =>
                  v >= 10000 ? (v / 10000).toFixed(0) + "万" : String(v)
                }
              />
              <Tooltip
                contentStyle={{
                  background: "rgba(26,26,46,0.95)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 12,
                  backdropFilter: "blur(12px)",
                  color: "#fff",
                  fontSize: 13,
                  fontWeight: 300,
                }}
                cursor={{ fill: "rgba(255,255,255,0.03)" }}
                formatter={(value) => {
                  const v = Number(value);
                  return [v.toLocaleString("zh-CN") + " 套", "房源数量"];
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={48}>
                {data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={BAR_COLORS[i % BAR_COLORS.length]}
                    fillOpacity={0.75}
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
