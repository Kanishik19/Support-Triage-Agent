export default function Header({ apiStatus }) {
  const statusMeta = {
    checking: { color: "var(--ink-muted)", label: "Checking API..." },
    online: { color: "#3b7a3b", label: "API connected" },
    offline: { color: "var(--danger)", label: "API unreachable" },
  }[apiStatus];

  return (
    <header
      style={{
        borderBottom: "1px solid var(--line)",
        padding: "28px 0 20px",
      }}
    >
      <div
        style={{
          maxWidth: 880,
          margin: "0 auto",
          padding: "0 24px",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "var(--accent)",
              marginBottom: 6,
            }}
          >
            Support ops
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 600, margin: "0 0 4px", letterSpacing: "-0.01em" }}>
            Ticket triage agent
          </h1>
          <p style={{ fontSize: 13.5, color: "var(--ink-soft)", margin: 0 }}>
            Classifies, scores, and routes support tickets automatically.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4, flexShrink: 0 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: statusMeta.color,
              display: "inline-block",
            }}
          />
          <span style={{ fontSize: 12, color: "var(--ink-soft)" }}>{statusMeta.label}</span>
        </div>
      </div>
    </header>
  );
}
