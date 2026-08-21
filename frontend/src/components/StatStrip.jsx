function Stat({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 22, fontWeight: 600, color: "var(--ink)" }}>{value}</div>
      <div style={{ fontSize: 11.5, color: "var(--ink-muted)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
        {label}
      </div>
    </div>
  );
}

export default function StatStrip({ stats }) {
  if (!stats) return null;
  return (
    <div style={{ display: "flex", gap: 28, marginBottom: 20, flexWrap: "wrap" }}>
      <Stat label="Tickets" value={stats.total} />
      <Stat label="Flagged for review" value={stats.flagged_for_review} />
      <Stat label="Avg confidence" value={`${Math.round(stats.avg_confidence * 100)}%`} />
      <Stat label="Processed in" value={`${stats.elapsed_seconds}s`} />
    </div>
  );
}
