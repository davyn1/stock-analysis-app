"""Compute the full indicator set locally with pandas-ta.

We compute everything once (it's cheap) and let the tailoring layer decide what to
surface per experience level. All values are taken from the most recent bar.
"""
import math

import pandas as pd
import pandas_ta as ta


def _clean(value):
    """Convert numpy/pandas scalars to JSON-safe floats; NaN/inf -> None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, 4)


def _support_resistance(df: pd.DataFrame, window: int = 20):
    """Simple recent support/resistance: rolling min(low)/max(high) over `window` bars."""
    recent = df.tail(window)
    return _clean(recent["low"].min()), _clean(recent["high"].max())


def _volume_at_level(df: pd.DataFrame, level, window: int = 20, tolerance: float = 0.01):
    """Total volume from recent bars that traded within ±tolerance of a price level.

    Daily bars can't tell us how much of a day's volume happened *at* a price, so
    a bar counts if its low-high range overlaps the level's tolerance band. High
    volume near a level suggests it's actively defended/contested (stronger)."""
    if level is None:
        return None
    recent = df.tail(window)
    lo, hi = level * (1 - tolerance), level * (1 + tolerance)
    touched = (recent["low"] <= hi) & (recent["high"] >= lo)
    return _clean(recent.loc[touched, "volume"].sum())


def _fibonacci_levels(df: pd.DataFrame, window: int = 90):
    """Fib retracement levels between the swing low and high of the recent window."""
    recent = df.tail(window)
    low = float(recent["low"].min())
    high = float(recent["high"].max())
    diff = high - low
    if diff == 0:
        return {}
    return {
        f"fib_{int(r * 1000)}": _clean(high - diff * r)
        for r in (0.236, 0.382, 0.5, 0.618, 0.786)
    }


def format_time(ts, intraday: bool):
    """lightweight-charts wants 'YYYY-MM-DD' strings for daily/weekly bars but
    Unix seconds for intraday bars."""
    return int(ts.timestamp()) if intraday else ts.strftime("%Y-%m-%d")


def _series_points(index, values, intraday: bool) -> list[dict]:
    """Pair a time index with a value series as [{time, value}], skipping NaNs.
    Shaped for lightweight-charts line series input."""
    points = []
    for ts, v in zip(index, values):
        v = _clean(v)
        if v is not None:
            points.append({"time": format_time(ts, intraday), "value": v})
    return points


def compute_series(df: pd.DataFrame, intraday: bool = False) -> dict[str, list[dict]]:
    """Full-length overlay line series for charting. Keys match the scalar
    indicator names in compute_indicators so tailoring can share one vocabulary."""
    out: dict[str, list[dict]] = {}
    out["sma_20"] = _series_points(df.index, ta.sma(df["close"], length=20), intraday)
    out["sma_50"] = _series_points(df.index, ta.sma(df["close"], length=50), intraday)
    bb = ta.bbands(df["close"], length=20)
    if bb is not None and not bb.empty:
        out["bb_lower"] = _series_points(df.index, bb.iloc[:, 0], intraday)
        out["bb_upper"] = _series_points(df.index, bb.iloc[:, 2], intraday)
    return out


def compute_indicators(df: pd.DataFrame) -> dict:
    """Return a flat dict of latest-bar indicator values across all tiers.

    Keys are grouped by indicator; the tailoring layer filters these by level.
    """
    out: dict = {}

    # --- Trend: moving averages ---
    out["sma_20"] = _clean(ta.sma(df["close"], length=20).iloc[-1])
    out["sma_50"] = _clean(ta.sma(df["close"], length=50).iloc[-1])
    out["ema_20"] = _clean(ta.ema(df["close"], length=20).iloc[-1])

    # --- Momentum: RSI ---
    out["rsi_14"] = _clean(ta.rsi(df["close"], length=14).iloc[-1])

    # --- Support / resistance ---
    support, resistance = _support_resistance(df)
    out["support"] = support
    out["resistance"] = resistance

    # --- MACD (intermediate) ---
    macd = ta.macd(df["close"])  # columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
    if macd is not None and not macd.empty:
        out["macd"] = _clean(macd.iloc[-1, 0])
        out["macd_histogram"] = _clean(macd.iloc[-1, 1])
        out["macd_signal"] = _clean(macd.iloc[-1, 2])

    # --- Bollinger Bands (intermediate) ---
    bb = ta.bbands(df["close"], length=20)  # BBL, BBM, BBU, BBB, BBP
    if bb is not None and not bb.empty:
        out["bb_lower"] = _clean(bb.iloc[-1, 0])
        out["bb_middle"] = _clean(bb.iloc[-1, 1])
        out["bb_upper"] = _clean(bb.iloc[-1, 2])

    # --- Volume (intermediate) ---
    out["volume_latest"] = _clean(df["volume"].iloc[-1])
    out["volume_avg_20"] = _clean(df["volume"].tail(20).mean())
    out["volume_at_support"] = _volume_at_level(df, support)
    out["volume_at_resistance"] = _volume_at_level(df, resistance)

    # --- Candlestick patterns (advanced) ---
    # pandas-ta exposes a small set without TA-Lib; doji is reliably available.
    try:
        doji = ta.cdl_pattern(df["open"], df["high"], df["low"], df["close"], name="doji")
        out["candle_doji"] = bool(doji.iloc[-1, 0] != 0) if doji is not None and not doji.empty else None
    except Exception:
        out["candle_doji"] = None

    # --- Fibonacci retracement levels (advanced) ---
    out.update(_fibonacci_levels(df))

    return out
