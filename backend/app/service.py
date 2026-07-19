"""Orchestration: fetch (cached) price data -> compute -> tailor -> explain (cached)."""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from . import backtest, indicators, signals, tailoring, verdict as verdict_engine
from .explainers import generate_explanation
from .models import PriceCache, ExplanationCache
from .providers import get_provider, ProviderError
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BacktestRequest,
    BacktestResult,
    ChartData,
)


def _build_chart(df: pd.DataFrame, all_ind: dict, level, intraday: bool = False) -> ChartData:
    """Shape price data + overlays for lightweight-charts, tailored to the level."""
    dates = [indicators.format_time(ts, intraday) for ts in df.index]
    candles = [
        {"time": d, "open": round(float(o), 4), "high": round(float(h), 4),
         "low": round(float(lo), 4), "close": round(float(c), 4)}
        for d, o, h, lo, c in zip(dates, df["open"], df["high"], df["low"], df["close"])
    ]
    volume = [
        # Color volume bars by whether the day closed up or down.
        {"time": d, "value": int(v), "color": "#2e8b5766" if c >= o else "#c0392b66"}
        for d, v, o, c in zip(dates, df["volume"], df["open"], df["close"])
    ]
    all_series = indicators.compute_series(df, intraday)
    lines = {k: all_series[k] for k in tailoring.chart_line_keys(level) if k in all_series}
    levels = {
        k: all_ind[k]
        for k in tailoring.chart_level_keys(level)
        if all_ind.get(k) is not None
    }
    return ChartData(
        candles=candles,
        volume=volume,
        lines=lines,
        levels=levels,
        signals=signals.detect_signals(df, intraday),
    )


def _load_cached_prices(db: Session, symbol: str) -> pd.DataFrame | None:
    rows = (
        db.query(PriceCache)
        .filter(PriceCache.symbol == symbol)
        .order_by(PriceCache.date)
        .all()
    )
    if not rows:
        return None
    df = pd.DataFrame(
        {
            "open": [r.open for r in rows],
            "high": [r.high for r in rows],
            "low": [r.low for r in rows],
            "close": [r.close for r in rows],
            "volume": [r.volume for r in rows],
        },
        index=pd.to_datetime([r.date for r in rows], utc=True),
    )
    df.index.name = "date"
    return df


