import { useState } from "react";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import LandingPage from "./components/LandingPage.jsx";
import ResultCard from "./components/ResultCard.jsx";
import { ChartIcon } from "./components/icons.jsx";
import { analyze } from "./api.js";

function LoadingSkeleton() {
  return (
    <div className="skeleton-card" aria-label="Loading analysis" role="status">
      <div className="skeleton-row w40" />
      <div className="skeleton-block" />
      <div className="skeleton-row w70" />
      <div className="skeleton-row w90" />
      <div className="skeleton-row w60" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <div className="empty-icon"><ChartIcon /></div>
      <p>
        Enter a ticker above and pick your experience level —
        you&apos;ll get the chart, detected signals, key indicators,
        and a plain-language read of what they mean.
      </p>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("landing"); // landing | analyzer
  const [symbol, setSymbol] = useState("AAPL");
  const [level, setLevel] = useState("beginner");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setData(null);
    try {
      setData(await analyze({ symbol, level }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (view === "landing") {
    return <LandingPage onStart={() => setView("analyzer")} />;
  }

  return (
    <main className="app">
      <button className="home-link" onClick={() => setView("landing")}>
        ‹ Home
      </button>

      <header className="app-header">
        <span className="brand-mark"><ChartIcon /></span>
        <div>
          <h1>Stock Analysis</h1>
          <p className="subtitle">
            A tailored technical read, at your experience level.
          </p>
        </div>
      </header>

      <AnalyzeForm
        symbol={symbol}
        setSymbol={setSymbol}
        level={level}
        setLevel={setLevel}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {error && (
        <div className="error-box" role="alert">
          <strong>Couldn&apos;t analyze that.</strong> {error}
        </div>
      )}

      {loading && <LoadingSkeleton />}
      {!loading && !error && !data && <EmptyState />}
      {data && <ResultCard data={data} />}
    </main>
  );
}
