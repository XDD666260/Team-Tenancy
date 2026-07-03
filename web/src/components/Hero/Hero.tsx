"use client";

import { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";

gsap.registerPlugin(ScrollTrigger);

export default function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const btnRef = useRef<HTMLAnchorElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const ctx = gsap.context(() => {
      // ── 入场动画 ──
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.fromTo(
        titleRef.current,
        { y: 80, opacity: 0, filter: "blur(8px)" },
        { y: 0, opacity: 1, filter: "blur(0px)", duration: 1.2 }
      )
        .fromTo(
          subtitleRef.current,
          { y: 40, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.8 },
          "-=0.7"
        )
        .fromTo(
          btnRef.current,
          { y: 30, opacity: 0, scale: 0.85 },
          {
            y: 0,
            opacity: 1,
            scale: 1,
            duration: 0.7,
            ease: "back.out(2)",
          },
          "-=0.5"
        );

      // ── 背景光晕呼吸 ──
      gsap.to(glowRef.current, {
        scale: 1.15,
        opacity: 0.7,
        duration: 4,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });

      // ── 滚动：标题向上淡出 ──
      gsap.to([titleRef.current, subtitleRef.current], {
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: "bottom top",
          scrub: 0.6,
        },
        y: -120,
        opacity: 0,
      });

      // ── 滚动：按钮轻微弹跳 ──
      gsap.to(btnRef.current, {
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: "center+=100 top",
          scrub: 0.4,
        },
        y: 24,
        scale: 1.06,
      });
    }, sectionRef);

    return () => {
      ctx.revert();
    };
  }, []);

  return (
    <section
      ref={sectionRef}
      className="relative flex h-screen flex-col items-center justify-center overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, #1a1a2e 0%, #2b4b82 35%, #392752 70%, #6e426a 100%)",
      }}
    >
      {/* 背景光晕 */}
      <div
        ref={glowRef}
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(43,75,130,0.5) 0%, transparent 70%), radial-gradient(ellipse 40% 40% at 30% 60%, rgba(148,221,222,0.15) 0%, transparent 70%), radial-gradient(ellipse 50% 40% at 70% 30%, rgba(247,180,167,0.12) 0%, transparent 70%)",
        }}
      />

      {/* 网格纹理 */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
        }}
      />

      {/* ── 内容区 ── */}
      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        {/* 标签 */}
        <span
          className="mb-6 inline-block rounded-full border px-4 py-1.5 text-xs tracking-[0.2em] uppercase"
          style={{
            borderColor: "rgba(148,221,222,0.3)",
            color: "var(--color-mint)",
            background: "rgba(148,221,222,0.06)",
          }}
        >
          重庆 · 二手房数据分析平台
        </span>

        {/* 主标题 */}
        <h1
          ref={titleRef}
          className="text-5xl font-light tracking-wider sm:text-6xl md:text-7xl lg:text-8xl"
          style={{
            background:
              "linear-gradient(180deg, #ffffff 0%, rgba(247,180,167,0.9) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          重庆房价洞察
        </h1>

        {/* 副标题 */}
        <p
          ref={subtitleRef}
          className="mt-5 text-lg font-light tracking-wide sm:text-xl md:text-2xl"
          style={{ color: "var(--color-text-secondary)" }}
        >
          基于 50,507 条真实数据 · 机器学习驱动分析 · 数据驱动决策
        </p>

        {/* CTA 按钮 */}
        <Link
          ref={btnRef}
          href="/analysis"
          className="group relative mt-10 inline-flex items-center gap-2 rounded-full px-8 py-3.5 text-base font-light tracking-wide transition-all duration-300"
          style={{
            background: "rgba(255,255,255,0.08)",
            border: "1px solid rgba(255,255,255,0.2)",
            backdropFilter: "blur(10px)",
            color: "var(--color-text)",
          }}
          onMouseEnter={(e) => {
            gsap.to(e.currentTarget, {
              scale: 1.04,
              background: "rgba(43,75,130,0.3)",
              borderColor: "rgba(148,221,222,0.5)",
              boxShadow: "0 0 30px rgba(148,221,222,0.15)",
              duration: 0.3,
            });
          }}
          onMouseLeave={(e) => {
            gsap.to(e.currentTarget, {
              scale: 1,
              background: "rgba(255,255,255,0.08)",
              borderColor: "rgba(255,255,255,0.2)",
              boxShadow: "0 0 0px rgba(148,221,222,0)",
              duration: 0.3,
            });
          }}
        >
          <span>查看详情</span>
          <svg
            className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"
            />
          </svg>
        </Link>
      </div>

      {/* ── 底部滚动指示器 ── */}
      <div className="absolute bottom-10 z-10 flex flex-col items-center gap-2 opacity-40">
        <span className="text-xs tracking-widest" style={{ color: "var(--color-text-hint)" }}>
          向下滚动
        </span>
        <div className="h-8 w-[1px] animate-pulse" style={{ background: "rgba(255,255,255,0.3)" }} />
      </div>
    </section>
  );
}
