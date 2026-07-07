import { useEffect, useRef, useState } from "react";
import { LABELS, DESCRIPTIONS, formatValue } from "../indicatorLabels.js";

export default function IndicatorGrid({ indicators }) {
  const entries = Object.entries(indicators);
  const [pinned, setPinned] = useState(null); // key whose tooltip is click-pinned
  const gridRef = useRef(null);

  // Close a pinned tooltip on outside click or Escape (tap-friendly behavior).
  useEffect(() => {
    if (!pinned) return;
    const onDown = (e) => {
      if (gridRef.current && !gridRef.current.contains(e.target)) setPinned(null);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setPinned(null);
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [pinned]);

  if (entries.length === 0) return null;

  return (
    <div className="indicator-grid" ref={gridRef}>
      {entries.map(([key, value]) => {
        const tip = DESCRIPTIONS[key];
        const isPinned = pinned === key;
        return (
          <div
            className={`indicator${tip ? " has-tip" : ""}${isPinned ? " pinned" : ""}`}
            key={key}
            tabIndex={tip ? 0 : undefined}
            onClick={tip ? () => setPinned(isPinned ? null : key) : undefined}
            onKeyDown={
              tip
                ? (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setPinned(isPinned ? null : key);
                    }
                  }
                : undefined
            }
          >
            <span className="indicator-label">
              {LABELS[key] ?? key}
              {tip && <span className="info-dot" aria-hidden="true">ⓘ</span>}
            </span>
            <span className="indicator-value">{formatValue(value)}</span>
            {tip && (
              <span className="indicator-tip" role="tooltip">
                {tip}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
