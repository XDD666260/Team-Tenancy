import { notFound } from "next/navigation";
import Link from "next/link";
import SmoothScroll from "@/components/SmoothScroll";
import DistrictDetailClient from "@/components/Dashboard/DistrictDetailClient";
import { getDistrictDetail } from "@/lib/api";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ name: string }>;
}

export default async function DistrictDetailPage({ params }: Props) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);

  const detail = await getDistrictDetail(decoded);
  if (!detail || detail.house_count === 0) {
    notFound();
  }

  return (
    <SmoothScroll>
      <main style={{ background: "var(--bg-primary)", minHeight: "100vh" }}>
        {/* 返回导航 */}
        <div className="mx-auto max-w-4xl px-6 pt-8 sm:px-8">
          <Link
            href="/analysis"
            className="tag inline-flex items-center gap-2"
            style={{ padding: "8px 18px", fontSize: 13 }}
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            ← 返回仪表盘
          </Link>
        </div>

        <DistrictDetailClient detail={detail} />
      </main>
    </SmoothScroll>
  );
}
