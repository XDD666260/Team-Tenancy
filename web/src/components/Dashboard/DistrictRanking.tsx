"use client";

import { useRef, useEffect } from "react";
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
import type { DistrictStat } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

const RANK_COLORS = [
  "#94ddde", // #1 薄荷绿突出
  "#2b4b82",
  "#2b4b82",
  "#392752",
  "#392752",
  "#6e426a",
  "#6e426a",
  "#a0637f",
  "#a0637f",
  "#ce8992",
  "#ce8992",
  "#f0abc1",
  "#f0abc1",
  "#f7b4a7",
  "#f7b4a7",
];

interface Props {
  districts: DistrictStat[];
}

export default function DistrictRanking({ districts }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);

  // 取 TOP 15，反转让 Recharts 横向柱状图从上到下排列
  const data = [...districts].slice(0, 15).reverse();

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

  return (
    <section
      ref={sectionRef}
      className="relative mx-auto max-w-6xl px-4 pb-16 sm:px-6 lg:px-8"
    >
      <div className="glass-card p-6 sm:p-8">
        <div className="mb-6 flex items-center justify-between">
          <h2
            className="text-lg font-light tracking-wider sm:text-xl"
            style={{ color: "var(--color-text)" }}
          >
            区县房源排名
          </h2>
          <span
            className="text-xs font-light"
            style={{ color: "var(--color-text-hint)" }}
          >
            TOP 15
          </span>
        </div>

        <div className="h-[420px] sm:h-[480px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 0, right: 8, left: 8, bottom: 0 }}
              barCategoryGap="25%"
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                horizontal={false}
              />
              <XAxis
                type="number"
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
              <YAxis
                type="category"
                dataKey="district"
                axisLine={false}
                tickLine={false}
                width={72}
                tick={{
                  fill: "rgba(255,255,255,0.65)",
                  fontSize: 12,
                  fontWeight: 300,
                }}
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
                formatter={(value, _name, props) => {
                  const v = Number(value);
                  const district = (props.payload as DistrictStat).district;
                  const avgPrice = (props.payload as DistrictStat).avg_unit_price;
                  return [
                    `${v.toLocaleString("zh-CN")} 套`,
                    `${district} · 均价 ¥${avgPrice.toLocaleString("zh-CN")}/㎡`,
                  ];
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={22}>
                {data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={RANK_COLORS[i % RANK_COLORS.length]}
                    fillOpacity={0.8}
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
