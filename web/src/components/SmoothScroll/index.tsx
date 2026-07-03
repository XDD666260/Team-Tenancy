"use client";

import { useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * 轻量滚动容器 — 仅注册 GSAP ScrollTrigger 刷新
 * 不再使用 Lenis，改用浏览器原生 scroll-behavior: smooth
 */
export default function SmoothScroll({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // 监听原生滚动，同步刷新 ScrollTrigger
    const onScroll = () => ScrollTrigger.update();
    window.addEventListener("scroll", onScroll, { passive: true });

    // 刷新 GSAP ticker 以支持 ScrollTrigger
    const tick = gsap.ticker.add(() => {
      ScrollTrigger.update();
    });

    return () => {
      window.removeEventListener("scroll", onScroll);
      gsap.ticker.remove(tick);
      ScrollTrigger.getAll().forEach((t) => t.kill());
    };
  }, []);

  return <>{children}</>;
}
