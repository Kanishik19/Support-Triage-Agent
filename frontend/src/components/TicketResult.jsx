import { useState } from "react";
import ConfidenceBar from "./ConfidenceBar.jsx";
import { URGENCY_META, CATEGORY_LABELS } from "../constants.js";

export default function TicketResult({ result, defaultExpanded = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const um = URGENCY_META[result.urgency] || URGENCY_META.low;

  return (
    <div
      style={{
        borderBottom: "1px solid var(--line)",
        padding: "16px 0",
      }}
    >
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: um.color,
            flexShrink: 0,
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14.5, fontWeight: 500, color: "var(--ink)", marginBottom: 2 }}>
            {result.subject}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--ink-muted)" }}>
            {um.label} &middot; {CATEGORY_LABELS[result.category] || result.category} &middot;{" "}
            <span style={{ color: "var(--ink-soft)" }}>{result.assigned_team}</span>
          </div>
        </div>
        {result.needs_human_review && (
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: "var(--warning)",
              background: "var(--warning-soft)",
              padding: "3px 9px",
              borderRadius: 999,
              flexShrink: 0,
            }}
          >
            Needs review
          </span>
        )}
        <ConfidenceBar value={result.confidence} color={um.color} />
        <span
          style={{
            fontSize: 11,
            color: "var(--ink-muted)",
            transform: expanded ? "rotate(180deg)" : "none",
            transition: "transform 0.15s",
            flexShrink: 0,
          }}
        >
          &#9662;
        </span>
      </div>

      {expanded && (
        <div style={{ marginTop: 12, paddingLeft: 20, fontSize: 13, color: "var(--ink-soft)", lineHeight: 1.6 }}>
          <p style={{ margin: "0 0 8px" }}>{result.reasoning}</p>
          {result.needs_human_review && result.review_reasons?.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 16, color: "var(--warning)" }}>
              {result.review_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
          <div style={{ marginTop: 8, fontSize: 11.5, color: "var(--ink-muted)" }}>
            {result.ticket_id} &middot; classified via {result.method}
          </div>
        </div>
      )}
    </div>
  );
}
