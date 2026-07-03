"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

gsap.registerPlugin(ScrollTrigger);

const DONUT_COLORS = ["rgba(148,221,222,0.85)", "rgba(247,180,167,0.75)"];

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
      className="relative mx-auto max-w-6xl px-4 pb-24 sm:px-6 lg:px-8"
    >
      <div className="glass-card p-6 sm:p-8">
        <h2
          className="mb-6 text-lg font-light tracking-wider sm:text-xl"
          style={{ color: "var(--color-text)" }}
        >
          数据来源分布
        </h2>

        <div className="flex flex-col items-center gap-6 lg:flex-row">
          {/* 环形图 */}
          <div className="h-56 w-56 sm:h-64 sm:w-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius="60%"
                  outerRadius="85%"
                  paddingAngle={3}
                  dataKey="value"
                  stroke="transparent"
                >
                  {data.map((_, i) => (
                    <Cell key={i} fill={DONUT_COLORS[i]} />
                  ))}
                </Pie>
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
                  formatter={(value) => {
                    const v = Number(value);
                    return [
                      `${v.toLocaleString("zh-CN")} 条 (${((v / total) * 100).toFixed(1)}%)`,
                      "",
                    ];
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* 图例 */}
          <div className="flex flex-col gap-4">
            {data.map((item, i) => (
              <div key={item.name} className="flex items-center gap-3">
                <span
                  className="inline-block h-3 w-3 rounded-full"
                  style={{ background: DONUT_COLORS[i] }}
                />
                <div>
                  <p
                    className="text-sm font-light"
                    style={{ color: "var(--color-text)" }}
                  >
                    {item.name}
                  </p>
                  <p
                    className="text-xs font-light"
                    style={{ color: "var(--color-text-hint)" }}
                  >
                    {item.value.toLocaleString("zh-CN")} 条 ·{" "}
                    {((item.value / total) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}

            {/* 总计 */}
            <div
              className="mt-2 border-t pt-3"
              style={{ borderColor: "rgba(255,255,255,0.06)" }}
            >
              <p
                className="text-xs font-light tracking-wider"
                style={{ color: "var(--color-text-hint)" }}
              >
                总计 {total.toLocaleString("zh-CN")} 条房源
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
