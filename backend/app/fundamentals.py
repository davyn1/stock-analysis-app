"""Fundamentals layer (verdict phase 2): fetch key company metrics from Finnhub
and normalize them for the verdict engine's long-term horizon.

Design:
- Finnhub's /stock/metric (Basic Financials) is on the FREE tier — unlike the
  candle endpoint that pushed price fetching to yfinance. Uses FINNHUB_API_KEY.
- Everything degrades gracefully: no key, network failure, unknown ticker, or a
  missing metric all yield None values — the verdict shows those factors as
  "unavailable" and its basis stays technicals-only. /analyze NEVER fails
  because fundamentals couldn't be fetched.
- Cached one row per (symbol, day) in SQLite, same philosophy as prices:
  fundamentals move quarterly, so daily is generous.
- Finnhub's metric key names vary by field vintage, so each concept probes a
  list of candidate keys and takes the first usable number.
"""
import json
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from .config import settings
from .models import FundamentalsCache

BASE_URL = "https://finnhub.io/api/v1"

# concept -> candidate keys in Finnhub's `metric` dict, first hit wins.
_METRIC_KEYS = {
    "pe_ttm": ["peTTM", "peBasicExclExtraTTM", "peNormalizedAnnual"],
    "eps_growth_yoy": ["epsGrowthTTMYoy", "epsGrowthQuarterlyYoy", "epsGrowth5Y"],
    "revenue_growth_yoy": ["revenueGrowthTTMYoy", "revenueGrowthQuarterlyYoy", "revenueGrowth5Y"],
    "net_margin": ["netProfitMarginTTM", "netProfitMarginAnnual", "netProfitMargin5Y"],
    "debt_to_equity": ["totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"],
    "roe": ["roeTTM", "roeRfy", "roe5Y"],
    "market_cap": ["marketCapitalization"],
}


def _num(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return round(f, 4)


def _normalize(metric: dict) -> dict:
    out = {}
    for concept, candidates in _METRIC_KEYS.items():
        val = None
        for key in candidates:
            val = _num(metric.get(key))
            if val is not None:
                break
        out[concept] = val
    return out


def _fetch_from_finnhub(symbol: str) -> dict | None:
    resp = httpx.get(
        f"{BASE_URL}/stock/metric",
        params={"symbol": symbol, "metric": "all", "token": settings.finnhub_api_key},
        timeout=20.0,
    )
    if resp.status_code != 200:
        return None
    metric = resp.json().get("metric") or {}
    if not metric:
        return None
    return _normalize(metric)


def get_fundamentals(db: Session, symbol: str) -> dict | None:
    """Normalized fundamentals for `symbol`, or None when unavailable.

    Cache-first (one row per symbol per day); any failure returns None so the
    caller can proceed technicals-only.
    """
    if not settings.finnhub_api_key.strip():
        return None

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = db.query(FundamentalsCache).filter_by(symbol=symbol, as_of=today).first()
    if row:
        return json.loads(row.payload)

    try:
        data = _fetch_from_finnhub(symbol)
    except Exception:
        return None
    if data is None:
        return None

    db.add(FundamentalsCache(symbol=symbol, as_of=today, payload=json.dumps(data)))
    db.commit()
    return data
