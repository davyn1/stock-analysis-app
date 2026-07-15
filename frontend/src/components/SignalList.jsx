const SHOW_LAST = 8;

function formatTime(time) {
  // Daily/weekly bars use "YYYY-MM-DD" strings; intraday bars use Unix seconds.
  if (typeof time === "number") {
    return new Date(time * 1000).toLocaleString([], {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  }
  return time;
}

export default function SignalList({ signals }) {
  if (!signals?.length) {
    return <p className="signals-empty">No signals detected in this window.</p>;
  }
  const recent = signals.slice(-SHOW_LAST).reverse(); // newest first

  return (
    <div className="signal-list">
      <h3>Signals <span className="signal-count">({signals.length} in window)</span></h3>
      <ul>
        {recent.map((s, i) => (
          <li key={`${s.time}-${s.type}-${i}`} className={`signal ${s.direction}`}>
            <span className="signal-arrow">{s.direction === "bullish" ? "▲" : "▼"}</span>
            <span className="signal-when">{formatTime(s.time)}</span>
            <span className="signal-label">{s.label}</span>
            <span className="signal-price">${s.price.toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
