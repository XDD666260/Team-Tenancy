"use client";

/**
 * Shift5 风格 — 数据英雄区
 * 大数字 + 标签 + 分割线，黑白极简
 */
export default function StatsHero({
  stats,
}: {
  stats: { value: string; label: string }[];
}) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-20 sm:px-8 lg:px-10">
      <hr className="hr mb-16" />
      <div className="grid grid-cols-2 gap-10 sm:grid-cols-3 lg:grid-cols-5">
        {stats.map((s) => (
          <div key={s.label}>
            <p className="stat-number" style={{ color: "var(--text-primary)" }}>
              {s.value}
            </p>
            <p className="stat-label mt-2">{s.label}</p>
          </div>
        ))}
      </div>
      <hr className="hr mt-16" />
    </div>
  );
}
