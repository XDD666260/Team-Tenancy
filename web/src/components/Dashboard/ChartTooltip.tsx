"use client";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div
      style={{
        background: "rgba(15, 15, 28, 0.96)",
        border: "1px solid rgba(148, 221, 222, 0.2)",
        borderRadius: 12,
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        padding: "12px 16px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
      }}
    >
      {label && (
        <p style={{ color: "#aaaaaa", fontSize: 12, fontWeight: 400, marginBottom: 6 }}>
          {label}
        </p>
      )}
      {payload.map((entry: { name?: string; value?: number; color?: string }, i: number) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginTop: i > 0 ? 3 : 0 }}>
          <span
            style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: entry.color || "#94ddde",
              boxShadow: `0 0 6px ${entry.color || "#94ddde"}66`,
            }}
          />
          <span style={{ color: "#cccccc", fontSize: 13, fontWeight: 300 }}>
            {entry.name}
          </span>
          <span style={{ color: "#ffffff", fontSize: 13, fontWeight: 500 }}>
            {entry.value?.toLocaleString?.() || entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}
