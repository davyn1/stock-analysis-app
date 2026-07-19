import { useState } from "react";

// The verdict is decided by deterministic backend rules (verdict.py) — this
// component only renders it. Factors are shown so the read is fully auditable.
const VERDICT_COPY = {
  favorable: "Favorable",
  neutral: "Neutral",
  unfavorable: "Unfavorable",
  insufficient: "Not enough data",
};

const DIRECTION_ICON = { bullish: "▲", bearish: "▼", neutral: "•", unavailable: "–" };

function Horizon({ h }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`verdict-horizon ${h.verdict}`}>
      <div className="verdict-horizon-head">
        <span className="verdict-horizon-label">{h.label}</span>
        <span className="verdict-window">{h.window}</span>
      </div>
      <span className={`verdict-badge ${h.verdict}`}>{VERDICT_COPY[h.verdict] ?? h.verdict}</span>
      <button
        type="button"
        className="verdict-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        {open ? "Hide factors" : `Why? ${h.score >= 0 ? "+" : ""}${h.score} of ${h.max_score} checks`}
      </button>
      {open && (
        <ul className="verdict-factors">
          {h.factors.map((f) => (
            <li key={f.label} className={`verdict-factor ${f.direction}`}>
              <span className="vf-icon">{DIRECTION_ICON[f.direction]}</span>
              <span>
                <strong>{f.label}.</strong> {f.detail}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function VerdictCard({ verdict }) {
  if (!verdict?.horizons?.length) return null;
  return (
    <div className="verdict-card">
      <div className="verdict-title">
        <h3>Technical read</h3>
        <span className="verdict-basis">rules-based · {verdict.basis}</span>
      </div>
      <div className="verdict-grid">
        {verdict.horizons.map((h) => (
          <Horizon key={h.key} h={h} />
        ))}
      </div>
    </div>
  );
}
