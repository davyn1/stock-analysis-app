# Stock Analysis App

Two-user personal web app: ticker in → daily OHLCV fetched → indicators computed
locally with pandas-ta → LLM writes a narrative tailored to experience level
(beginner/intermediate/advanced). Product brief: PROJECT_BRIEF.md. Setup: README.md.

## Running the app

- I run both dev servers myself in my IDE (backend :8000, frontend :5173).
  Never start or restart them — if a port is down, tell me and I'll start it.
- To verify backend logic without servers or keys:
  `backend/.venv/Scripts/python.exe -m scripts.smoke_test` (run from `backend/`).

## Architecture rules

- New price source → implement `PriceProvider` in `backend/app/providers/`,
  register in the factory in `providers/__init__.py`, select via `PRICE_PROVIDER`.
  Same pattern for LLMs: `Explainer` in `backend/app/explainers/`, `EXPLAIN_PROVIDER`.
- The LLM only explains pre-computed numbers — never calculates or invents
  values. Keep this hard rule in every explainer prompt.
  # reason: prevents hallucinated figures, a core product decision
- Indicator *definitions* live in frontend tooltips (`DESCRIPTIONS` in
  `frontend/src/indicatorLabels.js`); LLM prompts must NOT define indicators,
  only interpret. Adding an indicator touches three places: compute in
  `backend/app/indicators.py`, assign a level in `backend/app/tailoring.py`,
  label + tooltip in `indicatorLabels.js`.

## Gotchas

- Explanations are cached per (symbol, day, level). After changing any explainer
  prompt, run `DELETE FROM explanation_cache` on `backend/stock_cache.db`, or
  stale output persists all day.
- Gemini model must be `gemini-2.5-flash` or newer — `gemini-2.0-flash` has a
  free-tier quota of 0. Keep `thinkingBudget: 0` (thinking tokens count against
  maxOutputTokens and truncate the response).
- pandas-ta must stay 0.4.x (0.3.14b0 was pulled from PyPI); it requires numpy ≥ 2.
- If yfinance returns non-JSON/parse errors, upgrade it before debugging anything
  else — stale versions break when Yahoo changes endpoints. On VPN it also needs
  `CURL_CA_BUNDLE` pointed at `backend/win_ca_bundle.pem`.
- `frontend/standalone.html` is a legacy zero-build UI copy — don't maintain it.

## Charting

- Library: TradingView `lightweight-charts` v5 (`chart.addSeries(SeriesType, opts)`
  API — v4 examples online use `addCandlestickSeries()`, which no longer exists).
- Chart data rides on the `/analyze` response (`chart` field): candles + volume +
  overlay lines, tailored per level via `chart_line_keys`/`chart_level_keys` in
  `backend/app/tailoring.py`.

## Product direction (decided 2026-07-19)

This app is the ANALYZER, full stop. End goal: for any ticker, a deterministic
per-horizon verdict — is it favorable to buy/hold short-term, medium-term,
long-term, or not — shown as a verdict card and interpreted by the LLM.
- Verdict logic is deterministic code (`backend/app/verdict.py`); the LLM only
  interprets a verdict it's given, never decides or re-decides one. Same hard
  rule as "LLM never calculates".
- Phase 1 (DONE): technicals-only verdicts. Phase 2 (BUILT 2026-07-19):
  fundamentals via Finnhub feed the LONG horizon only (`app/fundamentals.py`,
  /stock/metric is free tier — candles is the paid one). Activates when
  FINNHUB_API_KEY is set; without it the verdict degrades to technicals-only
  and shows the fundamentals factor as unavailable. Cached one row per
  (symbol, day) in fundamentals_cache. Metric key names are probed via
  candidate lists (_METRIC_KEYS) — verify against a real response when a key
  is first configured.

## Trading (PARKED)

Automated trading (watchlist scanner → paper → live) is on ice. If it returns,
it likely becomes a separately deployed app; the `/trading/*` seam is the
boundary that makes that split mechanical. What stays:
- Signals (`backend/app/signals.py`) and the backtester
  (`backend/app/backtest.py`, `/trading/backtest`, strategy picker + equity
  curve in UI) remain — they serve the analyzer ("how did this strategy compare
  to holding?" is analysis evidence). Backtester panel stays visible in the UI.
- `/trading/*` auth: `app/auth.py` `require_trading_auth` is OPEN when
  `TRADING_TOKEN` is unset (local dev) and ENFORCED (`Bearer` token) once it's
  set. The frontend sends `VITE_TRADING_TOKEN` if defined.
- The LLM never decides trades — any strategy logic is deterministic code.
