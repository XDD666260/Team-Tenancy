"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

interface KpiItem {
  label: string;
  value: string;
  suffix: string;
  desc: string;
  accent: string; // CSS color
}

function formatNumber(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + "万";
  if (n >= 1000) return n.toLocaleString("zh-CN");
  return String(n);
}

function formatPrice(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + "万";
  return n.toLocaleString("zh-CN");
}

const KPI_CARD_STYLE: React.CSSProperties = {
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 16,
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
};

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
      // 卡片交错淡入
      gsap.fromTo(
        ".kpi-card",
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          stagger: 0.08,
          duration: 0.7,
          ease: "power3.out",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top 85%",
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
    },
    {
      label: "房源均价",
      value: formatNumber(avgUnitPrice),
      suffix: "元/㎡",
      desc: "单位面积均价",
      accent: "var(--color-primary)",
    },
    {
      label: "套均总价",
      value: formatPrice(avgTotalPrice),
      suffix: "万元",
      desc: "平均总价水平",
      accent: "var(--color-pink-light)",
    },
    {
      label: "价格区间",
      value: formatNumber(minUnitPrice),
      suffix: "—" + formatNumber(maxUnitPrice),
      desc: "最低 — 最高单价",
      accent: "var(--color-dust-purple-mid)",
    },
    {
      label: "覆盖区县",
      value: String(districtCount),
      suffix: "个",
      desc: "数据广度指标",
      accent: "var(--color-mint)",
    },
  ];

  return (
    <section ref={sectionRef} className="relative -mt-10 px-4 pb-16 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((kpi) => (
          <KpiCard key={kpi.label} {...kpi} />
        ))}
      </div>
    </section>
  );
}

function KpiCard({ label, value, suffix, desc, accent }: KpiItem) {
  const valueRef = useRef<HTMLSpanElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);

  // Hover glow effect
  const onEnter = () => {
    gsap.to(glowRef.current, {
      opacity: 1,
      duration: 0.3,
    });
  };
  const onLeave = () => {
    gsap.to(glowRef.current, {
      opacity: 0,
      duration: 0.3,
    });
  };

  return (
    <div
      className="kpi-card group relative cursor-default p-5 transition-transform duration-300"
      style={KPI_CARD_STYLE}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      {/* Hover glow */}
      <div
        ref={glowRef}
        className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 transition-opacity"
        style={{
          boxShadow: `0 0 28px ${accent}22, inset 0 0 28px ${accent}08`,
        }}
      />

      <div className="relative z-10">
        <p
          className="mb-2 text-xs font-light tracking-wider uppercase"
          style={{ color: "var(--color-text-hint)" }}
        >
          {label}
        </p>
        <div className="flex items-baseline gap-0.5">
          <span
            ref={valueRef}
            className="text-2xl font-light tracking-tight sm:text-3xl"
            style={{ color: accent }}
          >
            {value}
          </span>
          <span
            className="text-sm font-light"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {suffix}
          </span>
        </div>
        <p
          className="mt-1.5 text-xs font-light"
          style={{ color: "var(--color-text-hint)" }}
        >
          {desc}
        </p>
      </div>
    </div>
  );
}
