import SmoothScroll from "@/components/SmoothScroll";
import Hero from "@/components/Hero/Hero";
import Link from "next/link";

export default function Home() {
  return (
    <SmoothScroll>
      <main style={{ background: "var(--bg-primary)" }}>
        <Hero />

        {/* 首页下半部分 — 预览引导区 */}
        <section className="mx-auto max-w-5xl px-6 pb-32 pt-20 sm:px-8">
          <hr className="hr mb-16" />

          <div className="grid grid-cols-1 gap-10 sm:grid-cols-3">
            <div>
              <p className="stat-label mb-3">数据规模</p>
              <p className="stat-number text-3xl sm:text-4xl" style={{ color: "var(--text-primary)" }}>
                50,507
              </p>
              <p className="body mt-2">
                条真实在售房源，覆盖安居客和链家两大平台
              </p>
            </div>
            <div>
              <p className="stat-label mb-3">分析模型</p>
              <p className="stat-number text-3xl sm:text-4xl" style={{ color: "var(--text-primary)" }}>
                4+
              </p>
              <p className="body mt-2">
                RandomForest · GradientBoosting · KMeans · Apriori
              </p>
            </div>
            <div>
              <p className="stat-label mb-3">覆盖范围</p>
              <p className="stat-number text-3xl sm:text-4xl" style={{ color: "var(--text-primary)" }}>
                30+
              </p>
              <p className="body mt-2">
                个重庆区县，从渝中核心到远郊区县全面覆盖
              </p>
            </div>
          </div>

          <hr className="hr my-16" />

          <div className="flex flex-col items-center gap-6 text-center">
            <p className="lead max-w-xl">
              查看完整的<strong style={{ color: "var(--accent-mint)" }}>数据仪表盘</strong>，
              包含房价预测、聚类画像、关联规则等深度分析。
            </p>
            <Link href="/analysis" className="tag" style={{
              padding: "14px 32px", fontSize: 15, fontWeight: 500,
              borderColor: "var(--accent-mint)", color: "var(--accent-mint)",
            }}>
              进入数据仪表盘 →
            </Link>
          </div>
        </section>
      </main>
    </SmoothScroll>
  );
}
