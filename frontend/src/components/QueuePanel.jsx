import { useEffect, useState } from "react";
import { api, ApiError } from "../api.js";
import TicketResult from "./TicketResult.jsx";
import StatStrip from "./StatStrip.jsx";
import { URGENCY_META, URGENCY_ORDER } from "../constants.js";

export default function QueuePanel() {
  const [results, setResults] = useState(null);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoading(true);
      setError("");
      try {
        const tickets = await api.sampleTickets();
        const batch = await api.triageBatch(tickets);
        if (!cancelled) {
          const sorted = [...batch.results].sort(
            (a, b) => URGENCY_ORDER[a.urgency] - URGENCY_ORDER[b.urgency]
          );
          setResults(sorted);
          setStats(batch.stats);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Failed to load the ticket queue.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <div style={{ fontSize: 13.5, color: "var(--ink-soft)", padding: "20px 0" }}>Loading ticket queue...</div>;
  }

  if (error) {
    return (
      <div
        style={{
          fontSize: 13.5,
          color: "var(--danger)",
          background: "var(--danger-soft)",
          borderRadius: "var(--radius)",
          padding: "14px 16px",
        }}
      >
        {error}
      </div>
    );
  }

  const filtered = filter === "all" ? results : results.filter((r) => r.urgency === filter);

  return (
    <div>
      <StatStrip stats={stats} />

      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        {["all", "critical", "high", "medium", "low"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              fontSize: 12.5,
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid var(--line)",
              background: filter === f ? "var(--ink)" : "var(--surface)",
              color: filter === f ? "#fff" : "var(--ink-soft)",
              cursor: "pointer",
            }}
          >
            {f === "all" ? "All" : URGENCY_META[f].label}
          </button>
        ))}
      </div>

      <div style={{ borderTop: "1px solid var(--line)" }}>
        {filtered.map((r) => (
          <TicketResult key={r.ticket_id} result={r} />
        ))}
      </div>
    </div>
  );
}
