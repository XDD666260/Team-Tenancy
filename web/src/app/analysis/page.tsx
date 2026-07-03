import SmoothScroll from "@/components/SmoothScroll";

export default function AnalysisPage() {
  return (
    <SmoothScroll>
      <main className="flex min-h-screen items-center justify-center bg-bg-dark">
        <div className="text-center">
          <h1 className="text-3xl font-light tracking-wider text-white">
            数据分析
          </h1>
          <p
            className="mt-4 text-lg font-light"
            style={{ color: "var(--color-text-secondary)" }}
          >
            数据概览与可视化图表即将呈现…
          </p>
          <div
            className="mx-auto mt-8 h-0.5 w-24 rounded-full"
            style={{ background: "var(--color-mint)" }}
          />
        </div>
      </main>
    </SmoothScroll>
  );
}
