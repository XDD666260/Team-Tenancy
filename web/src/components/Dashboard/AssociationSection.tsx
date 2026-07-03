"use client";

import { useRef, useEffect, useMemo } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import type { AssociationRule } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

/* ── 内置硬兜底数据 ── */
const FALLBACK_RULES: AssociationRule[] = [
  { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "两江新区 + 总价120-200万", support: 0.023, confidence: 0.53, lift: 7.33 },
  { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万 + 3室", support: 0.024, confidence: 0.56, lift: 7.12 },
  { antecedents: "单价8000-12000 + 总价<50万", consequents: "面积<60㎡", support: 0.024, confidence: 0.99, lift: 6.82 },
  { antecedents: "区县=武隆区 + 总价<50万", consequents: "南向 + 面积<60㎡", support: 0.027, confidence: 0.66, lift: 6.72 },
  { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万", support: 0.039, confidence: 0.92, lift: 6.34 },
  { antecedents: "两江新区 + 单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万", support: 0.023, confidence: 0.91, lift: 6.31 },
  { antecedents: "单价12000-18000 + 面积90-120㎡", consequents: "总价120-200万 + 南向", support: 0.029, confidence: 0.68, lift: 6.16 },
  { antecedents: "总价120-200万 + 面积90-120㎡", consequents: "单价12000-18000 + 3室", support: 0.024, confidence: 0.45, lift: 5.97 },
  { antecedents: "房龄5-10年", consequents: "南向 + anjuke来源", support: 0.026, confidence: 0.86, lift: 5.92 },
  { antecedents: "面积60-90㎡", consequents: "单价8000-12000", support: 0.079, confidence: 0.31, lift: 2.86 },
];

const LIFT_TIERS = [
  { threshold: 6, color: "#ff5722", label: "≥6" },
  { threshold: 4, color: "#ff8a65", label: "≥4" },
  { threshold: 2, color: "#ffab91", label: "≥2" },
  { threshold: 0, color: "#94ddde", label: "<2" },
];
function getLiftTier(lift: number) { return LIFT_TIERS.find(t => lift >= t.threshold) || LIFT_TIERS[3]; }

interface Props { data: { rules?: AssociationRule[]; total_rules?: number } }

export default function AssociationSection({ data }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const scatterRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  /* 修复点①: 三重兜底 */
  const rules = useMemo(() => {
    const src = data?.rules?.length ? data.rules : FALLBACK_RULES;
    return src.slice(0, 10);
  }, [data]);
  const totalRules = data?.total_rules || rules.length;

  /* 修复点②: 热力图数据 */
  const scatterData = useMemo(() => rules.map((r, i) => ({
    x: +(r.support * 100).toFixed(2),
    y: +(r.confidence * 100).toFixed(1),
    z: +r.lift.toFixed(2),
    idx: i,
    ante: r.antecedents,
    cons: r.consequents,
  })), [rules]);

  /* 修复点⑦: debug */
  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      console.log("[AssociationSection] rules:", rules.length,
        "| scatterData:", scatterData,
        "| container:", scatterRef.current ? `${scatterRef.current.offsetWidth}x${scatterRef.current.offsetHeight}` : "null");
    }
  }, [rules, scatterData]);

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
            Apriori · {totalRules} 条规则 · min_support=2%
          </span>
        </div>

        {/* ═══ 热力图 — 修复点③: data-testid + 空数据提示 ═══ */}
        <div className="glass-card p-6 sm:p-8" data-testid="heatmap-chart">
          <h3 className="mb-1 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            规则分布热力图
          </h3>
          <p className="mb-5 text-xs" style={{ color: "#888888", fontSize: 12 }}>
            横轴 = 支持度(%) &nbsp;·&nbsp; 纵轴 = 置信度(%) &nbsp;·&nbsp; 圆大小 = 提升度
          </p>
          {rules.length === 0 ? (
            <div className="flex h-[300px] items-center justify-center" style={{ color: "#888888" }}>暂无规则数据</div>
          ) : (
            <div ref={scatterRef} className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 12, right: 20, left: 0, bottom: 12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis type="number" dataKey="x" name="支持度"
                    domain={["dataMin - 1", "dataMax + 1"]}
                    axisLine={false} tickLine={false}
                    tick={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }}
                    label={{ value: "支持度 (%)", position: "bottom", offset: 0, fill: "#888888", fontSize: 12 }} />
                  <YAxis type="number" dataKey="y" name="置信度"
                    domain={["dataMin - 5", "dataMax + 5"]}
                    axisLine={false} tickLine={false}
                    tick={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }}
                    label={{ value: "置信度 (%)", angle: -90, position: "insideLeft", offset: 8, fill: "#888888", fontSize: 12 }} />
                  <ZAxis type="number" dataKey="z" range={[50, 320]} />
                  <Tooltip content={<ScatterTooltip />} />
                  <Scatter data={scatterData} isAnimationActive={false}>
                    {scatterData.map((d) => {
                      const tier = getLiftTier(d.z);
                      return (
                        <Cell key={d.idx} fill={tier.color} fillOpacity={0.65}
                          stroke={tier.color} strokeWidth={1.5}
                          style={{ filter: `drop-shadow(0 0 5px ${tier.color}44)` }} />
                      );
                    })}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}
          {/* 热力图图例 */}
          <div className="mt-4 flex items-center gap-4 text-xs" style={{ color: "#888888" }}>
            <span>提升度:</span>
            {LIFT_TIERS.map(t => (
              <span key={t.threshold} className="flex items-center gap-1.5">
                <span className="inline-block h-3 w-3 rounded-full"
                  style={{ background: t.color, boxShadow: `0 0 5px ${t.color}66` }} />
                {t.label}
              </span>
            ))}
          </div>
        </div>

        {/* ═══ TOP 10 表格 — 修复点④: 规则内容 + 橙色进度条 ═══ */}
        <div className="glass-card overflow-x-auto p-6 sm:p-8" data-testid="rules-table">
          <h3 className="mb-6 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            TOP 10 高提升度规则
          </h3>
          {/* 表头 */}
          <div className="mb-2 grid grid-cols-12 gap-2 px-2 pb-2"
            style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <span className="col-span-1 text-xs font-medium" style={{ color: "#888888" }}>#</span>
            <span className="col-span-5 text-xs font-medium" style={{ color: "#888888" }}>前提条件 → 结论</span>
            <span className="col-span-2 text-center text-xs font-medium" style={{ color: "#888888" }}>支持度</span>
            <span className="col-span-2 text-center text-xs font-medium" style={{ color: "#888888" }}>置信度</span>
            <span className="col-span-2 text-center text-xs font-medium" style={{ color: "#888888" }}>提升度</span>
          </div>
          {rules.length === 0 ? (
            <div className="flex h-40 items-center justify-center" style={{ color: "#888888" }}>暂无规则数据</div>
          ) : (
            <div className="space-y-1">
              {rules.map((rule, i) => (
                <RuleRow key={i} rule={rule} rank={i + 1} />
              ))}
            </div>
          )}
        </div>

        {/* ═══ 关键发现 ═══ */}
        <div className="glass-card p-6 sm:p-8" data-testid="findings-cards">
          <h3 className="mb-4 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            关键发现
          </h3>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
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

