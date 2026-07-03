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
      <main className="min-h-screen bg-bg-dark">
        {/* 返回导航 */}
        <div className="mx-auto max-w-4xl px-4 pt-6 sm:px-6">
          <Link
            href="/analysis"
            className="inline-flex items-center gap-2 text-sm font-light transition-colors duration-300 hover:opacity-70"
            style={{ color: "#aaaaaa" }}
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            返回数据仪表盘
          </Link>
        </div>

        <DistrictDetailClient detail={detail} />
      </main>
    </SmoothScroll>
  );
}
