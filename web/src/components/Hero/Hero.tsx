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
  const badgeRef = useRef<HTMLSpanElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const ctx = gsap.context(() => {
      // [UI-OPTIMIZE] 入场：标题模糊→清晰，徽标回弹
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.fromTo(badgeRef.current,
        { y: 20, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.6, ease: "back.out(1.7)" }
      )
        .fromTo(titleRef.current,
          { y: 80, opacity: 0, filter: "blur(8px)" },
          { y: 0, opacity: 1, filter: "blur(0px)", duration: 1.2 },
          "-=0.3"
        )
        .fromTo(subtitleRef.current,
          { y: 40, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.8 },
          "-=0.7"
        )
        .fromTo(btnRef.current,
          { y: 30, opacity: 0, scale: 0.9 },
          { y: 0, opacity: 1, scale: 1, duration: 0.6, ease: "back.out(2)" },
          "-=0.5"
        );

      // [UI-OPTIMIZE] 光晕呼吸
      gsap.to(glowRef.current, {
        scale: 1.12, opacity: 0.65, duration: 5,
        repeat: -1, yoyo: true, ease: "sine.inOut",
      });

      // [UI-OPTIMIZE] 滚动淡出
      gsap.to([titleRef.current, subtitleRef.current, badgeRef.current], {
        scrollTrigger: { trigger: sectionRef.current, start: "top top", end: "bottom top", scrub: 0.6 },
        y: -120, opacity: 0,
      });

      gsap.to(btnRef.current, {
        scrollTrigger: { trigger: sectionRef.current, start: "top top", end: "center+=100 top", scrub: 0.4 },
        y: 20, scale: 1.05,
      });
    }, sectionRef);

    return () => { ctx.revert(); };
  }, []);

  return (
    <section ref={sectionRef}
      className="relative flex h-screen flex-col items-center justify-center overflow-hidden"
      style={{ background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 45%, #2d1b69 100%)" }}>

      {/* [UI-OPTIMIZE] 三层径向光晕 */}
      <div ref={glowRef} className="pointer-events-none absolute inset-0 opacity-35"
        style={{
          background:
            "radial-gradient(ellipse 55% 45% at 50% 50%, rgba(43,75,130,0.45) 0%, transparent 70%)," +
            "radial-gradient(ellipse 35% 35% at 35% 55%, rgba(148,221,222,0.12) 0%, transparent 70%)," +
            "radial-gradient(ellipse 45% 35% at 65% 35%, rgba(247,180,167,0.10) 0%, transparent 70%)",
        }} />

      {/* [UI-OPTIMIZE] 网格纹理 */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)",
          backgroundSize: "80px 80px",
        }} />

      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        {/* [UI-OPTIMIZE] 徽标 */}
        <span ref={badgeRef}
          className="mb-8 inline-block rounded-full border px-5 py-2 text-xs tracking-[0.18em]"
          style={{
            borderColor: "rgba(148,221,222,0.25)",
            color: "var(--color-mint)",
            background: "rgba(148,221,222,0.05)",
            backdropFilter: "blur(8px)",
          }}>
          重庆 · 二手房数据分析平台
        </span>

        {/* [UI-OPTIMIZE] 主标题 — heading-xl 48px */}
        <h1 ref={titleRef}
          className="heading-xl text-5xl sm:text-6xl md:text-7xl lg:text-8xl"
          style={{
            background: "linear-gradient(180deg, #ffffff 0%, rgba(247,180,167,0.88) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}>
          重庆房价洞察
        </h1>

        {/* [UI-OPTIMIZE] 副标题 — Roboto Mono 16px */}
        <p ref={subtitleRef}
          className="subtitle mt-6 tracking-wide"
          style={{ color: "var(--color-text-secondary)" }}>
          基于 <span className="num-glow-pink">50,507</span> 条真实数据 · 机器学习驱动分析 · 数据驱动决策
        </p>

        {/* [UI-OPTIMIZE] 胶囊按钮 */}
        <Link ref={btnRef} href="/analysis"
          className="btn-capsule mt-12">
          <span>查看详情</span>
          <svg className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-0.5"
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>
        </Link>
      </div>

      {/* [UI-OPTIMIZE] 向下滚动 — CSS 动画箭头 */}
      <div className="absolute bottom-10 z-10 flex flex-col items-center gap-2 opacity-45">
        <span className="text-xs tracking-[0.2em]" style={{ color: "var(--color-text-hint)" }}>
          向下滚动
        </span>
        <svg className="scroll-arrow-anim h-4 w-4" fill="none" stroke="var(--color-mint)" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </div>
    </section>
  );
}
