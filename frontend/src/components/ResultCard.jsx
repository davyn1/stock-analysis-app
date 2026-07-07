import IndicatorGrid from "./IndicatorGrid.jsx";

export default function ResultCard({ data }) {
  return (
    <section className="result-card">
      <header className="result-header">
        <h2>
          {data.symbol} <span className="price">${data.latest_close.toLocaleString()}</span>
        </h2>
        <p className="meta">
          as of {data.as_of} · {data.level} · source: {data.data_source}
          {data.cached_explanation ? " · cached" : ""}
        </p>
      </header>

      <IndicatorGrid indicators={data.indicators} />

      <h3>Explanation</h3>
      <p className="explanation">{data.explanation}</p>

      <p className="disclaimer">Educational analysis only — not financial advice.</p>
    </section>
  );
}
