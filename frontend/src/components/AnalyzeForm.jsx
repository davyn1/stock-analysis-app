const LEVELS = ["beginner", "intermediate", "advanced"];

export default function AnalyzeForm({ symbol, setSymbol, level, setLevel, onSubmit, loading }) {
  return (
    <form className="analyze-form" onSubmit={onSubmit}>
      <label>
        Ticker
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="AAPL"
          autoFocus
        />
      </label>

      <label>
        Experience
        <select value={level} onChange={(e) => setLevel(e.target.value)}>
          {LEVELS.map((l) => (
            <option key={l} value={l}>
              {l[0].toUpperCase() + l.slice(1)}
            </option>
          ))}
        </select>
      </label>

      <button type="submit" disabled={loading || !symbol.trim()}>
        {loading ? "Analyzing…" : "Analyze"}
      </button>
    </form>
  );
}
