"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";

export default function DashboardHero({ updateTime }: { updateTime: string }) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const badgeRef = useRef<HTMLDivElement>(null);

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
        { y: 0, opacity: 1, duration: 0.7, ease: "power3.out", delay: 0.25 }
      );
      gsap.fromTo(
        badgeRef.current,
        { scale: 0.8, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.5)", delay: 0.5 }
      );
    });
    return () => ctx.revert();
  }, []);

  return (
    <section
      className="relative flex h-[30vh] min-h-[260px] items-center justify-center overflow-hidden"
      style={{
        background:
          "linear-gradient(180deg, #1a1a2e 0%, #2b4b82 50%, #1a1a2e 100%)",
      }}
    >
      {/* 几何装饰线 */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(45deg, transparent, transparent 40px, rgba(148,221,222,0.3) 40px, rgba(148,221,222,0.3) 41px), repeating-linear-gradient(-45deg, transparent, transparent 40px, rgba(247,180,167,0.3) 40px, rgba(247,180,167,0.3) 41px)",
        }}
      />

      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        <div
          ref={badgeRef}
          className="mb-5 inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-xs tracking-[0.15em]"
          style={{
            borderColor: "rgba(148,221,222,0.25)",
            color: "var(--color-mint)",
            background: "rgba(148,221,222,0.05)",
          }}
        >
          <span
            className="inline-block h-1.5 w-1.5 rounded-full"
            style={{ background: "var(--color-mint)" }}
          />
          实时数据
        </div>

        <h1
          ref={titleRef}
          className="text-3xl font-light tracking-wider sm:text-4xl md:text-5xl"
          style={{
            background:
              "linear-gradient(180deg, #ffffff 0%, rgba(148,221,222,0.85) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          数据仪表盘
        </h1>

        <p
          ref={subtitleRef}
          className="mt-3 text-sm font-light tracking-wide sm:text-base"
          style={{ color: "var(--color-text-secondary)" }}
        >
          基于 50,507 条真实二手房数据 · 多维度可视化分析
          {updateTime && (
            <span
              className="ml-3 inline-block"
              style={{ color: "var(--color-text-hint)" }}
            >
              更新于 {updateTime}
            </span>
          )}
        </p>
      </div>
    </section>
  );
}
