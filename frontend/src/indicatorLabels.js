// Friendly display labels for the indicator keys returned by the backend.
// Anything not listed falls back to the raw key.
export const LABELS = {
  sma_20: "SMA (20)",
  sma_50: "SMA (50)",
  ema_20: "EMA (20)",
  sma_100: "SMA (100)",
  sma_200: "SMA (200)",
  pct_change_3m: "3-month change %",
  pct_change_1y: "1-year change %",
  high_52w: "52-week high",
  pct_from_52w_high: "Off 52-wk high %",
  rsi_14: "RSI (14)",
  support: "Support",
  resistance: "Resistance",
  macd: "MACD",
  macd_signal: "MACD Signal",
  macd_histogram: "MACD Histogram",
  bb_lower: "Bollinger Lower",
  bb_middle: "Bollinger Mid",
  bb_upper: "Bollinger Upper",
  volume_latest: "Volume (latest)",
  volume_avg_20: "Volume avg (20)",
  volume_at_support: "Vol @ Support",
  volume_at_resistance: "Vol @ Resistance",
  candle_doji: "Doji candle?",
  fib_236: "Fib 23.6%",
  fib_382: "Fib 38.2%",
  fib_500: "Fib 50.0%",
  fib_618: "Fib 61.8%",
  fib_786: "Fib 78.6%",
};

// Static, generic explanations of what each indicator IS — shown on hover so the
// AI narrative doesn't have to define terms every time. Intentionally number-free
// (the value is already displayed next to the label).
export const DESCRIPTIONS = {
  sma_20: "Simple Moving Average of the last 20 closing prices — a short-term trend line. When it sits above the 50-day SMA, the recent trend is generally up.",
  sma_50: "Simple Moving Average of the last 50 closing prices — a medium-term trend line used as a baseline for the broader trend.",
  ema_20: "Exponential Moving Average over 20 days — like the SMA but weights recent prices more, so it reacts faster to new moves.",
  sma_100: "Simple Moving Average of the last 100 closing prices — a slower trend line bridging the medium and long-term picture.",
  sma_200: "Simple Moving Average of the last 200 closing prices — the classic long-term trend line. Price above it is broadly considered a long-term uptrend.",
  pct_change_3m: "How much the price has moved over roughly the last three months of trading.",
  pct_change_1y: "How much the price has moved over roughly the last year of trading.",
  high_52w: "The highest price traded in the last 52 weeks — a widely watched reference level.",
  pct_from_52w_high: "How far the current price sits below its 52-week high. Near zero means the uptrend is intact; deeply negative means a major drawdown.",
  rsi_14: "Relative Strength Index (14-day): momentum on a 0–100 scale. Above 70 is often 'overbought', below 30 'oversold'; 40–60 is neutral.",
  support: "A price level where buying interest has tended to halt declines — a potential floor.",
  resistance: "A price level where selling interest has tended to cap advances — a potential ceiling.",
  macd: "Moving Average Convergence Divergence — the gap between a fast and slow EMA. Tracks trend momentum; rising means strengthening.",
  macd_signal: "A 9-day EMA of the MACD line. MACD crossing above it is a bullish signal; crossing below is bearish.",
  macd_histogram: "The gap between MACD and its signal line. Bars growing above zero = building upward momentum; below zero = downward.",
  bb_lower: "Lower Bollinger Band — two standard deviations below the 20-day average. Price near it can mean the stock is stretched to the downside.",
  bb_middle: "Middle Bollinger Band — the 20-day simple moving average the bands are built around.",
  bb_upper: "Upper Bollinger Band — two standard deviations above the 20-day average. Price near it can mean the stock is stretched to the upside.",
  volume_latest: "Shares traded in the most recent session. Heavy volume adds conviction to a price move.",
  volume_avg_20: "Average daily volume over the last 20 sessions — a baseline for judging whether recent volume is unusually high or low.",
  volume_at_support: "Total volume from recent days that traded within ~1% of the support level. Heavy trading there suggests the level is actively defended and may hold more strongly.",
  volume_at_resistance: "Total volume from recent days that traded within ~1% of the resistance level. Heavy trading there suggests strong selling interest that may cap advances.",
  candle_doji: "A doji candle (open ≈ close) signals indecision and can precede a reversal. 'Yes' means the latest bar is a doji.",
  fib_236: "Fibonacci 23.6% retracement — a shallow potential support/resistance level from the recent swing high-to-low range.",
  fib_382: "Fibonacci 38.2% retracement — a potential support/resistance level from the recent swing range.",
  fib_500: "The 50% retracement of the recent swing range — a commonly watched midpoint level.",
  fib_618: "Fibonacci 61.8% retracement — the 'golden ratio' level, a closely watched potential reversal zone.",
  fib_786: "Fibonacci 78.6% retracement — a deep potential support/resistance level from the recent swing range.",
};

export function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value.toLocaleString();
  return String(value);
}