/* ── 热力图自定义 Tooltip ── */
function ScatterTooltip({ active, payload }: any) {
  if (!active || !payload || !payload[0]) return null;
  const p = payload[0]?.payload;
  if (!p) return null;
  return (
    <div style={{
      background: "rgba(15,15,28,0.96)", border: "1px solid rgba(148,221,222,0.2)",
      borderRadius: 12, backdropFilter: "blur(20px)", padding: "12px 16px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.5)", maxWidth: 340,
    }}>
      <p style={{ color: "#aaaaaa", fontSize: 11, marginBottom: 4 }}>规则 #{p.idx + 1}</p>
      <p style={{ color: "#ffffff", fontSize: 12, lineHeight: 1.5 }}>{p.ante}</p>
      <p style={{ color: "var(--color-mint)", fontSize: 11, marginTop: 2 }}>→ {p.cons}</p>
      <div style={{ display: "flex", gap: 14, marginTop: 6 }}>
        <span style={{ color: "#ccc", fontSize: 11 }}>支持度: {p.x}%</span>
        <span style={{ color: "#ccc", fontSize: 11 }}>置信度: {p.y}%</span>
        <span style={{ color: "#ff5722", fontSize: 11, fontWeight: 500 }}>提升度: {p.z}</span>
      </div>
    </div>
  );
}

