"""Cache tables: raw price data, computed indicators, and LLM explanations.

Everything is cached per (symbol, date) so a given trading day is fetched/
computed/explained at most once, keeping both API costs and Claude costs low.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, UniqueConstraint

from .database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PriceCache(Base):
    """One row per (symbol, trading day) of raw OHLCV."""
    __tablename__ = "price_cache"
    __table_args__ = (UniqueConstraint("symbol", "date", name="uix_symbol_date"),)

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    fetched_at = Column(DateTime, default=_utcnow)


class FundamentalsCache(Base):
    """One row per (symbol, fetch day) of normalized Finnhub fundamentals.
    Fundamentals move quarterly, so a daily cache means at most one API call
    per symbol per day."""
    __tablename__ = "fundamentals_cache"
    __table_args__ = (UniqueConstraint("symbol", "as_of", name="uix_fund_symbol_asof"),)

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    as_of = Column(String, index=True, nullable=False)  # YYYY-MM-DD fetch day
    payload = Column(Text, nullable=False)  # JSON: normalized metrics
    fetched_at = Column(DateTime, default=_utcnow)


class ExplanationCache(Base):
    """One cached Claude explanation per (symbol, as-of date, experience level)."""
    __tablename__ = "explanation_cache"
    __table_args__ = (
        UniqueConstraint("symbol", "as_of", "level", name="uix_symbol_asof_level"),
    )

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    as_of = Column(String, index=True, nullable=False)  # YYYY-MM-DD of latest bar
    level = Column(String, nullable=False)  # beginner | intermediate | advanced
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
