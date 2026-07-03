"use client";

import { useRef, useEffect, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

interface KpiItem {
  label: string;
  value: string;
  suffix: string;
  desc: string;
  accent: string; // CSS var or hex
  glowClass: string;
}

function formatNumber(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + "万";
  return n.toLocaleString("zh-CN");
}

function formatPrice(n: number): string {
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

interface Props {
  totalHouses: number;
  avgUnitPrice: number;
  avgTotalPrice: number;
  maxUnitPrice: number;
  minUnitPrice: number;
  districtCount: number;
}

export default function KpiCards({
  totalHouses,
  avgUnitPrice,
  avgTotalPrice,
  maxUnitPrice,
  minUnitPrice,
  districtCount,
}: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".kpi-card",
        { y: 48, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          stagger: 0.06,
          duration: 0.75,
          ease: "power3.out",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top 88%",
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  const kpis: KpiItem[] = [
    {
      label: "在售房源",
      value: formatNumber(totalHouses),
      suffix: "条",
      desc: "覆盖重庆全域",
      accent: "var(--color-mint)",
      glowClass: "num-glow-mint",
    },
    {
      label: "房源均价",
      value: formatPrice(avgUnitPrice),
      suffix: "元/㎡",
      desc: "单位面积均价",
      accent: "#ffffff",
      glowClass: "num-glow-blue",
    },
    {
      label: "套均总价",
      value: formatPrice(avgTotalPrice),
      suffix: "万元",
      desc: "平均总价水平",
      accent: "var(--color-pink-light)",
      glowClass: "num-glow-pink",
    },
    {
      label: "最高单价",
      value: formatPrice(maxUnitPrice),
      suffix: "元/㎡",
      desc: "最低 " + formatPrice(minUnitPrice) + " 元/㎡",
      accent: "var(--color-dust-purple-light)",
      glowClass: "num-glow-pink",
    },
    {
      label: "覆盖区县",
      value: String(districtCount),
      suffix: "个",
      desc: "数据广度指标",
      accent: "var(--color-mint)",
      glowClass: "num-glow-mint",
    },
  ];

  return (
    <section
      ref={sectionRef}
      className="relative -mt-12 px-4 pb-20 sm:px-6 lg:px-8"
    >
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((item) => (
          <KpiCard key={item.label} {...item} />
        ))}
      </div>
    </section>
  );
}

/* ── 单张卡片 ── */
function KpiCard({ label, value, suffix, desc, accent, glowClass }: KpiItem) {
  const glowRef = useRef<HTMLDivElement>(null);

  const onEnter = () => {
    gsap.to(glowRef.current, { opacity: 1, duration: 0.3 });
  };
  const onLeave = () => {
    gsap.to(glowRef.current, { opacity: 0, duration: 0.35 });
  };

  return (
    <div
      className="kpi-card glass-card group relative cursor-default"
      style={{ padding: 24, transition: "all 0.35s ease" }}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      {/* [UI-OPTIMIZE] hover 外发光 */}
      <div ref={glowRef}
        className="pointer-events-none absolute inset-0 rounded-[20px] opacity-0"
        style={{
          boxShadow: `0 0 36px ${accent}22, inset 0 0 28px ${accent}08`,
          transition: "opacity 0.35s ease",
        }} />

      <div className="relative z-10 flex flex-col">
        {/* 标签 — 14px */}
        <span className="body-text mb-3" style={{ fontSize: 14, color: "var(--color-text-hint)" }}>
          {label}
        </span>

        {/* 数值 — mono + 发光 */}
        <div className="flex items-baseline gap-1">
          <span className={`font-mono-data text-2xl sm:text-3xl tracking-tight ${glowClass}`}
            style={{ color: accent, fontWeight: 600 }}>
            {value}
          </span>
          <span className="text-sm font-light" style={{ color: "rgba(255,255,255,0.4)" }}>
            {suffix}
          </span>
        </div>

        {/* 描述 */}
        <span className="body-text mt-2" style={{ fontSize: 14, color: "#888888" }}>
          {desc}
        </span>
      </div>
    </div>
  );
}
