import SmoothScroll from "@/components/SmoothScroll";
import Hero from "@/components/Hero/Hero";
import Link from "next/link";

export default function Home() {
  return (
    <SmoothScroll>
      <main style={{ background: "var(--bg-primary)" }}>
        <Hero />

        {/* Hero 下方的仪表盘预览区 — #dashboard-section 锚点 */}
        <section
          id="dashboard-section"
          className="mx-auto max-w-5xl px-6 pb-32 pt-20 sm:px-8"
        >
          <hr className="hr mb-16" />

          {/* 三列核心数据 */}
          <div className="grid grid-cols-1 gap-12 sm:grid-cols-3">
            <div>
              <p className="stat-label mb-3">数据规模</p>
              <p
                className="stat-number text-3xl sm:text-4xl"
                style={{ color: "var(--text-primary)" }}
              >
                五万余条
              </p>
              <p className="body mt-2">
                二手房数据，覆盖安居客和链家两大平台
              </p>
            </div>
            <div>
              <p className="stat-label mb-3">分析模型</p>
              <p
                className="stat-number text-3xl sm:text-4xl"
                style={{ color: "var(--text-primary)" }}
              >
                4+
              </p>
              <p className="body mt-2">
                RandomForest · GradientBoosting · KMeans · Apriori
              </p>
            </div>
            <div>
              <p className="stat-label mb-3">覆盖区县</p>
              <p
                className="stat-number text-3xl sm:text-4xl"
                style={{ color: "var(--text-primary)" }}
              >
                39
              </p>
              <p className="body mt-2">
                个重庆区县，从渝中核心到远郊区县全面覆盖
              </p>
            </div>
          </div>

          <hr className="hr my-16" />

          {/* 进入仪表盘链接 */}
          <div className="flex flex-col items-center gap-6 text-center">
            <p className="lead max-w-xl">
              查看完整的{" "}
              <strong style={{ color: "var(--accent-mint)" }}>
                数据仪表盘
              </strong>
              ，包含房价预测、聚类画像、关联规则等深度分析。
            </p>
            <Link
              href="/analysis"
              className="tag"
              style={{
                padding: "14px 32px",
                fontSize: 15,
                fontWeight: 500,
                borderColor: "var(--accent-mint)",
                color: "var(--accent-mint)",
              }}
            >
              进入数据仪表盘 →
            </Link>
          </div>
        </section>
      </main>
    </SmoothScroll>
  );
}
