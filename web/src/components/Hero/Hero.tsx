"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export default function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const badgeRef = useRef<HTMLSpanElement>(null);

  // 按钮 hover 状态
  const [btnHovered, setBtnHovered] = useState(false);

  // [FIX-1] 点击平滑滚动到仪表盘
  const scrollToDashboard = useCallback(() => {
    const target = document.getElementById("dashboard-section");
    if (target) {
      target.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // [FIX-2] 入场动画 — 只播放一次
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.fromTo(
        badgeRef.current,
        { y: 30, opacity: 0, scale: 0.9 },
        { y: 0, opacity: 1, scale: 1, duration: 0.7, ease: "back.out(1.7)" }
      )
        .fromTo(
          titleRef.current,
          { y: 60, opacity: 0, filter: "blur(6px)" },
          { y: 0, opacity: 1, filter: "blur(0px)", duration: 1.2 },
          "-=0.4"
        )
        .fromTo(
          subtitleRef.current,
          { y: 30, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.7 },
          "-=0.6"
        )
        .fromTo(
          btnRef.current,
          { y: 20, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.5 },
          "-=0.4"
        );

      // [FIX-3] 滚动淡出 — 使用 toggleActions 确保回滚时恢复
      // start: "top top" (Hero顶部到视口顶部时开始)
      // end: "bottom top" (Hero底部到视口顶部时结束)
      // 当元素在视口中时完全可见，离开时淡出，回来时恢复
      if (contentRef.current) {
        gsap.to(contentRef.current, {
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top top",
            end: "bottom top",
            scrub: 0.5,
            // 关键: scrub 会自动在回滚时反向执行动画
          },
          opacity: 0,
          y: -60,
        });
      }
    }, sectionRef);

    return () => {
      ctx.revert();
    };
  }, []);

  return (
    <>
      {/* ═══ Hero 全屏区 ═══ */}
      <section
        ref={sectionRef}
        className="relative flex h-screen flex-col items-center justify-center overflow-hidden"
        style={{
          background:
            "linear-gradient(160deg, #0a0a14 0%, #141a30 30%, #1e2a4a 60%, #1a1430 100%)",
        }}
      >
        {/* [FIX-4] 柔和径向光晕 — 标题后方焦点 */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 50% 40% at 50% 45%, rgba(43,75,130,0.18) 0%, transparent 60%)," +
              "radial-gradient(circle at 50% 50%, rgba(255,255,255,0.04) 0%, transparent 70%)," +
              "radial-gradient(ellipse 30% 25% at 35% 30%, rgba(148,221,222,0.06) 0%, transparent 60%)," +
              "radial-gradient(ellipse 35% 30% at 65% 65%, rgba(247,180,167,0.05) 0%, transparent 60%)",
          }}
        />

        {/* 网格纹理 */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.018]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px)," +
              "linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)",
            backgroundSize: "72px 72px",
          }}
        />

        {/* ═══ 内容区 — 被 ScrollTrigger 控制淡出 ═══ */}
        <div
          ref={contentRef}
          className="relative z-10 flex flex-col items-center px-6 text-center"
        >
          {/* 品牌徽标 */}
          <span
            ref={badgeRef}
            className="mb-8 inline-flex items-center gap-2 rounded-full border px-5 py-2 text-xs tracking-[0.15em]"
            style={{
              borderColor: "rgba(148,221,222,0.25)",
              color: "#94ddde",
              background: "rgba(148,221,222,0.06)",
              backdropFilter: "blur(8px)",
            }}
          >
            <span
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ background: "#94ddde", boxShadow: "0 0 6px rgba(148,221,222,0.5)" }}
            />
            重庆 · 二手房数据分析平台
          </span>

          {/* [FIX-5] 标题 64px — 加大字号 + 渐变文字 */}
          <h1
            ref={titleRef}
            className="text-5xl font-light tracking-tight sm:text-6xl md:text-7xl"
            style={{
              fontSize: "clamp(40px, 8vw, 72px)",
              fontWeight: 300,
              letterSpacing: "-0.02em",
              lineHeight: 1.1,
              background:
                "linear-gradient(180deg, #ffffff 0%, rgba(247,180,167,0.85) 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            重庆房价洞察
          </h1>

          {/* [FIX-6] 副标题 #cccccc + 加粗 */}
          <p
            ref={subtitleRef}
            className="mt-6 max-w-2xl text-base tracking-wide sm:text-lg"
            style={{
              color: "#cccccc",
              fontWeight: 400,
              lineHeight: 1.5,
            }}
          >
            基于{" "}
            <strong style={{ color: "#f7b4a7", fontWeight: 600 }}>
              50,507
            </strong>{" "}
            条真实二手房数据 · 机器学习驱动分析 · 数据驱动决策
          </p>

          {/* [FIX-7] 升级版胶囊按钮 */}
          <button
            ref={btnRef}
            onClick={scrollToDashboard}
            onMouseEnter={() => setBtnHovered(true)}
            onMouseLeave={() => setBtnHovered(false)}
            className="group mt-10 inline-flex items-center gap-3"
            style={{
              background: btnHovered
                ? "rgba(255,255,255,0.15)"
                : "rgba(255,255,255,0.08)",
              border: btnHovered
                ? "1px solid rgba(148,221,222,0.35)"
                : "1px solid rgba(255,255,255,0.2)",
              borderRadius: 999,
              padding: "14px 32px",
              fontSize: 16,
              fontWeight: 400,
              color: "#ffffff",
              cursor: "pointer",
              transform: btnHovered ? "scale(1.05)" : "scale(1)",
              boxShadow: btnHovered
                ? "0 0 24px rgba(247,180,167,0.3), 0 8px 24px rgba(0,0,0,0.3)"
                : "0 4px 16px rgba(0,0,0,0.2)",
              transition: "all 0.3s ease",
              backdropFilter: "blur(10px)",
              outline: "none",
            }}
          >
            <span>查看详情</span>
            {/* [FIX-8] 箭头 hover 时微摆 */}
            <svg
              className="transition-transform duration-300"
              style={{
                transform: btnHovered ? "translateX(3px)" : "translateX(0)",
              }}
              width="16"
              height="16"
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
          </button>
        </div>

        {/* [FIX-9] 向下滚动 — CSS bounce 动画 */}
        <div className="absolute bottom-10 z-10 flex flex-col items-center gap-3">
          <span
            className="text-xs tracking-[0.2em]"
            style={{ color: "#888888" }}
          >
            向下滚动
          </span>
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="#94ddde"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
            style={{
              stroke: "#94ddde",
              animation: "heroBounce 2s ease-in-out infinite",
            }}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 8.25l-7.5 7.5-7.5-7.5"
            />
          </svg>
        </div>
      </section>

      {/* ═══ 仪表盘目标锚点 ═══ */}
      <div id="dashboard-section" />
    </>
  );
}
