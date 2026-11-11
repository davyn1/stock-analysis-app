# Features and project facts

Facts in this file are taken from the code and the GitHub repository. Paths are
relative to the repository root. Keep it in sync with the code (see CLAUDE.md).

## Summary

A web app that takes a stock ticker, computes technical indicators and a
rule-based rating for three time horizons from daily price data, and has an LLM
explain those results at a beginner, intermediate or advanced level. It also
draws a candlestick chart with detected signals and backtests three trading
strategies against buy-and-hold.

## Tech stack

| Area | Used |
|---|---|
| Languages | Python, JavaScript (JSX) |
| Backend | FastAPI, Uvicorn, Pydantic, pydantic-settings, SQLAlchemy, pandas, numpy, pandas-ta, httpx, truststore |
| Frontend | React 18, Vite 6, TradingView lightweight-charts v5 |
| Database | SQLite (`DATABASE_URL`; the code notes Postgres as an option but none is configured) |
| LLM services | Google Gemini via REST (default `gemini-2.5-flash`); Anthropic Claude via the `anthropic` SDK (optional, `claude-haiku-4-5-20251001`) |
| Market data services | Twelve Data (default), yfinance, Finnhub (price candles, and company metrics for fundamentals) |
| Dev tooling | Playwright (screenshots only; not in `backend/requirements.txt`) |

Versions are pinned in `backend/requirements.txt` and `frontend/package.json`.

## Features

| Feature | What it does | Implemented in |
|---|---|---|
| Analyze endpoint | `POST /analyze`: fetches prices, computes indicators, rating and explanation, returns chart data | `backend/app/main.py`, `backend/app/service.py` (`analyze`) |
| Price providers | Pluggable `PriceProvider`; selected by `PRICE_PROVIDER` (`twelvedata`, `yfinance`, `finnhub`) | `backend/app/providers/` (`base.py`, `twelvedata.py`, `yfinance_provider.py`, `finnhub.py`, factory in `__init__.py`) |
| Indicators | 28 values: SMA 20/50/100/200, EMA 20, RSI 14, MACD (line, signal, histogram), Bollinger Bands (upper, middle, lower), Fibonacci levels (23.6, 38.2, 50, 61.8, 78.6%), support, resistance, volume at support/resistance, latest and 20-day average volume, 52-week high, % from 52-week high, 3-month and 1-year % change, doji candle flag | `backend/app/indicators.py` |
| Level tailoring | Beginner sees 7 indicators, intermediate 22, advanced 28; chart overlays also vary by level | `backend/app/tailoring.py` |
| Signal detection | SMA 20/50 crossovers, RSI dropping below 30 or rising above 70, MACD/signal crossovers; shown as chart markers and a list | `backend/app/signals.py`, `frontend/src/components/SignalList.jsx` |
| Rating ("verdict") | Short (4 factors), medium (4), long (5 technical + 6 fundamental) horizons. Each factor votes +1/0/-1; net ≥ +2 is favorable, ≤ -2 unfavorable, otherwise neutral; fewer than 2 decidable factors is "insufficient" | `backend/app/verdict.py`, `frontend/src/components/VerdictCard.jsx` |
| Fundamentals | Finnhub `/stock/metric` (P/E, EPS growth, revenue growth, net margin, debt/equity, ROE, market cap) feeds the long horizon only. Active only when `FINNHUB_API_KEY` is set | `backend/app/fundamentals.py` |
| LLM explanation | Pluggable `Explainer` selected by `EXPLAIN_PROVIDER` (`gemini`, `claude`). Prompt forbids calculating or changing values; numbers are rounded in code before the prompt; Markdown is stripped from the output | `backend/app/explainers/` (`base.py`, `gemini.py`, `claude.py`, `__init__.py`) |
| Charts | Candlesticks, volume, indicator overlays, support/resistance and Fibonacci lines, signal markers; 8 timeframes (`1m`, `3m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`) via `GET /chart/{symbol}` | `backend/app/service.py` (`chart_for_interval`), `frontend/src/components/StockChart.jsx`, `frontend/src/components/ResultCard.jsx` |
| Backtester | `GET /trading/strategies`, `POST /trading/backtest`. Strategies: `sma_cross`, `macd_cross`, `rsi_reversal`. Reports return, buy-and-hold return, trades, win rate, max drawdown, time in market, equity curve | `backend/app/backtest.py`, `backend/app/trading/__init__.py`, `frontend/src/components/Backtester.jsx`, `frontend/src/components/EquityChart.jsx` |
| Caching | SQLite tables: prices per (symbol, date), fundamentals per (symbol, day), explanations per (symbol, day, level). In-memory 300-second cache for chart payloads and non-daily price data | `backend/app/models.py`, `backend/app/service.py`, `backend/app/fundamentals.py` |
| Indicator tooltips | Definitions of each indicator shown on hover (the LLM does not define them) | `frontend/src/indicatorLabels.js`, `frontend/src/components/IndicatorGrid.jsx` |
| Landing page and UI | Landing page, analyzer form, loading skeleton, error box; light and dark themes follow the OS setting | `frontend/src/App.jsx`, `frontend/src/components/LandingPage.jsx`, `frontend/src/components/AnalyzeForm.jsx`, `frontend/src/styles.css` |
| Health check | `GET /health` returns `{"status": "ok"}` | `backend/app/main.py` |
| README screenshots | Headless Chromium captures 5 views in light and dark | `scripts/take_screenshots.py`, `docs/screenshots/` |

