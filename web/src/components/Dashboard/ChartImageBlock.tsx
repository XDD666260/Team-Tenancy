"use client";

import { useRef, useEffect } from "react";
import Image from "next/image";

/**
 * Shift5 风格图文模块
 * 左文字 + 右图片，交替 layout 创造排版节奏
 */
interface Props {
  layout?: "text-left" | "text-right";
  tag: string;
  title: string;
  description: string;
  bulletPoints?: string[];
  imgSrc: string;
  imgAlt: string;
  imgWidth: number;
  imgHeight: number;
  priority?: boolean;
}

export default function ChartImageBlock({
  layout = "text-left",
  tag, title, description, bulletPoints,
  imgSrc, imgAlt, imgWidth, imgHeight, priority,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.style.animation = "fadeUp 0.7s ease forwards";
          obs.unobserve(el);
        }
      },
      { threshold: 0.15 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const TextCol = (
    <div className="flex flex-col justify-center">
      <span className="tag mb-6">{tag}</span>
      <h3 className="h3 mb-4" style={{ color: "var(--text-primary)" }}>{title}</h3>
      <p className="lead mb-5">{description}</p>
      {bulletPoints && (
        <ul className="space-y-2">
          {bulletPoints.map((pt, i) => (
            <li key={i} className="body flex items-start gap-2" style={{ fontSize: 14 }}>
              <span className="mt-1.5 h-1 w-1 flex-shrink-0 rounded-full" style={{ background: "var(--accent-mint)" }} />
              {pt}
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  const ImageCol = (
    <div className="relative flex items-center justify-center overflow-hidden rounded-xl"
      style={{ border: "1px solid var(--border-subtle)", background: "var(--bg-secondary)" }}>
      <Image
        src={imgSrc}
        alt={imgAlt}
        width={imgWidth}
        height={imgHeight}
        priority={priority}
        className="h-auto w-full object-contain"
        style={{ maxHeight: 420 }}
      />
    </div>
  );

  return (
    <div ref={ref} className="mx-auto max-w-6xl px-6 py-16 sm:px-8 lg:px-10">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-16">
        {layout === "text-left" ? (
          <>{TextCol}{ImageCol}</>
        ) : (
          <>{ImageCol}{TextCol}</>
        )}
      </div>
    </div>
  );
}
