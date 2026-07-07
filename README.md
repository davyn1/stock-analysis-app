# Personalized Stock Analysis

A small two-user web app: enter a ticker → fetch daily price data → compute
technical indicators locally → Claude explains them in plain language, tailored
to your experience level (beginner / intermediate / advanced).

See [PROJECT_BRIEF.md](PROJECT_BRIEF.md) for the full project brief.

## Architecture

```
ticker ─► provider (Finnhub) ─► price cache (SQLite)
                                     │
                                     ▼
                          pandas-ta indicators  ─► tailoring (per level)
                                     │
                                     ▼
                          Claude explanation (cached per symbol/day/level)
```

Layers map directly to files in `backend/app/`:

| Layer          | File                       |
|----------------|----------------------------|
| Data provider  | `providers/finnhub.py` (interface in `providers/base.py`) |
| Caching/DB     | `models.py`, `database.py` |
| Indicators     | `indicators.py`            |
| Tailoring      | `tailoring.py`             |
| Explanation    | `explain.py`               |
| Orchestration  | `service.py`               |
| API            | `main.py`                  |

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit .env with your keys
```

> **pandas-ta version:** the old `0.3.14b0` was pulled from PyPI. We use the
> maintained `0.4.x` rewrite, which requires **numpy ≥ 2** (and fixes the old
> `from numpy import NaN` bug), so numpy/pandas are left unpinned for pip to resolve.

## Verify it works (no keys needed)

```powershell
cd backend
python -m scripts.smoke_test
```

This runs the compute + tailoring layers on synthetic data — confirms pandas-ta
imports cleanly and indicators flow through to each experience level.

## Behind a corporate / TLS-inspecting proxy?

If `pip`/requests fail with `CERTIFICATE_VERIFY_FAILED: unable to get local
issuer certificate`, your machine has a TLS-inspecting proxy (corporate AV/VPN).
This only affects local dev — your AWS deployment won't have it.

- **pip**: add `--trusted-host pypi.org --trusted-host files.pythonhosted.org`.
- **Twelve Data / Finnhub / Claude**: handled automatically — the app calls
  `truststore.inject_into_ssl()` at startup, which trusts the proxy's root cert
  via the OS store. Nothing to do.
- **yfinance only** (uses `curl_cffi`, which bypasses Python's trust store):
  export the Windows cert store to a PEM and point curl at it:
  ```powershell
  # from backend/ (one time, regenerate if certs change)
  .venv\Scripts\python.exe -c "import ssl,certifi,pathlib; p=pathlib.Path('win_ca_bundle.pem'); p.write_text(pathlib.Path(certifi.where()).read_text()+'\n'+'\n'.join(ssl.DER_cert_to_PEM_cert(c[0]) for s in ('ROOT','CA') for c in ssl.enum_certificates(s)))"
  $env:CURL_CA_BUNDLE = "$PWD\win_ca_bundle.pem"   # before running uvicorn
  ```

## Run

Two terminals:

```powershell
# 1) backend (from backend/, venv activated)
#    on a corporate-proxy machine, set CURL_CA_BUNDLE first (see section above)
uvicorn app.main:app --reload
# -> http://localhost:8000/docs  for the interactive API

# 2) frontend (from frontend/)
npm install        # first time only
npm run dev
# -> http://localhost:5173   (Vite proxies /api -> backend, no CORS setup needed)
```

Then open **http://localhost:5173**, enter a ticker, pick an experience level.

The frontend is a Vite + React app (`frontend/src/`). A zero-build single-file
version is kept at `frontend/standalone.html` as a fallback — just open it in a
browser (it calls `http://localhost:8000` directly).

You can also hit the API directly:

```json
POST /analyze   { "symbol": "AAPL", "level": "beginner" }
```

## Data providers

Selected via `PRICE_PROVIDER` in `.env`. All implement the same `PriceProvider`
interface (`app/providers/base.py`), so switching is just an env change.

| `PRICE_PROVIDER` | Key needed? | Notes |
|------------------|-------------|-------|
| `twelvedata` (default) | free key | Official API, **works on AWS**. 800 calls/day free. |
| `yfinance`       | none        | Zero setup, great for local testing. ⚠️ scrapes Yahoo — may be **blocked on AWS/datacenter IPs**. |
| `finnhub`        | free key    | Free tier **lacks US historical candles** (returns 403). Kept for fundamentals later. |

- **Twelve Data**: https://twelvedata.com/ → `TWELVE_DATA_API_KEY`
- **yfinance**: no key — just set `PRICE_PROVIDER=yfinance`
- **Finnhub**: https://finnhub.io/ → `FINNHUB_API_KEY`

## Keys

- **Claude** (explanations): https://console.anthropic.com/ → `ANTHROPIC_API_KEY`
  - Without it, the pipeline still runs and returns the raw indicator dump
    instead of a narrative, so you can develop offline.

## Cost controls

- Price data cached per symbol/day; explanations cached per symbol/day/level —
  each trading day costs at most one data call + one Claude call per level.
- Default Claude model is Haiku (cheap). Change `ANTHROPIC_MODEL` in `.env`.

## Not yet in scope

Charts, fundamentals, auth, intraday data — see the brief's "Out of Scope".
```