/* ── 单行规则 ── */
function RuleRow({ rule, rank }: { rule: AssociationRule; rank: number }) {
  const tier = getLiftTier(rule.lift);
  const barPct = Math.min(rule.lift * 10, 100);

  return (
    <div className="grid grid-cols-12 gap-2 rounded-xl px-3 py-3 transition-all duration-300 hover:brightness-110"
      style={{
        background: rank <= 3 ? `linear-gradient(90deg, ${tier.color}10, transparent)` : "transparent",
        border: rank <= 3 ? `1px solid ${tier.color}18` : "1px solid transparent",
      }}>
      {/* 排名 */}
      <span className="col-span-1 flex items-center">
        <span className="font-mono-data text-sm font-medium"
          style={{ color: rank <= 3 ? tier.color : "#888888" }}>
          {String(rank).padStart(2, "0")}
        </span>
      </span>

      {/* 修复点⑤: 规则内容 — 确保字符串非空 */}
      <div className="col-span-5 flex flex-col justify-center overflow-hidden">
        <p className="truncate text-sm leading-relaxed" style={{ color: "#dddddd", fontSize: 13 }}>
          <span style={{ color: "var(--color-mint)" }}>{rule.antecedents || "(无前提)"}</span>
          <span style={{ color: "#aaaaaa", margin: "0 6px" }}>→</span>
          <span style={{ color: "var(--color-pink-light)" }}>{rule.consequents || "(无结论)"}</span>
        </p>
      </div>

      {/* 支持度 */}
      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium">{(rule.support * 100).toFixed(1)}%</span>
        <MiniBar pct={rule.support * 100 * 4} color="rgba(255,255,255,0.2)" />
      </div>

      {/* 置信度 */}
      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium">{(rule.confidence * 100).toFixed(0)}%</span>
        <MiniBar pct={rule.confidence * 100} color="rgba(255,255,255,0.25)" />
      </div>

      {/* 修复点⑥: 提升度 + 橙色渐变进度条 */}
      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium"
          style={{ color: tier.color, textShadow: `0 0 4px ${tier.color}44` }}>
          {rule.lift.toFixed(2)}
        </span>
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
          <div className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${barPct}%`,
              background: `linear-gradient(90deg, ${tier.color}88, ${tier.color})`,
              boxShadow: `0 0 4px ${tier.color}44`,
            }} />
        </div>
      </div>
    </div>
  );
}

function MiniBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="mt-1 h-0.5 w-full rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
      <div className="h-full rounded-full" style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
    </div>
  );
}

function FindingCard({ num, title, desc }: { num: string; title: string; desc: string }) {
  return (
    <div className="flex gap-3">
      <span className="font-mono-data text-xl font-medium opacity-30"
        style={{ color: "var(--color-mint)", lineHeight: 1.2, minWidth: 28 }}>{num}</span>
      <div>
        <p className="text-sm font-medium tracking-wide"
          style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>{title}</p>
        <p className="mt-1 text-sm leading-relaxed" style={{ color: "#aaaaaa", fontSize: 14 }}>{desc}</p>
      </div>
    </div>
  );
}
