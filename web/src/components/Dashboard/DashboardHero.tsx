"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";

export default function DashboardHero({ updateTime }: { updateTime: string }) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const badgeRef = useRef<HTMLDivElement>(null);
  const lineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        titleRef.current,
        { y: 60, opacity: 0, filter: "blur(4px)" },
        { y: 0, opacity: 1, filter: "blur(0px)", duration: 1, ease: "power3.out" }
      );
      gsap.fromTo(
        subtitleRef.current,
        { y: 24, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.7, ease: "power3.out", delay: 0.2 }
      );
      gsap.fromTo(
        badgeRef.current,
        { scale: 0.8, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.5)", delay: 0.4 }
      );
      gsap.fromTo(
        lineRef.current,
        { scaleX: 0 },
        { scaleX: 1, duration: 1.2, ease: "power3.inOut", delay: 0.6 }
      );
    });
    return () => ctx.revert();
  }, []);

  return (
    <section
      className="relative flex h-[32vh] min-h-[280px] items-center justify-center overflow-hidden"
      style={{
        background:
          "linear-gradient(180deg, #0d0d1a 0%, #1a1a2e 30%, #1f2b4b 70%, #1a1a2e 100%)",
      }}
    >
      {/* 几何装饰 */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(45deg, transparent, transparent 60px, rgba(148,221,222,0.5) 60px, rgba(148,221,222,0.5) 61px), repeating-linear-gradient(-45deg, transparent, transparent 60px, rgba(247,180,167,0.4) 60px, rgba(247,180,167,0.4) 61px)",
        }}
      />
      {/* 顶部光晕 */}
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-48 w-[600px] -translate-x-1/2"
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(43,75,130,0.2) 0%, transparent 70%)",
        }}
      />

      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        {/* 状态徽标 */}
        <div
          ref={badgeRef}
          className="mb-6 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs font-light tracking-[0.15em]"
          style={{
            borderColor: "rgba(148,221,222,0.2)",
            color: "var(--color-mint)",
            background: "rgba(148,221,222,0.06)",
          }}
        >
          <span
            className="inline-block h-1.5 w-1.5 rounded-full animate-pulse"
            style={{ background: "var(--color-mint)", boxShadow: "var(--glow-mint)" }}
          />
          实时数据
        </div>

        {/* 标题 — PingFang SC Medium */}
        <h1
          ref={titleRef}
          className="text-3xl font-medium tracking-wider sm:text-4xl md:text-5xl"
          style={{
            fontFamily: '"PingFang SC", "Noto Sans SC", sans-serif',
            fontWeight: 500,
            background:
              "linear-gradient(180deg, #ffffff 0%, rgba(226,226,226,0.9) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          数据仪表盘
        </h1>

        {/* 副标题 — 14px #aaa */}
        <p
          ref={subtitleRef}
          className="mt-4 text-sm font-light tracking-wide"
          style={{ color: "#aaaaaa" }}
        >
          基于 50,507 条真实二手房数据 · 多维度可视化分析
          {updateTime && (
            <span className="ml-3" style={{ color: "rgba(255,255,255,0.25)" }}>
              更新于 {updateTime}
            </span>
          )}
        </p>

        {/* 分割线 */}
        <div
          ref={lineRef}
          className="mx-auto mt-6 h-px w-16"
          style={{
            background:
              "linear-gradient(90deg, transparent, rgba(148,221,222,0.5), transparent)",
          }}
        />
      </div>
    </section>
  );
}
