"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import ChartTooltip from "./ChartTooltip";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

gsap.registerPlugin(ScrollTrigger);

/* 环形图色 — 高饱和对比 */
const DONUT_COLORS = ["#4a90e2", "#ff8a80"]; // 亮蓝 vs 粉橙

interface Props {
  bySource: Record<string, number>;
}

export default function SourceChart({ bySource }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);

  const data = Object.entries(bySource).map(([name, value]) => ({
    name,
    value,
  }));
  const total = data.reduce((sum, d) => sum + d.value, 0);

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

  return (
    <section ref={sectionRef} className="relative mx-auto max-w-6xl px-4 pb-28 sm:px-6 lg:px-8">
      <div className="card-dark p-6 sm:p-8">
        <h2
          className="mb-8 text-lg font-medium tracking-wider sm:text-xl"
          style={{
            fontFamily: '"PingFang SC", "Noto Sans SC", sans-serif',
            fontWeight: 500,
            color: "#ffffff",
          }}
        >
          数据来源分布
        </h2>

        <div className="flex flex-col items-center gap-8 lg:flex-row lg:justify-center">
          {/* 环形图 */}
          <div className="h-60 w-60 sm:h-72 sm:w-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius="58%"
                  outerRadius="84%"
                  paddingAngle={4}
                  dataKey="value"
                  stroke="transparent"
                >
                  {data.map((_, i) => (
                    <Cell
                      key={i}
                      fill={DONUT_COLORS[i]}
                      fillOpacity={0.85}
                    />
                  ))}
                </Pie>
                {/* 中心文字 */}
                <text
                  x="50%"
                  y="48%"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  style={{ pointerEvents: "none" }}
                >
                  <tspan
                    x="50%"
                    dy="-6"
                    className="font-mono-data"
                    style={{
                      fill: "#ffffff",
                      fontSize: 22,
                      fontWeight: 500,
                    }}
                  >
                    {total >= 10000
                      ? (total / 10000).toFixed(1) + "万"
                      : total.toLocaleString("zh-CN")}
                  </tspan>
                  <tspan
                    x="50%"
                    dy="22"
                    style={{ fill: "#aaaaaa", fontSize: 12, fontWeight: 300 }}
                  >
                    总房源
                  </tspan>
                </text>
                <Tooltip content={<ChartTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* 图例 — 强化对比 */}
          <div className="flex flex-col gap-5">
            {data.map((item, i) => (
              <div key={item.name} className="flex items-center gap-4">
                <span
                  className="inline-block h-4 w-4 rounded-full"
                  style={{
                    background: DONUT_COLORS[i],
                    boxShadow: `0 0 8px ${DONUT_COLORS[i]}66`,
                  }}
                />
                <div>
                  <p
                    className="text-base font-medium tracking-wide"
                    style={{
                      fontFamily: '"PingFang SC", "Noto Sans SC", sans-serif',
                      fontWeight: 500,
                      color: "#ffffff",
                    }}
                  >
                    {item.name}
                  </p>
                  <p className="text-sm font-light" style={{ color: "#aaaaaa", fontSize: 14 }}>
                    {item.value.toLocaleString("zh-CN")} 条 ·{" "}
                    {((item.value / total) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}

            {/* 总计分割线 */}
            <div
              className="mt-2 border-t pt-4"
              style={{ borderColor: "rgba(255,255,255,0.08)" }}
            >
              <p className="text-sm font-light" style={{ color: "#888888", fontSize: 14 }}>
                总计{" "}
                <span className="font-mono-data font-medium" style={{ color: "#ffffff" }}>
                  {total.toLocaleString("zh-CN")}
                </span>{" "}
                条房源数据
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
