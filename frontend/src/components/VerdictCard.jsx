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

// Factors grouped by evidence type; the group label only appears when a horizon
// mixes groups (i.e. the long horizon once fundamentals are enabled).
function FactorList({ factors }) {
  const groups = [...new Set(factors.map((f) => f.group ?? "technicals"))];
  return (
    <ul className="verdict-factors">
      {groups.map((g) => (
        <li key={g}>
          {groups.length > 1 && <span className="vf-group">{g}</span>}
          <ul className="verdict-factors">
            {factors
              .filter((f) => (f.group ?? "technicals") === g)
              .map((f) => (
                <li key={f.label} className={`verdict-factor ${f.direction}`}>
                  <span className="vf-icon">{DIRECTION_ICON[f.direction]}</span>
                  <span>
                    <strong>{f.label}.</strong> {f.detail}
                  </span>
                </li>
              ))}
          </ul>
        </li>
      ))}
    </ul>
  );
}

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
      {open && <FactorList factors={h.factors} />}
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