## Testing

- **Count:** 1 test script, `backend/scripts/smoke_test.py`, containing 18 `assert` statements. There are no pytest tests and no frontend tests.
- **Covers:** indicator computation and per-level filtering on synthetic price data; verdict structure, buckets, score bounds and the fundamentals factors; all 3 backtest strategies (curve lengths, final equity, trade counts, drawdown sign, exposure range); prompt rounding and Markdown stripping in the explainer helpers.
- **Not covered:** API endpoints, price providers, LLM calls, the database layer, the frontend.
- **How it runs:** locally only, with no keys or network: `python -m scripts.smoke_test` from `backend/`. It is not run in CI.

## Infrastructure

- **CI/CD:** none. The repository has no `.github/workflows`. The only GitHub Actions activity is GitHub's automatic dependency graph update.
- **Containerization:** none (no Dockerfile or compose file).
- **Hosting:** none. `PROJECT_BRIEF.md` plans an AWS Lightsail or EC2 instance; nothing for it exists in the repository.
- **Deploys:** none. The app runs locally: Uvicorn on port 8000 and the Vite dev server on port 5173, which proxies `/api` to the backend (`frontend/vite.config.js`).

## Reliability and security

| Measure | Details | Path |
|---|---|---|
| Secrets | Keys are read from `backend/.env` by pydantic-settings. `.env`, `*.db` and `win_ca_bundle.pem` are gitignored. `backend/.env.example` holds placeholders only | `backend/app/config.py`, `.gitignore`, `backend/.env.example` |
| Gemini key in URL | The Gemini key is sent as a `key` query parameter, not a header | `backend/app/explainers/gemini.py` |
| Auth | `/trading/*` requires `Authorization: Bearer <TRADING_TOKEN>` when `TRADING_TOKEN` is set; it is open when unset. `/analyze` and `/chart` have no auth | `backend/app/auth.py`, `backend/app/trading/__init__.py` |
| Input validation | Pydantic models: `level` must be one of 3 values; `days` 60–730 for analyze and 120–1825 for backtest; `initial_cash` > 0; unknown strategy or chart interval returns 400. `symbol` is only uppercased and trimmed (no length or format check) | `backend/app/schemas.py`, `backend/app/service.py`, `backend/app/backtest.py` |
| Error handling | Provider failures raise `ProviderError` and return HTTP 502; invalid interval or strategy returns 400; validation errors return 422 (FastAPI default) | `backend/app/main.py`, `backend/app/trading/__init__.py`, `backend/app/providers/base.py` |
| LLM failure fallback | A missing key or failed LLM call returns the raw indicator values instead of an error. The fallback text is cached like a normal explanation for that day | `backend/app/explainers/base.py` (`raw_fallback`), `backend/app/service.py` |
| Fundamentals failure | Any error returns `None` and the rating continues on technicals only | `backend/app/fundamentals.py` |
| CORS | Allowed origins: `http://localhost:5173`, `http://localhost:3000`, `http://127.0.0.1:5500` | `backend/app/main.py` |
| TLS behind proxies | `truststore` makes HTTP clients use the OS certificate store | `backend/app/main.py` |
| Rate limiting | None | — |

## Numbers from the code

| Item | Value | Path |
|---|---|---|
| Indicators computed | 28 | `backend/app/indicators.py` |
| Indicators shown per level | 7 / 22 / 28 | `backend/app/tailoring.py` |
| LLM calls per ticker per trading day, at most | 3 (one per level; unique key on symbol, day, level) | `backend/app/models.py` |
| Price history kept for the rating | 730 days | `backend/app/service.py` (`VERDICT_HISTORY_DAYS`) |
| Daily price cache considered fresh | latest bar ≤ 4 days old | `backend/app/service.py` (`_prices_are_fresh`) |
| In-memory chart cache | 300 seconds | `backend/app/service.py` (`_INTERVAL_TTL_SECONDS`) |
| Gemini request timeout / max output tokens | 30 s / 1200 | `backend/app/explainers/gemini.py` |
| Claude max output tokens | 900 (no explicit timeout set) | `backend/app/explainers/claude.py` |
| Twelve Data, Finnhub candle and Finnhub metric timeouts | 20 s each | `backend/app/providers/twelvedata.py`, `backend/app/providers/finnhub.py`, `backend/app/fundamentals.py` |
| yfinance timeout | none set | `backend/app/providers/yfinance_provider.py` |
| Frontend request timeouts | 60 s for analyze and backtest, 30 s otherwise | `frontend/src/api.js` |
| Analyze lookback (`days`) | 60–730, default 180 | `backend/app/schemas.py` |
| Backtest window (`days`) | 120–1825, default 730; default starting cash 10,000 | `backend/app/schemas.py` |
| Rating thresholds | net score ≥ +2 favorable, ≤ -2 unfavorable | `backend/app/verdict.py` |
| RSI zones | 70 overbought, 30 oversold | `backend/app/verdict.py`, `backend/app/signals.py` |
| Smoke test assertions | 18 | `backend/scripts/smoke_test.py` |

## Status

- **Deployed:** no. No live URL.
- **Repository:** public on GitHub (`davyn1/stock-analysis-app`), default branch `master`.
- **Collaborators:** 1 (`davyn1`).
- **Last code change:** 2026-10-23. **This file last updated:** 2026-11-11.
