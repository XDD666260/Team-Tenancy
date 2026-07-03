"use client";

import { useRef, useEffect, useMemo } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import type { AssociationData, AssociationRule } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

const LIFT_COLORS = [
  { threshold: 6, color: "#ff5722", glow: "rgba(255,87,34,0.4)" },
  { threshold: 4, color: "#ff8a65", glow: "rgba(255,138,101,0.35)" },
  { threshold: 2, color: "#ffab91", glow: "rgba(255,171,145,0.25)" },
  { threshold: 0, color: "#94ddde", glow: "rgba(148,221,222,0.2)" },
];

function getLiftColor(lift: number) {
  const tier = LIFT_COLORS.find((t) => lift >= t.threshold) || LIFT_COLORS[LIFT_COLORS.length - 1];
  return tier;
}

interface Props {
  data: AssociationData;
}

export default function AssociationSection({ data }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);
  const rules = (data?.rules || []).slice(0, 10);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    const ctx = gsap.context(() => {
      gsap.fromTo(".assoc-section", { opacity: 0, y: 36 }, {
        opacity: 1, y: 0, duration: 0.8, ease: "power3.out",
        scrollTrigger: { trigger: sectionRef.current, start: "top 82%" },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, []);

  /* ── 热力图数据：支持度 × 置信度 — 提升度着色 ── */
  const heatmapData = useMemo(() => {
    return rules.map((r, i) => ({
      x: +(r.support * 100).toFixed(2),
      y: +(r.confidence * 100).toFixed(1),
      z: +r.lift.toFixed(2),
      idx: i,
      antecedents: r.antecedents,
      consequents: r.consequents,
    }));
  }, [rules]);

  return (
    <section ref={sectionRef} className="relative mx-auto max-w-6xl px-4 pb-28 sm:px-6 lg:px-8">
      <div className="assoc-section space-y-5">

        {/* ═══ 标题 ═══ */}
        <div className="flex items-center gap-3 pb-2">
          <span className="h-5 w-0.5 rounded-full" style={{ background: "#ff5722" }} />
          <h2 className="text-lg font-medium tracking-wider sm:text-xl"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            关联规则挖掘
          </h2>
          <span className="text-sm font-light" style={{ color: "#aaaaaa", fontSize: 14 }}>
            Apriori · {data.total_rules} 条规则 · min_support=2%
          </span>
        </div>

        {/* ═══ 热力图：支持度 × 置信度 → 提升度 ═══ */}
        <div className="glass-card p-6 sm:p-8">
          <h3 className="mb-6 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            规则分布热力图
          </h3>
          <p className="-mt-4 mb-4 text-xs font-light" style={{ color: "#888888" }}>
            横轴=支持度(%) · 纵轴=置信度(%) · 颜色深浅=提升度
          </p>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 16, right: 16, left: -4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis type="number" dataKey="x" name="支持度"
                  axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }}
                  label={{ value: "支持度 (%)", position: "bottom", offset: -4, fill: "#888888", fontSize: 11 }} />
                <YAxis type="number" dataKey="y" name="置信度"
                  axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }}
                  label={{ value: "置信度 (%)", angle: -90, position: "insideLeft", offset: 10, fill: "#888888", fontSize: 11 }} />
                <ZAxis type="number" dataKey="z" range={[60, 320]} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload[0]) return null;
                    const p = payload[0].payload;
                    return (
                      <div style={{
                        background: "rgba(15,15,28,0.96)", border: "1px solid rgba(148,221,222,0.2)",
                        borderRadius: 12, backdropFilter: "blur(20px)", padding: "12px 16px",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.5)", maxWidth: 320,
                      }}>
                        <p style={{ color: "#aaaaaa", fontSize: 11, marginBottom: 4 }}>规则 #{p.idx + 1}</p>
                        <p style={{ color: "#94ddde", fontSize: 12, lineHeight: 1.5 }}>
                          {p.antecedents}
                        </p>
                        <p style={{ color: "#f7b4a7", fontSize: 11, marginTop: 2 }}>→ {p.consequents}</p>
                        <div style={{ display: "flex", gap: 12, marginTop: 6 }}>
                          <span style={{ color: "#ccc", fontSize: 11 }}>支持: {p.x}%</span>
                          <span style={{ color: "#ccc", fontSize: 11 }}>置信: {p.y}%</span>
                          <span style={{ color: "#ff5722", fontSize: 11, fontWeight: 500 }}>提升: {p.z}</span>
                        </div>
                      </div>
                    );
                  }}
                />
                <Scatter data={heatmapData}>
                  {heatmapData.map((d) => {
                    const tier = getLiftColor(d.z);
                    return (
                      <Cell key={d.idx} fill={tier.color} fillOpacity={0.7}
                        stroke={tier.color} strokeWidth={1}
                        style={{ filter: `drop-shadow(0 0 4px ${tier.glow})` }} />
                    );
                  })}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          {/* 热力图图例 */}
          <div className="mt-3 flex items-center gap-3 text-xs font-light" style={{ color: "#888888" }}>
            <span>提升度:</span>
            {LIFT_COLORS.map((t) => (
              <span key={t.threshold} className="flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ background: t.color, boxShadow: `0 0 4px ${t.glow}` }} />
                ≥{t.threshold}
              </span>
            ))}
          </div>
        </div>

        {/* ═══ TOP 10 表格 ═══ */}
        <div className="glass-card overflow-x-auto p-6 sm:p-8">
          <h3 className="mb-6 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            TOP 10 高提升度规则
          </h3>
          {/* 表头 */}
          <div className="mb-3 grid grid-cols-12 gap-2 px-2">
            <span className="col-span-1 text-xs font-medium" style={{ color: "#888888" }}>#</span>
            <span className="col-span-5 text-xs font-medium" style={{ color: "#888888" }}>前提条件 → 结论</span>
            <span className="col-span-2 text-center text-xs font-medium" style={{ color: "#888888" }}>支持度</span>
            <span className="col-span-2 text-center text-xs font-medium" style={{ color: "#888888" }}>置信度</span>
            <span className="col-span-2 text-center text-xs font-medium" style={{ color: "#888888" }}>提升度</span>
          </div>
          <div className="space-y-1.5">
            {rules.map((rule, i) => (
              <RuleRow key={i} rule={rule} rank={i + 1} />
            ))}
          </div>
        </div>

        {/* ═══ 关键发现 ═══ */}
        <div className="glass-card p-6 sm:p-8">
          <h3 className="mb-4 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            关键发现
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FindingCard num="01" title="两江新区 = 中高价位核心区"
              desc="单价12000-18000 + 面积90-120㎡ → 两江新区，Lift=7.33，远超随机概率。" />
            <FindingCard num="02" title="低价 = 小面积（几乎必然）"
              desc="总价<50万 + 单价8000-12000 → 面积<60㎡，置信度高达 99%。" />
            <FindingCard num="03" title="改善型购房甜蜜点"
              desc="90-120㎡ + 12000-18000元/㎡ → 总价120-200万 + 3室。" />
            <FindingCard num="04" title="武隆区度假养老特征"
              desc="武隆区 50万以下 → 南向小户型，Lift=6.72，反映远郊区县独特模式。" />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── 单条规则行（含提升度进度条） ── */
