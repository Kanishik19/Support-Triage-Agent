export default function ConfidenceBar({ value, color }) {
  const pct = Math.round(value * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 12, color: "var(--ink-soft)", fontVariantNumeric: "tabular-nums", minWidth: 32 }}>
        {pct}%
      </span>
      <div style={{ width: 64, height: 4, background: "var(--line)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color }} />
      </div>
    </div>
  );
}
