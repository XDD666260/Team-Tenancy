import { notFound } from "next/navigation";
import Link from "next/link";
import SmoothScroll from "@/components/SmoothScroll";
import DistrictDetailClient from "@/components/Dashboard/DistrictDetailClient";

// 预生成的区县列表
const KNOWN_DISTRICTS = [
  "渝北区", "沙坪坝区", "南岸区", "江北区", "九龙坡区",
  "两江新区", "巴南区", "渝中区", "北碚区", "大渡口区",
  "璧山区", "江津区", "长寿区", "合川区", "永川区",
];

export function generateStaticParams() {
  return KNOWN_DISTRICTS.map((name) => ({ name: encodeURIComponent(name) }));
}

interface Props {
  params: Promise<{ name: string }>;
}

export default async function DistrictDetailPage({ params }: Props) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);

  if (!KNOWN_DISTRICTS.includes(decoded)) {
    notFound();
  }

  // 静态构建时用内置数据
  const dummyDetail = getDistrictDummy(decoded);

  return (
    <SmoothScroll>
      <main style={{ background: "var(--bg-primary)", minHeight: "100vh" }}>
        <div className="mx-auto max-w-4xl px-6 pt-8 sm:px-8">
          <Link href="/analysis" className="tag inline-flex items-center gap-2"
            style={{ padding: "8px 18px", fontSize: 13 }}>
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            ← 返回仪表盘
          </Link>
        </div>
        <DistrictDetailClient detail={dummyDetail} />
      </main>
    </SmoothScroll>
  );
}

function getDistrictDummy(name: string) {
  const base: Record<string, { count: number; unit: number; total: number; area: number; max: number; min: number }> = {
    "渝北区": { count: 6842, unit: 9520, total: 98.5, area: 103.5, max: 380, min: 22 },
    "两江新区": { count: 3280, unit: 12450, total: 135.6, area: 108.9, max: 520, min: 35 },
    "渝中区": { count: 2680, unit: 13800, total: 152.7, area: 110.6, max: 680, min: 40 },
    "江北区": { count: 3910, unit: 11200, total: 118.2, area: 105.2, max: 450, min: 30 },
    "沙坪坝区": { count: 5120, unit: 7830, total: 72.1, area: 92.3, max: 280, min: 18 },
    "南岸区": { count: 4380, unit: 8650, total: 85.3, area: 98.5, max: 320, min: 20 },
    "九龙坡区": { count: 3520, unit: 7420, total: 68.9, area: 93.1, max: 260, min: 15 },
    "巴南区": { count: 2950, unit: 6210, total: 58.3, area: 106.5, max: 200, min: 12 },
  };
  const d = base[name] || { count: 1500, unit: 7000, total: 70, area: 95, max: 250, min: 15 };
  return {
    district: name, house_count: d.count, avg_unit_price: d.unit, avg_total_price: d.total,
    avg_area: d.area, max_price: d.max, min_price: d.min,
    decoration_distribution: [
      { type: "精装", count: Math.floor(d.count * 0.38) }, { type: "简装", count: Math.floor(d.count * 0.28) },
      { type: "毛坯", count: Math.floor(d.count * 0.18) }, { type: "豪装", count: Math.floor(d.count * 0.10) },
      { type: "中装", count: Math.floor(d.count * 0.06) },
    ],
    layout_distribution: [
      { rooms: 1, count: Math.floor(d.count * 0.08) }, { rooms: 2, count: Math.floor(d.count * 0.28) },
      { rooms: 3, count: Math.floor(d.count * 0.42) }, { rooms: 4, count: Math.floor(d.count * 0.16) },
      { rooms: 5, count: Math.floor(d.count * 0.06) },
    ],
    price_distribution: [
      { range: "50万以下", count: Math.floor(d.count * 0.24) }, { range: "50-80万", count: Math.floor(d.count * 0.30) },
      { range: "80-120万", count: Math.floor(d.count * 0.22) }, { range: "120-200万", count: Math.floor(d.count * 0.15) },
      { range: "200-300万", count: Math.floor(d.count * 0.06) }, { range: "300万以上", count: Math.floor(d.count * 0.03) },
    ],
    area_distribution: [
      { range: "60㎡以下", count: Math.floor(d.count * 0.12) }, { range: "60-90㎡", count: Math.floor(d.count * 0.32) },
      { range: "90-120㎡", count: Math.floor(d.count * 0.30) }, { range: "120-150㎡", count: Math.floor(d.count * 0.18) },
      { range: "150㎡以上", count: Math.floor(d.count * 0.08) },
    ],
    top_communities: [
      { name: name + "花园一期", count: 320, avg_price: d.unit * 1.1 },
      { name: name + "新城国际", count: 280, avg_price: d.unit * 1.3 },
      { name: "龙湖" + name + "项目", count: 250, avg_price: d.unit * 1.5 },
      { name: "万科" + name + "中心", count: 210, avg_price: d.unit * 0.9 },
      { name: "保利" + name + "公馆", count: 180, avg_price: d.unit * 1.2 },
    ],
  };
}
