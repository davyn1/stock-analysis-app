import { ChartIcon, SignalIcon, ExplainIcon } from "./icons.jsx";

const FEATURES = [
  {
    icon: <ChartIcon />,
    title: "Real charts, every timeframe",
    text: "Candlesticks with volume, moving averages, Bollinger Bands and Fibonacci levels — from 1-minute bars to weekly.",
  },
  {
    icon: <SignalIcon />,
    title: "Signals, not noise",
    text: "Golden crosses, RSI zones and MACD crossovers detected automatically and marked right on the chart.",
  },
  {
    icon: <ExplainIcon />,
    title: "Explained at your level",
    text: "AI narratives tailored to beginner, intermediate or advanced — interpreting the numbers, never inventing them.",
  },
];

export default function LandingPage({ onStart }) {
  return (
    <div className="landing">
      <section className="landing-hero">
        <h1>
          Technical analysis,
          <br />
          <span className="landing-accent">explained for humans.</span>
        </h1>
        <p className="landing-sub">
          Enter a ticker. Get real indicators computed from real price data —
          and a plain-language read of what they mean, tuned to how much
          investing experience you have.
        </p>
        <button className="landing-cta" onClick={onStart}>
          Open the analyzer
        </button>
      </section>

      <section className="landing-features" aria-label="Features">
        {FEATURES.map((f) => (
          <div className="feature" key={f.title}>
            <div className="feature-icon">{f.icon}</div>
            <h2>{f.title}</h2>
            <p>{f.text}</p>
          </div>
        ))}
      </section>

      <footer className="landing-footer">
        Educational analysis only — not financial advice.
      </footer>
    </div>
  );
}
