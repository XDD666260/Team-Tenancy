"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { AssociationData, AssociationRule } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

const LIFT_COLORS = [
  { threshold: 6, color: "#ff5722", glow: "rgba(255,87,34,0.3)" },
  { threshold: 4, color: "#ff8a65", glow: "rgba(255,138,101,0.3)" },
  { threshold: 2, color: "#ffab91", glow: "rgba(255,171,145,0.25)" },
  { threshold: 0, color: "#94ddde", glow: "rgba(148,221,222,0.2)" },
];

function getLiftStyle(lift: number) {
  const tier = LIFT_COLORS.find((t) => lift >= t.threshold) || LIFT_COLORS[LIFT_COLORS.length - 1];
  return tier;
}

interface Props {
  data: AssociationData;
}

export default function AssociationSection({ data }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);

  const rules = data.rules.slice(0, 10);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".assoc-section",
        { opacity: 0, y: 36 },
        { opacity: 1, y: 0, duration: 0.8, ease: "power3.out",
          scrollTrigger: { trigger: sectionRef.current, start: "top 82%" } }
      );
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
            Apriori · {data.total_rules} 条规则 · min_support=2%
          </span>
        </div>

        {/* ═══ TOP 10 规则表格 ═══ */}
        <div
          className="overflow-x-auto p-6 sm:p-8"
          style={{
            background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 16, backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
          }}
        >
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
        <div
          className="p-6 sm:p-8"
          style={{
            background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 16, backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
          }}
        >
          <h3 className="mb-4 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
            关键发现
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FindingCard
              num="01"
              title="两江新区 = 中高价位核心区"
              desc="单价12000-18000 + 面积90-120㎡ → 两江新区，Lift=7.33，远超随机概率。两江新区已成重庆中高端二手房标杆。"
            />
            <FindingCard
              num="02"
              title="低价 = 小面积（几乎必然）"
              desc="总价<50万 + 单价8000-12000 → 面积<60㎡，置信度高达 99%。重庆几乎没有50万以下的大面积房源。"
            />
            <FindingCard
              num="03"
              title="改善型购房甜蜜点"
              desc="90-120㎡ + 12000-18000元/㎡ → 总价120-200万 + 3室。这是重庆改善型购房者的标准配置。"
            />
            <FindingCard
              num="04"
              title="武隆区度假养老特征"
              desc="武隆区 50万以下 → 南向小户型，Lift=6.72。反映远郊区县度假/养老型房产独特模式。"
            />
          </div>
        </div>

      </div>
    </section>
  );
}

/* ── 单条规则行 ── */
function RuleRow({ rule, rank }: { rule: AssociationRule; rank: number }) {
  const liftStyle = getLiftStyle(rule.lift);

  return (
    <div
      className="grid grid-cols-12 gap-2 rounded-xl px-3 py-3 transition-all duration-300 hover:brightness-110"
      style={{
        background: rank <= 3
          ? `linear-gradient(90deg, ${liftStyle.color}11, transparent)`
          : "transparent",
        border: rank <= 3 ? `1px solid ${liftStyle.color}22` : "1px solid transparent",
      }}
    >
      {/* 排名 */}
      <span className="col-span-1 flex items-center">
        <span
          className="font-mono-data text-sm font-medium"
          style={{ color: rank <= 3 ? liftStyle.color : "#888888" }}
        >
          {String(rank).padStart(2, "0")}
        </span>
      </span>

      {/* 规则文本 */}
      <div className="col-span-5 flex flex-col justify-center">
        <p className="text-sm leading-relaxed" style={{ color: "#dddddd", fontSize: 13 }}>
          <span style={{ color: "var(--color-mint)" }}>{rule.antecedents}</span>
          {" → "}
          <span style={{ color: "var(--color-pink-light)" }}>{rule.consequents}</span>
        </p>
      </div>

      {/* 支持度 */}
      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium">{(rule.support * 100).toFixed(1)}%</span>
        <BarMini pct={rule.support * 100 * 5} bg="rgba(255,255,255,0.15)" />
      </div>

      {/* 置信度 */}
      <div className="col-span-2 flex flex-col items-center justify-center">
        <span className="font-mono-data text-sm font-medium">{(rule.confidence * 100).toFixed(0)}%</span>
        <BarMini pct={rule.confidence * 100} bg="rgba(255,255,255,0.2)" />
      </div>

      {/* 提升度 — 高亮 */}
      <div className="col-span-2 flex flex-col items-center justify-center">
        <span
          className="font-mono-data text-sm font-medium"
          style={{ color: liftStyle.color, textShadow: `0 0 4px ${liftStyle.glow}` }}
        >
          {rule.lift.toFixed(2)}
        </span>
        <BarMini pct={Math.min(rule.lift * 10, 100)} bg={liftStyle.color} />
      </div>
    </div>
  );
}

function BarMini({ pct, bg }: { pct: number; bg: string }) {
  return (
    <div className="mt-1 h-0.5 w-full rounded-full" style={{ background: "rgba(255,255,255,0.05)" }}>
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.min(pct, 100)}%`, background: bg }}
      />
    </div>
  );
}

function FindingCard({ num, title, desc }: { num: string; title: string; desc: string }) {
  return (
    <div className="flex gap-3">
      <span
        className="font-mono-data text-xl font-medium opacity-30"
        style={{ color: "var(--color-mint)", lineHeight: 1.2 }}
      >
        {num}
      </span>
      <div>
        <p className="text-sm font-medium tracking-wide"
          style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
          {title}
        </p>
        <p className="mt-1 text-sm leading-relaxed" style={{ color: "#aaaaaa", fontSize: 14 }}>
          {desc}
        </p>
      </div>
    </div>
  );
}
