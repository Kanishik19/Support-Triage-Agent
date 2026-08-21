import { useEffect, useState } from "react";
import Header from "./components/Header.jsx";
import TryItPanel from "./components/TryItPanel.jsx";
import QueuePanel from "./components/QueuePanel.jsx";
import { api } from "./api.js";

export default function App() {
  const [tab, setTab] = useState("try");
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    api
      .health()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  return (
    <div>
      <Header apiStatus={apiStatus} />

      <main style={{ maxWidth: 880, margin: "0 auto", padding: "28px 24px 80px" }}>
        {apiStatus === "offline" && (
          <div
            style={{
              fontSize: 13.5,
              color: "var(--danger)",
              background: "var(--danger-soft)",
              borderRadius: "var(--radius)",
              padding: "14px 16px",
              marginBottom: 20,
            }}
          >
            Can't reach the triage API. Run <code>python api.py</code> in the project root, then reload this page.
          </div>
        )}

        <div style={{ display: "flex", gap: 4, marginBottom: 24, borderBottom: "1px solid var(--line)" }}>
          {[
            ["try", "Try it yourself"],
            ["queue", "Sample queue"],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              style={{
                padding: "10px 4px",
                marginRight: 20,
                fontSize: 14,
                fontWeight: 500,
                border: "none",
                background: "none",
                cursor: "pointer",
                color: tab === key ? "var(--ink)" : "var(--ink-muted)",
                borderBottom: tab === key ? "2px solid var(--accent)" : "2px solid transparent",
                marginBottom: -1,
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "try" ? <TryItPanel /> : <QueuePanel />}
      </main>
    </div>
  );
}
