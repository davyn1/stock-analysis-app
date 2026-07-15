import { useEffect, useState } from "react";
import IndicatorGrid from "./IndicatorGrid.jsx";
import SignalList from "./SignalList.jsx";
import StockChart from "./StockChart.jsx";
import { fetchChart } from "../api.js";

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h", "4h", "1d", "1w"];

function PriceChange({ candles }) {
  // Day-over-day change from the daily payload's last two complete bars.
  if (!candles || candles.length < 2) return null;
  const last = candles[candles.length - 1].close;
  const prev = candles[candles.length - 2].close;
  const delta = last - prev;
  const pct = (delta / prev) * 100;
  const up = delta >= 0;
  return (
    <span className={`price-change ${up ? "up" : "down"}`}>
      {up ? "+" : "−"}${Math.abs(delta).toFixed(2)} ({up ? "+" : "−"}
      {Math.abs(pct).toFixed(2)}%)
    </span>
  );
}

export default function ResultCard({ data }) {
  const [tf, setTf] = useState("1d");
  const [chartData, setChartData] = useState(data.chart);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState(null);

  // New analysis (symbol/level change) -> reset to the daily chart it shipped with.
  useEffect(() => {
    setTf("1d");
    setChartData(data.chart);
    setChartError(null);
  }, [data]);

  async function pickTimeframe(next) {
    setTf(next);
    setChartError(null);
    if (next === "1d") {
      setChartData(data.chart); // already in the analyze response, no fetch
      return;
    }
    setChartLoading(true);
    try {
      setChartData(await fetchChart(data.symbol, next, data.level));
    } catch (err) {
      setChartError(err.message);
      setChartData(null);
    } finally {
      setChartLoading(false);
    }
  }

  return (
    <section className="result-card">
      <header className="result-header">
        <h2>
          {data.symbol} <span className="price">${data.latest_close.toLocaleString()}</span>
          <PriceChange candles={data.chart?.candles} />
        </h2>
        <p className="meta">
          as of {data.as_of} · {data.level} · source: {data.data_source}
          {data.cached_explanation ? " · cached" : ""}
        </p>
      </header>

      <div className="timeframes" role="tablist" aria-label="Chart timeframe">
        {TIMEFRAMES.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tf === t}
            className={`tf-btn${tf === t ? " active" : ""}`}
            onClick={() => pickTimeframe(t)}
            disabled={chartLoading}
          >
            {t.toUpperCase()}
          </button>
        ))}
        {chartLoading && <span className="tf-status">loading…</span>}
      </div>

      {chartError && <p className="error">⚠️ {chartError}</p>}
      <StockChart chart={chartData} />
      <SignalList signals={chartData?.signals} />

      <IndicatorGrid indicators={data.indicators} />

      <h3>Explanation</h3>
      <p className="explanation">{data.explanation}</p>

      <p className="disclaimer">Educational analysis only — not financial advice.</p>
    </section>
  );
}
