# Project Brief: Personalized Stock Analysis Web App

## Overview
A personal web app (for two users) that provides stock chart/technical analysis
tailored to each user's investing experience level. The first phase focuses on
**technical/chart analysis**; fundamental/financial-statement analysis is a
planned future phase but out of scope for now.

**Core interaction**: User inputs a stock ticker (or describes preferences) →
app fetches price data → calculates technical indicators → returns analysis,
tailored in depth/tone to the user's stated experience level (beginner,
intermediate, advanced).

## Users & Goals
- Personal project for the developer + one friend
- No hard timeline — prioritize a genuinely useful end product over speed
- Budget: flexible, comfortable using AWS with cost controls/limiters

## Data Sources
- **Primary**: Finnhub free tier — official, supported API (no scraping
  fragility). 60 calls/min free, generous enough for interactive multi-stock
  lookups. Also covers fundamentals (P/E, earnings, insider transactions),
  which sets up the future financial-statement-analysis phase.
- **Fallback / cross-check**: Twelve Data free tier (800 calls/day, 4-hour
  delayed data) — use if Finnhub is unavailable or a second source is needed.
- **Implementation note**: pull raw OHLCV price data from the API and compute
  all technical indicators locally with `pandas-ta`. Avoid provider
  "built-in indicator" endpoints — these typically cost extra API calls per
  indicator, whereas one price-data call + local computation is free and
  fully controllable.
- **Usage pattern**: interactive lookups (one stock at a time, switching
  between tickers), not continuous polling. Daily caching of price data is
  sufficient — no need for minute-by-minute updates since this is for
  technical analysis on daily/weekly charts, not live trading.
- Avoid Alpha Vantage — free tier is now capped at 25 requests/day, too
  restrictive for interactive multi-stock lookups.

## Technical Analysis / Indicators
- **Library**: `pandas-ta` (Python) — 130-150+ indicators, integrates directly
  with pandas DataFrames, includes candlestick pattern detection
- **Indicators to implement (initial set)**:
  - Simple/Exponential Moving Averages (SMA/EMA) — trend direction
  - Support/Resistance levels — visual reversal zones
  - RSI — momentum, overbought/oversold (0-100 scale, easy to explain)
  - MACD — momentum + trend changes via crossovers
  - Bollinger Bands — volatility bands
  - Volume analysis — confirms strength of price moves
  - Candlestick patterns — short-term reversal/continuation signals
  - Fibonacci retracements — potential reversal levels (advanced)
- Compute all indicators once per stock/day (cheap), then filter which ones
  are *shown* based on user experience level (see Personalization Layer below)

## Personalization / Experience-Level Tailoring
Three-tier experience levels: **Beginner / Intermediate / Advanced**

**Architecture**:
1. **Data layer** — fetch OHLCV via yfinance (with Stooq fallback)
2. **Calculation layer** — run pandas-ta to compute all indicators
3. **Tailoring layer** (rules-based) — config/lookup table defining which
   indicators/data are surfaced per experience level:
   - Beginner: SMA, RSI, support/resistance + plain-language summary
   - Intermediate: + MACD, Bollinger Bands, volume analysis
   - Advanced: + candlestick patterns, Fibonacci retracements, raw indicator
     values/numbers
4. **Explanation layer** (LLM-based) — pass computed indicator values +
   experience level to Claude API to generate a plain-language narrative
   explanation. The LLM should **only explain pre-computed numbers**, never
   calculate them itself (avoid hallucinated figures).
   - Cache explanations per stock/day to control API costs

## Tech Stack
- **Backend**: Python (FastAPI preferred, or Flask)
- **Frontend**: React (no charting needed yet — analysis is text/data-based
  for now; charting library decision deferred to a later phase)
- **Database**: Postgres (AWS RDS free tier) or SQLite for low-volume personal
  use — stores cached price data, computed indicators, and cached LLM
  explanations
- **AI**: Claude API for plain-language explanation generation

## Deployment (AWS)
- Single instance approach: AWS Lightsail or EC2 `t4g.micro` (ARM, ~20-40%
  cheaper than x86 equivalents) running both the FastAPI app and the database
- Lightsail free tier: 750 hours/month for first 3 months, then ~$3.50+/month
- Avoid multi-service setups (Elastic Beanstalk, separate RDS, etc.) initially
  — unnecessary complexity for a two-person app
- Set up AWS Billing alerts/budgets from day one to avoid surprise charges

## Out of Scope (For Now)
- Fundamental/financial statement analysis (future phase)
- Interactive charting/visualization (future phase — library decision deferred)
- Real-time/intraday data and minute-by-minute polling (not needed for
  daily-chart technical analysis)
- Multi-user accounts/auth beyond the two intended users

## Open Decisions for Build Phase
- Exact list of indicators to launch with (start with the "initial set" above,
  expand later)
- Specific prompt structure for the LLM explanation layer
- Whether SQLite is sufficient or Postgres/RDS is worth the setup for two users
- Charting library selection (when chart phase begins): leading candidates
  were Highcharts Stock (free for personal use, built-in indicators) and
  Chart.js/react-chartjs-2 (lightweight, performant)
