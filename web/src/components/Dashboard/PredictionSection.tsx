"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import type { PredictionData, ModelResult, FeatureImportanceItem } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

/* ── 模型卡片配色 ── */
const MODEL_COLORS: Record<string, string> = {
  RandomForest_total: "#4a90e2",
  RandomForest_unit: "#9b59b6",
  GradientBoosting_total: "#00bcd4",
  GradientBoosting_unit: "#ff5722",
};

const MODEL_LABELS: Record<string, string> = {
  RandomForest_total: "Random Forest · 总价",
  RandomForest_unit: "Random Forest · 单价",
  GradientBoosting_total: "Gradient Boosting · 总价",
  GradientBoosting_unit: "Gradient Boosting · 单价",
};

const FEATURE_COLORS = ["#4a90e2", "#ff5722"]; // RF blue vs GB orange

interface Props {
  data: PredictionData;
}

export default function PredictionSection({ data }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);

  const models = data?.models || {};
  const fi = data?.feature_importance || {};

  // RF & GB 总价版特征重要性对比
  const rfImportance = fi["RandomForest_total"] || [];
  const gbImportance = fi["GradientBoosting_total"] || [];
  const features = rfImportance.slice(0, 8).map((item) => ({
    feature: item.feature_cn,
    RF: +(item.importance * 100).toFixed(2),
    GB: +((gbImportance.find((g) => g.feature === item.feature)?.importance || 0) * 100).toFixed(2),
  }));

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".pred-section",
        { opacity: 0, y: 36 },
        {
          opacity: 1, y: 0, duration: 0.8, ease: "power3.out",
          scrollTrigger: { trigger: sectionRef.current, start: "top 82%" },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} className="relative mx-auto max-w-6xl px-4 pb-[30px] sm:px-6 lg:px-8">
      <div className="pred-section space-y-5">

        {/* ═══ 区块标题 ═══ */}
        <div className="flex items-center gap-3 pb-2">
          <span
            className="h-5 w-0.5 rounded-full"
            style={{ background: "var(--color-mint)" }}
          />
          <h2
            className="text-lg font-medium tracking-wider sm:text-xl"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}
          >
            房价预测模型
          </h2>
          <span className="text-sm font-light" style={{ color: "#aaaaaa", fontSize: 14 }}>
            机器学习 · 集成学习
          </span>
        </div>

        {/* ═══ 模型指标卡片 2×2 ═══ */}
        <div className="grid grid-cols-2 gap-5">
          {Object.entries(models).map(([key, m]) => (
            <ModelCard key={key} modelKey={key} model={m} />
          ))}
        </div>

        {/* ═══ 特征重要性对比图 ═══ */}
        <div
          className="p-6 sm:p-8"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 16,
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
          }}
        >
          <h3
            className="mb-2 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}
          >
            特征重要性对比
          </h3>
          <p className="mb-6 text-sm" style={{ color: "#aaaaaa", fontSize: 14 }}>
            RF vs GB · 总价预测 · 面积 + 地段 = 房价的 84.7%
          </p>

          <div className="h-[340px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={features}
                layout="vertical"
                margin={{ top: 0, right: 12, left: 8, bottom: 0 }}
                barCategoryGap="30%"
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis
                  type="number"
                  axisLine={false} tickLine={false}
                  tick={{ fill: "#aaaaaa", fontSize: 11, fontWeight: 300 }}
                  tickFormatter={(v: number) => v + "%"}
                />
                <YAxis
                  type="category" dataKey="feature"
                  axisLine={false} tickLine={false} width={110}
                  tick={{ fill: "#cccccc", fontSize: 13, fontWeight: 300 }}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgba(18,18,30,0.96)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12, backdropFilter: "blur(16px)",
                    color: "#fff", fontSize: 13, fontWeight: 300,
                  }}
                  formatter={(value) => [`${Number(value).toFixed(2)}%`]}
                />
                <Bar dataKey="RF" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {features.map((_, i) => (
                    <Cell key={`rf-${i}`} fill={FEATURE_COLORS[0]} fillOpacity={0.8} />
                  ))}
                </Bar>
                <Bar dataKey="GB" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {features.map((_, i) => (
                    <Cell key={`gb-${i}`} fill={FEATURE_COLORS[1]} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* 图例 */}
          <div className="mt-4 flex items-center gap-6">
            {[{ color: FEATURE_COLORS[0], label: "Random Forest" }, { color: FEATURE_COLORS[1], label: "Gradient Boosting" }].map((leg) => (
              <div key={leg.label} className="flex items-center gap-2">
                <span className="inline-block h-3 w-3 rounded-sm" style={{ background: leg.color }} />
                <span className="text-xs font-light" style={{ color: "#aaaaaa" }}>{leg.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ═══ 关键洞察 ═══ */}
        <div
          className="p-6 sm:p-8"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 16,
            backdropFilter: "blur(12px)",
            WebkitBackdropFilter: "blur(12px)",
          }}
        >
          <h3
            className="mb-4 text-base font-medium tracking-wider"
            style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}
          >
            核心发现
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <InsightCard
              color="var(--color-mint)"
              title="面积主导"
              desc="面积重要性 33.7%，是房价第一驱动力。面积大 10㎡比精装修更能提升总价。"
            />
            <InsightCard
              color="var(--color-pink-light)"
              title="地段溢价"
              desc="小区 + 区县编码合占 51%，说明地段档次直接决定房价层级。"
            />
            <InsightCard
              color="#4a90e2"
              title="模型能力"
              desc={`RF 测试 R² = ${(models["RandomForest_total"]?.test_r2 * 100).toFixed(0)}%，总价比单价更易预测（R² 差约 13%）。`}
            />
          </div>
        </div>

      </div>
    </section>
  );
}

