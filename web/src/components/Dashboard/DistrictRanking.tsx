"use client";

import { useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import type { DistrictStat } from "@/lib/types";

gsap.registerPlugin(ScrollTrigger);

/* TOP 排名渐变色 — 从亮到暗 */
const RANK_GRADIENT = [
  "#4a90e2", // #1
  "#5b7fc5",
  "#6c6ea8",
  "#7d5d8b",
  "#9b59b6", // #5
  "#a75aaa",
  "#b35b9e",
  "#bf5c92",
  "#e91e63", // #9
  "#e0557a",
  "#e16e91",
  "#e287a8",
  "#ff5722", // #13
  "#ff7043",
  "#ff8964",
];

interface Props {
  districts: DistrictStat[];
}

// 中文→拼音 slug
const DISTRICT_SLUG: Record<string, string> = {
  "两江新区": "liangjiang", "渝北区": "yubei", "江北区": "jiangbei",
  "沙坪坝区": "shapingba", "南岸区": "nanan", "渝中区": "yuzhong",
  "九龙坡区": "jiulongpo", "巴南区": "banan", "北碚区": "beibei",
  "大渡口区": "dadukou", "璧山区": "bishan", "江津区": "jiangjin",
  "长寿区": "changshou", "合川区": "hechuan", "永川区": "yongchuan",
};

export default function DistrictRanking({ districts }: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const initialized = useRef(false);
  const router = useRouter();

  const data = [...districts].slice(0, 15).reverse();

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        sectionRef.current,
        { opacity: 0, y: 36 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          ease: "power3.out",
          scrollTrigger: { trigger: sectionRef.current, start: "top 82%" },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  return (
    <section ref={sectionRef} className="relative pb-[10px]">
      <div>
        <div className="mb-8 flex items-center justify-between">
          <h2
            className="text-lg font-medium tracking-wider sm:text-xl"
            style={{
              fontFamily: '"PingFang SC", "Noto Sans SC", sans-serif',
              fontWeight: 500,
              color: "#ffffff",
            }}
          >
            区县房源排名
          </h2>
          <span
            className="text-sm font-light"
            style={{ color: "#aaaaaa", fontSize: 14 }}
          >
            TOP 15
          </span>
        </div>

        <div id="district-chart" className="h-[460px] sm:h-[520px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 0, right: 12, left: 8, bottom: 0 }}
              barCategoryGap="28%"
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.05)"
                horizontal={false}
              />
              <XAxis
                type="number"
                axisLine={false}
                tickLine={false}
                tick={{
                  fill: "#aaaaaa",
                  fontSize: 11,
                  fontWeight: 300,
                }}
                tickFormatter={(v: number) =>
                  v >= 10000 ? (v / 10000).toFixed(0) + "万" : String(v)
                }
              />
              <YAxis
                type="category"
                dataKey="district"
                axisLine={false}
                tickLine={false}
                width={76}
                tick={{
                  fill: "#cccccc",
                  fontSize: 13,
                  fontWeight: 300,
                  fontFamily: '"PingFang SC", "Noto Sans SC", sans-serif',
                }}
              />
              <Tooltip
                content={<ChartTooltip />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar
                dataKey="count"
                radius={[0, 6, 6, 0]}
                maxBarSize={24}
                cursor="pointer"
                onClick={(entry) => {
                  const d = (entry as unknown as DistrictStat);
                  const slug = DISTRICT_SLUG[d.district] || d.district;
                  router.push(`/analysis/district/${slug}`);
                }}
                onMouseEnter={(_, index) => {
                  const bars = document.querySelectorAll(
                    "#district-chart .recharts-bar-rectangle"
                  );
                  bars.forEach((bar, i) => {
                    const el = bar as HTMLElement;
                    if (i === index) {
                      el.style.filter = "brightness(1.4) drop-shadow(0 3px 10px rgba(0,0,0,0.5))";
                    } else {
                      el.style.opacity = "0.4";
                    }
                  });
                }}
                onMouseLeave={() => {
                  const bars = document.querySelectorAll(
                    "#district-chart .recharts-bar-rectangle"
                  );
                  bars.forEach((bar) => {
                    const el = bar as HTMLElement;
                    el.style.filter = "";
                    el.style.opacity = "1";
                  });
                }}
              >
                {data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={RANK_GRADIENT[i % RANK_GRADIENT.length]}
                    fillOpacity={0.78}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
