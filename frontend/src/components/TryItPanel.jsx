import { useState } from "react";
import { api, ApiError } from "../api.js";
import TicketResult from "./TicketResult.jsx";

const EXAMPLES = [
  {
    label: "Critical outage",
    subject: "URGENT: production is down",
    body: "Our production API has been down for 10 minutes, our entire team is blocked, and we are losing money every minute this continues.",
  },
  {
    label: "Billing question",
    subject: "Charged twice this month",
    body: "I noticed I was charged twice for my subscription this billing cycle. Could I get a refund for the duplicate charge? No rush.",
  },
  {
    label: "Vague ticket",
    subject: "invoice",
    body: "where is it",
  },
];

export default function TryItPanel() {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!subject.trim() && !body.trim()) {
      setError("Enter a subject or a body first.");
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await api.triageOne({ subject: subject.trim(), body: body.trim() });
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function loadExample(ex) {
    setSubject(ex.subject);
    setBody(ex.body);
    setResult(null);
    setError("");
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.label}
            onClick={() => loadExample(ex)}
            type="button"
            style={{
              fontSize: 12.5,
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid var(--line)",
              background: "var(--surface)",
              color: "var(--ink-soft)",
              cursor: "pointer",
            }}
          >
            {ex.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="Subject"
          style={{
            width: "100%",
            padding: "11px 14px",
            fontSize: 14,
            border: "1px solid var(--line)",
            borderRadius: "var(--radius)",
            marginBottom: 10,
            boxSizing: "border-box",
            background: "var(--surface)",
          }}
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Describe the issue the way a customer would..."
          rows={4}
          style={{
            width: "100%",
            padding: "11px 14px",
            fontSize: 14,
            border: "1px solid var(--line)",
            borderRadius: "var(--radius)",
            marginBottom: 12,
            boxSizing: "border-box",
            fontFamily: "inherit",
            resize: "vertical",
            background: "var(--surface)",
          }}
        />

        {error && (
          <div style={{ fontSize: 13, color: "var(--danger)", marginBottom: 12 }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: "10px 20px",
            fontSize: 13.5,
            fontWeight: 600,
            color: "#fff",
            background: loading ? "var(--ink-muted)" : "var(--ink)",
            border: "none",
            borderRadius: "var(--radius)",
            cursor: loading ? "default" : "pointer",
          }}
        >
          {loading ? "Triaging..." : "Triage this ticket"}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: 20, borderTop: "1px solid var(--line)" }}>
          <TicketResult result={result} defaultExpanded />
        </div>
      )}
    </div>
  );
}