/* ── 单张模型指标卡 ── */
function ModelCard({ modelKey, model }: { modelKey: string; model: ModelResult }) {
  const accent = MODEL_COLORS[modelKey] || "#4a90e2";
  const label = MODEL_LABELS[modelKey] || modelKey;

  return (
    <div
      className="group p-5 transition-all duration-300"
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16,
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      {/* 模型名 */}
      <div className="mb-4 flex items-center gap-2.5">
        <span
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ background: accent, boxShadow: `0 0 6px ${accent}66` }}
        />
        <span className="text-sm font-medium tracking-wide" style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
          {label}
        </span>
      </div>

      {/* 关键指标 */}
      <div className="grid grid-cols-3 gap-3">
        <MetricItem label="测试 R²" value={(model.test_r2 * 100).toFixed(1) + "%"} accent={accent} />
        <MetricItem label="测试 MAE" value={model.test_mae.toFixed(0) + model.unit} accent={accent} />
        <MetricItem label="CV R²" value={(model.cv_r2_mean * 100).toFixed(1) + "%"} accent={accent} />
      </div>
    </div>
  );
}

function MetricItem({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="text-center">
      <p className="text-xs font-light" style={{ color: "#888888", fontSize: 11 }}>{label}</p>
      <p
        className="mt-1 font-mono-data text-lg font-medium"
        style={{ color: accent, textShadow: `0 0 6px ${accent}33` }}
      >
        {value}
      </p>
    </div>
  );
}

function InsightCard({ color, title, desc }: { color: string; title: string; desc: string }) {
  return (
    <div className="flex gap-3">
      <span
        className="mt-0.5 inline-block h-8 w-0.5 flex-shrink-0 rounded-full"
        style={{ background: color }}
      />
      <div>
        <p className="text-sm font-medium tracking-wide" style={{ fontFamily: '"PingFang SC","Noto Sans SC",sans-serif', fontWeight: 500 }}>
          {title}
        </p>
        <p className="mt-1 text-sm leading-relaxed" style={{ color: "#aaaaaa", fontSize: 14 }}>
          {desc}
        </p>
      </div>
    </div>
  );
}