def _save_prices(db: Session, symbol: str, df: pd.DataFrame) -> None:
    """Upsert-ish: only insert dates we don't already have for this symbol."""
    existing = {
        r.date for r in db.query(PriceCache.date).filter(PriceCache.symbol == symbol).all()
    }
    for ts, row in df.iterrows():
        date_str = ts.strftime("%Y-%m-%d")
        if date_str in existing:
            continue
        db.add(
            PriceCache(
                symbol=symbol, date=date_str,
                open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    db.commit()


def _prices_are_fresh(df: pd.DataFrame) -> bool:
    """Daily caching is enough: fresh if the latest bar is within the last calendar day
    that the market could have closed. We accept anything from the last 4 days to cover
    weekends/holidays without forcing a refetch on every request."""
    if df is None or df.empty:
        return False
    latest = df.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - latest).days
    return age_days <= 4


VALID_INTERVALS = ("1m", "3m", "5m", "15m", "1h", "4h", "1d", "1w")

# Intraday bars go stale in minutes, so they get small in-memory TTL caches
# instead of the SQLite daily cache. Two layers: raw frames (shared across
# levels) and built payloads (skip recompute on repeat clicks). Fine for a
# 2-user single-process app.
_INTERVAL_TTL_SECONDS = 300
_interval_cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
_payload_cache: dict[tuple[str, str, str], tuple[float, ChartData]] = {}


def chart_for_interval(db: Session, symbol: str, interval: str, level) -> ChartData:
    """Chart payload for any timeframe. Daily reuses the SQLite cache; other
    intervals fetch on demand (with a short in-memory cache)."""
    import time

    symbol = symbol.upper().strip()
    interval = interval.lower()
    if interval not in VALID_INTERVALS:
        raise ValueError(f"interval must be one of {', '.join(VALID_INTERVALS)}")

    pkey = (symbol, interval, level.value)
    hit = _payload_cache.get(pkey)
    if hit and time.time() - hit[0] < _INTERVAL_TTL_SECONDS:
        return hit[1]

    if interval == "1d":
        df = _load_cached_prices(db, symbol)
        if not _prices_are_fresh(df):
            df = get_provider().get_daily_ohlcv(symbol, 180)
            _save_prices(db, symbol, df)
    else:
        key = (symbol, interval)
        hit = _interval_cache.get(key)
        if hit and time.time() - hit[0] < _INTERVAL_TTL_SECONDS:
            df = hit[1]
        else:
            df = get_provider().get_ohlcv(symbol, interval)
            _interval_cache[key] = (time.time(), df)

    all_ind = indicators.compute_indicators(df)
    payload = _build_chart(df, all_ind, level, intraday=interval not in ("1d", "1w"))
    _payload_cache[pkey] = (time.time(), payload)
    return payload


# The verdict's long horizon needs ~2 years of daily bars (SMA200 + 1y change),
# regardless of how much the chart shows.
VERDICT_HISTORY_DAYS = 730


def analyze(db: Session, req: AnalyzeRequest) -> AnalyzeResponse:
    symbol = req.symbol.upper().strip()

    # 1. Price data — always ensure the long verdict window (cache-backed; on a
    # warm cache this fetches nothing). The chart still shows only req.days.
    df_full = _ensure_history(db, symbol, VERDICT_HISTORY_DAYS)
    if df_full is None or df_full.empty:
        raise ProviderError(f"No price data returned for {symbol!r}.")

    as_of = df_full.index[-1].strftime("%Y-%m-%d")

    # 2. Compute indicators on the full frame (rolling windows only use the most
    # recent bars, so values match the old shorter frame — but SMA200/1y-change
    # now have the history they need). Then tailor to the level.
    all_ind = indicators.compute_indicators(df_full)
    surfaced = tailoring.filter_indicators(all_ind, req.level)

    # 3. Verdict — deterministic, decided in code before the LLM sees anything.
    events_full = signals.detect_signals(df_full)
    the_verdict = verdict_engine.compute_verdict(df_full, all_ind, events_full)

    # 4. Explanation — cached per (symbol, as_of, level); interprets the verdict.
    cached = (
        db.query(ExplanationCache)
        .filter_by(symbol=symbol, as_of=as_of, level=req.level.value)
        .first()
    )
    if cached:
        explanation, was_cached = cached.explanation, True
    else:
        explanation = generate_explanation(symbol, req.level, surfaced, the_verdict)
        db.add(
            ExplanationCache(
                symbol=symbol, as_of=as_of, level=req.level.value, explanation=explanation
            )
        )
        db.commit()
        was_cached = False

    # Chart keeps the requested window so the default view stays readable.
    cutoff = df_full.index[-1] - pd.Timedelta(days=req.days)
    df_view = df_full[df_full.index >= cutoff]

    return AnalyzeResponse(
        symbol=symbol,
        as_of=as_of,
        level=req.level,
        latest_close=float(df_full["close"].iloc[-1]),
        indicators=surfaced,
        verdict=the_verdict,
        explanation=explanation,
        data_source=get_provider().name,
        cached_explanation=was_cached,
        chart=_build_chart(df_view, all_ind, req.level),
    )


def _ensure_history(db: Session, symbol: str, days: int) -> pd.DataFrame | None:
    """Like the analyze price step, but a backtest needs a long window, so also
    refetch when the cache is fresh but doesn't span far enough back. _save_prices
    only inserts missing dates, so a wider fetch backfills older bars in place."""
    df = _load_cached_prices(db, symbol)
    fresh = _prices_are_fresh(df)
    span_ok = (
        df is not None
        and not df.empty
        and (df.index[-1] - df.index[0]).days >= days * 0.8
    )
    if not (fresh and span_ok):
        fetched = get_provider().get_daily_ohlcv(symbol, days)
        if not fetched.empty:
            _save_prices(db, symbol, fetched)
        df = _load_cached_prices(db, symbol)
    return df


def run_backtest(db: Session, req: BacktestRequest) -> BacktestResult:
    symbol = req.symbol.upper().strip()
    df = _ensure_history(db, symbol, req.days)
    if df is None or df.empty:
        raise ProviderError(f"No price data returned for {symbol!r}.")

    result = backtest.run_backtest(df, req.strategy, initial_cash=req.initial_cash)
    result["symbol"] = symbol
    return BacktestResult(**result)
