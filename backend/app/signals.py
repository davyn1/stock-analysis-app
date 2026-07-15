"""Signal engine: turn indicator *series* into discrete events ("golden cross
on 2026-05-14"), separate from indicators.py which reports latest *values*.

Design:
- A rule is one function returning events for the dates it fired.
- detect_signals() runs every registered rule and returns one time-ordered list.
- Rules are deterministic code — the LLM never decides what counts as a signal.
- Consumers (chart markers, signal list, later the backtester/strategy layer)
  only read the event list; they never compute.

Event shape: {"time", "type", "label", "direction", "price"}
  direction: "bullish" | "bearish"
  time matches the chart's time format (date string daily, Unix seconds intraday).
"""
import pandas as pd
import pandas_ta as ta

from .indicators import format_time


def _cross_above(a: pd.Series, b: pd.Series) -> pd.Series:
    """True on bars where series a closed above series b after being at/below it."""
    return (a.shift(1) <= b.shift(1)) & (a > b)


def _cross_below(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a.shift(1) >= b.shift(1)) & (a < b)


def _events(df, mask, intraday, sig_type, label, direction) -> list[dict]:
    out = []
    for ts in df.index[mask.fillna(False)]:
        out.append(
            {
                "time": format_time(ts, intraday),
                "type": sig_type,
                "label": label,
                "direction": direction,
                "price": round(float(df.loc[ts, "close"]), 4),
            }
        )
    return out


def _sma_cross_rule(df, intraday) -> list[dict]:
    sma20 = ta.sma(df["close"], length=20)
    sma50 = ta.sma(df["close"], length=50)
    if sma20 is None or sma50 is None:
        return []
    return _events(df, _cross_above(sma20, sma50), intraday, "golden_cross",
                   "Golden cross (SMA20 above SMA50)", "bullish") + \
           _events(df, _cross_below(sma20, sma50), intraday, "death_cross",
                   "Death cross (SMA20 below SMA50)", "bearish")


def _rsi_zone_rule(df, intraday) -> list[dict]:
    rsi = ta.rsi(df["close"], length=14)
    if rsi is None:
        return []
    thirty = pd.Series(30.0, index=rsi.index)
    seventy = pd.Series(70.0, index=rsi.index)
    return _events(df, _cross_below(rsi, thirty), intraday, "rsi_oversold",
                   "RSI dropped below 30 (oversold)", "bullish") + \
           _events(df, _cross_above(rsi, seventy), intraday, "rsi_overbought",
                   "RSI rose above 70 (overbought)", "bearish")


def _macd_cross_rule(df, intraday) -> list[dict]:
    macd = ta.macd(df["close"])
    if macd is None or macd.empty:
        return []
    line, sig = macd.iloc[:, 0], macd.iloc[:, 2]
    return _events(df, _cross_above(line, sig), intraday, "macd_bull_cross",
                   "MACD crossed above signal line", "bullish") + \
           _events(df, _cross_below(line, sig), intraday, "macd_bear_cross",
                   "MACD crossed below signal line", "bearish")


# Register new rules here — one line per rule, nothing else changes.
_RULES = [_sma_cross_rule, _rsi_zone_rule, _macd_cross_rule]


def detect_signals(df: pd.DataFrame, intraday: bool = False) -> list[dict]:
    """Run every rule over the frame; return all events oldest-first."""
    events: list[dict] = []
    for rule in _RULES:
        events.extend(rule(df, intraday))
    # Sort by position in the frame (times are strings OR ints depending on
    # timeframe, so sort via the original index order instead of the value).
    order = {format_time(ts, intraday): i for i, ts in enumerate(df.index)}
    events.sort(key=lambda e: order.get(e["time"], -1))
    return events
