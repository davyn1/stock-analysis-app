"""Pydantic request/response models for the API."""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExperienceLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])
    level: ExperienceLevel = ExperienceLevel.beginner
    days: int = Field(180, ge=60, le=730, description="Lookback window in calendar days")


class ChartData(BaseModel):
    candles: list[dict[str, Any]]        # [{time, open, high, low, close}]
    volume: list[dict[str, Any]]         # [{time, value}]
    lines: dict[str, list[dict[str, Any]]]  # overlay line series per indicator key
    levels: dict[str, float]             # horizontal price lines (support, fibs, ...)
    signals: list[dict[str, Any]]        # [{time, type, label, direction, price}]


class AnalyzeResponse(BaseModel):
    symbol: str
    as_of: str
    level: ExperienceLevel
    latest_close: float
    indicators: dict[str, Any]   # only the indicators surfaced for this level
    verdict: dict[str, Any]      # deterministic per-horizon verdict (verdict.py)
    explanation: str
    data_source: str
    cached_explanation: bool
    chart: ChartData


# --- Trading: backtester ----------------------------------------------------

class BacktestRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])
    strategy: str = Field("sma_cross", description="Strategy key from backtest.STRATEGIES")
    days: int = Field(730, ge=120, le=1825, description="History window to backtest over")
    initial_cash: float = Field(10_000, gt=0)


class BacktestResult(BaseModel):
    symbol: str
    strategy: str
    strategy_label: str
    strategy_description: str
    start: str
    end: str
    bars: int
    initial_cash: float
    final_equity: float
    total_return_pct: float
    buy_hold_return_pct: float
    num_trades: int
    win_rate_pct: float | None
    avg_trade_pct: float | None
    best_trade_pct: float | None
    worst_trade_pct: float | None
    max_drawdown_pct: float
    exposure_pct: float
    trades: list[dict[str, Any]]          # [{entry_time, entry_price, exit_time, exit_price, return_pct, bars_held, open}]
    equity_curve: list[dict[str, Any]]    # [{time, value}] — strategy account value
    benchmark_curve: list[dict[str, Any]]  # [{time, value}] — buy-and-hold
