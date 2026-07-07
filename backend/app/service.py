"""Orchestration: fetch (cached) price data -> compute -> tailor -> explain (cached)."""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from . import indicators, tailoring
from .explainers import generate_explanation
from .models import PriceCache, ExplanationCache
from .providers import get_provider, ProviderError
from .schemas import AnalyzeRequest, AnalyzeResponse


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


def analyze(db: Session, req: AnalyzeRequest) -> AnalyzeResponse:
    symbol = req.symbol.upper().strip()

    # 1. Price data — cache first, fetch on miss/stale.
    df = _load_cached_prices(db, symbol)
    if not _prices_are_fresh(df):
        provider = get_provider()
        df = provider.get_daily_ohlcv(symbol, req.days)
        if df.empty:
            raise ProviderError(f"No price data returned for {symbol!r}.")
        _save_prices(db, symbol, df)

    as_of = df.index[-1].strftime("%Y-%m-%d")

    # 2. Compute all indicators, then 3. tailor to the level.
    all_ind = indicators.compute_indicators(df)
    surfaced = tailoring.filter_indicators(all_ind, req.level)

    # 4. Explanation — cached per (symbol, as_of, level).
    cached = (
        db.query(ExplanationCache)
        .filter_by(symbol=symbol, as_of=as_of, level=req.level.value)
        .first()
    )
    if cached:
        explanation, was_cached = cached.explanation, True
    else:
        explanation = generate_explanation(symbol, req.level, surfaced)
        db.add(
            ExplanationCache(
                symbol=symbol, as_of=as_of, level=req.level.value, explanation=explanation
            )
        )
        db.commit()
        was_cached = False

    return AnalyzeResponse(
        symbol=symbol,
        as_of=as_of,
        level=req.level,
        latest_close=float(df["close"].iloc[-1]),
        indicators=surfaced,
        explanation=explanation,
        data_source=get_provider().name,
        cached_explanation=was_cached,
    )