function RuleRow({ rule, rank }: { rule: AssociationRule; rank: number }) {
  const tier = getLiftColor(rule.lift);
  const pct = Math.min(rule.lift * 10, 100);

  return (
    <div
      className="grid grid-cols-12 gap-2 rounded-xl px-3 py-3 transition-all duration-300 hover:brightness-110"
      style={{
        background: rank <= 3 ? `linear-gradient(90deg, ${tier.color}11, transparent)` : "transparent",
        border: rank <= 3 ? `1px solid ${tier.color}22` : "1px solid transparent",
      }}
    >
      <span className="col-span-1 flex items-center">
        <span className="font-mono-data text-sm font-medium"
          style={{ color: rank <= 3 ? tier.color : "#888888" }}>
          {String(rank).padStart(2, "0")}
        </span>
      </span>

      <div className="col-span-5 flex flex-col justify-center">
        <p className="text-sm leading-relaxed" style={{ color: "#dddddd", fontSize: 13 }}>
          <span style={{ color: "var(--color-mint)" }}>{rule.antecedents}</span>
          {" → "}
          <span style={{ color: "var(--color-pink-light)" }}>{rule.consequents}</span>
        </p>
      </div>

      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium">{(rule.support * 100).toFixed(1)}%</span>
        <div className="mt-1 h-0.5 w-full rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
          <div className="h-full rounded-full" style={{ width: `${rule.support * 100 * 4}%`, background: "rgba(255,255,255,0.2)" }} />
        </div>
      </div>

      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium">{(rule.confidence * 100).toFixed(0)}%</span>
        <div className="mt-1 h-0.5 w-full rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
          <div className="h-full rounded-full" style={{ width: `${rule.confidence * 100}%`, background: "rgba(255,255,255,0.25)" }} />
        </div>
      </div>

      {/* 提升度 + 橙色渐变进度条 */}
      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium"
          style={{ color: tier.color, textShadow: `0 0 4px ${tier.glow}` }}>
          {rule.lift.toFixed(2)}
        </span>
        <div className="mt-1 h-1 w-full rounded-full" style={{ background: "rgba(255,255,255,0.05)", overflow: "hidden" }}>
          <div className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              background: `linear-gradient(90deg, #ff8a65, ${tier.color})`,
              boxShadow: `0 0 4px ${tier.glow}`,
            }} />
        </div>
      </div>
    </div>
  );
}

function FindingCard({ num, title, desc }: { num: string; title: string; desc: string }) {
  return (
    <div className="flex gap-3">
      <span className="font-mono-data text-xl font-medium opacity-30"
        style={{ color: "var(--color-mint)", lineHeight: 1.2 }}>{num}</span>
      <div>
        <p className="text-sm font-medium tracking-wide"
          style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>{title}</p>
        <p className="mt-1 text-sm leading-relaxed" style={{ color: "#aaaaaa", fontSize: 14 }}>{desc}</p>
      </div>
    </div>
  );
}
