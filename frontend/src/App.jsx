import { useState } from "react";
import AnalyzeForm from "./components/AnalyzeForm.jsx";
import ResultCard from "./components/ResultCard.jsx";
import { analyze } from "./api.js";

export default function App() {
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

  return (
    <main className="app">
      <h1>📈 Personalized Stock Analysis</h1>
      <p className="subtitle">
        Enter a ticker and your experience level for a tailored technical read.
      </p>

      <AnalyzeForm
        symbol={symbol}
        setSymbol={setSymbol}
        level={level}
        setLevel={setLevel}
        onSubmit={handleSubmit}
        loading={loading}
      />

      {error && <p className="error">⚠️ {error}</p>}
      {data && <ResultCard data={data} />}
    </main>
  );
}
