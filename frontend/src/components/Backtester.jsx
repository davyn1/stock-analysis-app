import { useEffect, useState } from "react";
import EquityChart from "./EquityChart.jsx";
import { fetchStrategies, runBacktest } from "../api.js";

function pct(v) {
  return v == null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function Metric({ label, value, tone }) {
  return (
    <div className="bt-metric">
      <span className="bt-metric-label">{label}</span>
      <span className={`bt-metric-value${tone ? ` ${tone}` : ""}`}>{value}</span>
    </div>
  );
}

function Trades({ trades }) {
  if (!trades?.length) {
    return <p className="signals-empty">No trades — no entry signal fired in this window.</p>;
  }
  return (
    <div className="bt-trades">
      <table>
        <thead>
          <tr>
            <th>Entry</th>
            <th>Exit</th>
            <th className="num">Return</th>
            <th className="num">Bars</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t, i) => (
            <tr key={`${t.entry_time}-${i}`} className={t.return_pct >= 0 ? "up" : "down"}>
              <td>{t.entry_time} <span className="bt-at">@${t.entry_price}</span></td>
              <td>
                {t.open
                  ? <span className="bt-open">open @${t.exit_price}</span>
                  : <>{t.exit_time} <span className="bt-at">@${t.exit_price}</span></>}
              </td>
              <td className="num">{pct(t.return_pct)}</td>
              <td className="num">{t.bars_held}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Backtest panel scoped to the currently analyzed symbol. Strategy logic is
// deterministic on the backend — this just picks a strategy and renders results.
export default function Backtester({ symbol }) {
  const [strategies, setStrategies] = useState([]);
  const [strategy, setStrategy] = useState("sma_cross");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch(() => setStrategies([]));
  }, []);

  // A new symbol invalidates any prior result.
  useEffect(() => {
    setResult(null);
    setError(null);
  }, [symbol]);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      setResult(await runBacktest({ symbol, strategy }));
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const current = strategies.find((s) => s.key === strategy);
  const beatsHold = result && result.total_return_pct > result.buy_hold_return_pct;

  return (
    <section className="backtester">
      <h3>Backtest a strategy</h3>
      <p className="bt-intro">
        Replay a rules-based strategy over {symbol}&apos;s recent history and see how it
        would have performed versus simply buying and holding.
      </p>

      <div className="bt-controls">
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          disabled={loading}
          aria-label="Strategy"
        >
          {strategies.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
        <button type="button" onClick={handleRun} disabled={loading}>
          {loading ? "Running…" : "Run backtest"}
        </button>
      </div>

      {current && <p className="bt-desc">{current.description}</p>}

      {error && <p className="error">⚠️ {error}</p>}

      {result && (
        <div className="bt-result">
          <div className="bt-metrics">
            <Metric
              label="Strategy return"
              value={pct(result.total_return_pct)}
              tone={result.total_return_pct >= 0 ? "up" : "down"}
            />
            <Metric
              label="Buy & hold"
              value={pct(result.buy_hold_return_pct)}
              tone={result.buy_hold_return_pct >= 0 ? "up" : "down"}
            />
            <Metric
              label="vs buy & hold"
              value={beatsHold ? "Outperformed" : "Underperformed"}
              tone={beatsHold ? "up" : "down"}
            />
            <Metric label="Trades" value={result.num_trades} />
            <Metric
              label="Win rate"
              value={result.win_rate_pct == null ? "—" : `${result.win_rate_pct}%`}
            />
            <Metric label="Max drawdown" value={pct(result.max_drawdown_pct)} tone="down" />
            <Metric label="Time in market" value={`${result.exposure_pct}%`} />
            <Metric
              label="Final on $10k"
              value={`$${result.final_equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              tone={result.final_equity >= result.initial_cash ? "up" : "down"}
            />
          </div>

          <EquityChart equity={result.equity_curve} benchmark={result.benchmark_curve} />

          <p className="bt-window">
            {result.bars} trading days · {result.start} → {result.end}
          </p>

          <Trades trades={result.trades} />

          <p className="disclaimer">
            Past performance of a backtest does not predict future results — educational only.
          </p>
        </div>
      )}
    </section>
  );
}
