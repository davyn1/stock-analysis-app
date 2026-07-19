"""Backtester: replay a deterministic strategy over historical daily bars and
report how it would have performed.

Design (mirrors signals.py / indicators.py — plain functions, plain dicts):
- A strategy maps signal *types* (from signals.detect_signals) to actions:
  enter long on any of its entry types, exit on any of its exit types.
- Strategy logic is deterministic code. The LLM never decides trades — this
  extends the project's "LLM never calculates" rule to "LLM never trades".
- Long-only, all-in / all-out (a personal-app MVP): when flat and an entry
  signal fires we buy with the full account at that bar's close; when long and
  an exit signal fires we sell the whole position at that bar's close. Signals
  are computed from the close, so filling at the same close is the earliest
  honest fill (no peeking at future bars).
- Output is a plain dict shaped for schemas.BacktestResult: headline metrics, a
  per-trade list, and two equity curves (strategy vs buy-and-hold) for charting.
"""
from collections import defaultdict

import pandas as pd

from . import signals
from .indicators import format_time


# A strategy is entry/exit signal types plus display copy. Add one here to
# expose a new strategy everywhere (engine, API, UI dropdown) — nothing else
# changes. `entry`/`exit` values must be `type`s emitted by signals.detect_signals.
STRATEGIES: dict[str, dict] = {
    "sma_cross": {
        "label": "SMA 20/50 crossover",
        "description": "Buy on a golden cross (SMA20 crosses above SMA50); "
        "sell on a death cross (SMA20 crosses below SMA50).",
        "entry": ["golden_cross"],
        "exit": ["death_cross"],
    },
    "macd_cross": {
        "label": "MACD signal crossover",
        "description": "Buy when the MACD line crosses above its signal line; "
        "sell when it crosses back below.",
        "entry": ["macd_bull_cross"],
        "exit": ["macd_bear_cross"],
    },
    "rsi_reversal": {
        "label": "RSI oversold / overbought",
        "description": "Buy when RSI(14) drops below 30 (oversold); "
        "sell when it rises above 70 (overbought).",
        "entry": ["rsi_oversold"],
        "exit": ["rsi_overbought"],
    },
}


def list_strategies() -> list[dict]:
    """Metadata for the UI strategy picker (no entry/exit internals)."""
    return [
        {"key": k, "label": s["label"], "description": s["description"]}
        for k, s in STRATEGIES.items()
    ]


def _max_drawdown_pct(equity: list[float]) -> float:
    """Largest peak-to-trough drop of the equity curve, as a negative percent
    (0.0 if it only ever went up)."""
    peak = float("-inf")
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, (v - peak) / peak * 100.0)
    return round(worst, 2)


def _stat(values: list[float], fn) -> float | None:
    return round(fn(values), 2) if values else None


def run_backtest(
    df: pd.DataFrame,
    strategy_key: str,
    initial_cash: float = 10_000.0,
    commission_pct: float = 0.0,
) -> dict:
    """Simulate `strategy_key` over daily frame `df`; return a result dict.

    `commission_pct` is charged on both sides of every trade (default 0). The
    returned dict omits `symbol` — the service layer stamps that on.
    """
    if strategy_key not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy {strategy_key!r}. "
            f"Choose one of: {', '.join(STRATEGIES)}."
        )
    if df is None or df.empty:
        raise ValueError("No price data to backtest.")

    strat = STRATEGIES[strategy_key]
    entry_types = set(strat["entry"])
    exit_types = set(strat["exit"])
    fee = commission_pct / 100.0

    # Bucket signal events by their (daily) time key so we can look them up per bar.
    events_by_time: dict[str, list[dict]] = defaultdict(list)
    for e in signals.detect_signals(df, intraday=False):
        events_by_time[e["time"]].append(e)

    closes = df["close"].astype(float).tolist()
    times = [format_time(ts, False) for ts in df.index]

    cash = float(initial_cash)
    shares = 0.0
    entry: dict | None = None          # open position: {time, price, cost, i}
    trades: list[dict] = []
    strategy_curve: list[dict] = []
    bars_in_market = 0

    for i, (tkey, close) in enumerate(zip(times, closes)):
        for e in events_by_time.get(tkey, []):
            if entry is None and e["type"] in entry_types:
                buy_price = close * (1 + fee)
                shares = cash / buy_price
                entry = {"time": tkey, "price": close, "cost": cash, "i": i}
                cash = 0.0
            elif entry is not None and e["type"] in exit_types:
                proceeds = shares * close * (1 - fee)
                trades.append(
                    {
                        "entry_time": entry["time"],
                        "entry_price": round(entry["price"], 4),
                        "exit_time": tkey,
                        "exit_price": round(close, 4),
                        "return_pct": round((proceeds / entry["cost"] - 1) * 100, 2),
                        "bars_held": i - entry["i"],
                        "open": False,
                    }
                )
                cash = proceeds
                shares = 0.0
                entry = None

        if entry is not None:
            bars_in_market += 1
        strategy_curve.append({"time": tkey, "value": round(cash + shares * close, 2)})

    # A position still open at the last bar is marked-to-market for equity, and
    # reported as an open (unrealized) trade — but excluded from win/return stats.
    if entry is not None:
        last_close = closes[-1]
        proceeds = shares * last_close * (1 - fee)
        trades.append(
            {
                "entry_time": entry["time"],
                "entry_price": round(entry["price"], 4),
                "exit_time": None,
                "exit_price": round(last_close, 4),
                "return_pct": round((proceeds / entry["cost"] - 1) * 100, 2),
                "bars_held": (len(closes) - 1) - entry["i"],
                "open": True,
            }
        )

    # Buy-and-hold benchmark: buy the full account on the first bar, hold to the end.
    first_close = closes[0]
    bh_shares = initial_cash / first_close
    benchmark_curve = [
        {"time": t, "value": round(bh_shares * c, 2)} for t, c in zip(times, closes)
    ]

    final_equity = strategy_curve[-1]["value"]
    closed = [t for t in trades if not t["open"]]
    returns = [t["return_pct"] for t in closed]
    wins = [r for r in returns if r > 0]

    return {
        "strategy": strategy_key,
        "strategy_label": strat["label"],
        "strategy_description": strat["description"],
        "start": times[0],
        "end": times[-1],
        "bars": len(df),
        "initial_cash": round(float(initial_cash), 2),
        "final_equity": final_equity,
        "total_return_pct": round((final_equity / initial_cash - 1) * 100, 2),
        "buy_hold_return_pct": round((closes[-1] / first_close - 1) * 100, 2),
        "num_trades": len(closed),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else None,
        "avg_trade_pct": _stat(returns, lambda v: sum(v) / len(v)),
        "best_trade_pct": _stat(returns, max),
        "worst_trade_pct": _stat(returns, min),
        "max_drawdown_pct": _max_drawdown_pct([p["value"] for p in strategy_curve]),
        "exposure_pct": round(bars_in_market / len(df) * 100, 1),
        "trades": trades,
        "equity_curve": strategy_curve,
        "benchmark_curve": benchmark_curve,
    }
