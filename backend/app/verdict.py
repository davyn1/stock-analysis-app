"""Verdict engine: the analyzer's headline output — a deterministic, per-horizon
read on whether a ticker's technical picture looks favorable to buy/hold.

Design (mirrors signals.py / backtest.py — plain functions, plain dicts):
- Three horizons (short / medium / long), each scored by a fixed checklist of
  technical conditions. Every factor is named and shown to the user, so the
  verdict is fully auditable — no black box.
- Scoring: each factor votes bullish (+1), bearish (-1), or neutral (0).
  Net score >= +2 -> "favorable", <= -2 -> "unfavorable", else "neutral".
  A horizon with fewer than 2 decidable factors is "insufficient" (e.g. a
  recent IPO with no 200-day history).
- The verdict is decided HERE, in deterministic code. The LLM only receives the
  finished verdict to interpret in plain language — it never decides, re-grades,
  or overrides it. Same hard rule as "LLM never calculates".
- Phase 1 is technicals-only; fundamentals (Finnhub) are the planned second
  evidence layer for the long horizon.
"""
import pandas as pd
import pandas_ta as ta

from .indicators import format_time

BULLISH, BEARISH, NEUTRAL, UNAVAILABLE = "bullish", "bearish", "neutral", "unavailable"

_VOTE = {BULLISH: 1, BEARISH: -1, NEUTRAL: 0}


def _factor(label: str, direction: str, detail: str, group: str = "technicals") -> dict:
    return {"label": label, "direction": direction, "detail": detail, "group": group}


def _vs(label, value, reference, above_detail, below_detail, above=BULLISH, below=BEARISH):
    """Factor from comparing a value against a reference level."""
    if value is None or reference is None:
        return _factor(label, UNAVAILABLE, "Not enough history to compute.")
    if value > reference:
        return _factor(label, above, above_detail)
    return _factor(label, below, below_detail)


def _short_factors(ind: dict, recent_events: list[dict]) -> list[dict]:
    f = [
        _vs("Price vs 20-day average", ind.get("latest_close"), ind.get("sma_20"),
            "Price is trading above its 20-day average — near-term trend is up.",
            "Price is trading below its 20-day average — near-term trend is down."),
        _vs("MACD momentum", ind.get("macd"), ind.get("macd_signal"),
            "MACD is above its signal line — upward momentum.",
            "MACD is below its signal line — downward momentum."),
    ]

    rsi = ind.get("rsi_14")
    if rsi is None:
        f.append(_factor("RSI (14)", UNAVAILABLE, "Not enough history to compute."))
    elif rsi >= 70:
        f.append(_factor("RSI (14)", BEARISH,
                         f"RSI at {rsi:.0f} is in overbought territory — the move looks stretched."))
    elif rsi <= 30:
        f.append(_factor("RSI (14)", BULLISH,
                         f"RSI at {rsi:.0f} is in oversold territory — selling looks exhausted."))
    else:
        f.append(_factor("RSI (14)", NEUTRAL, f"RSI at {rsi:.0f} is in the neutral zone."))

    # Net read of the last ~10 bars of signal events.
    bull = sum(1 for e in recent_events if e["direction"] == "bullish")
    bear = sum(1 for e in recent_events if e["direction"] == "bearish")
    if not recent_events:
        f.append(_factor("Recent signals", NEUTRAL, "No signals fired in the last two weeks."))
    elif bull > bear:
        f.append(_factor("Recent signals", BULLISH,
                         f"{bull} bullish vs {bear} bearish signal(s) in the last two weeks."))
    elif bear > bull:
        f.append(_factor("Recent signals", BEARISH,
                         f"{bear} bearish vs {bull} bullish signal(s) in the last two weeks."))
    else:
        f.append(_factor("Recent signals", NEUTRAL,
                         "Recent bullish and bearish signals are balanced."))
    return f


def _medium_factors(ind: dict) -> list[dict]:
    f = [
        _vs("20 vs 50-day trend", ind.get("sma_20"), ind.get("sma_50"),
            "The 20-day average is above the 50-day — the medium-term trend is up.",
            "The 20-day average is below the 50-day — the medium-term trend is down."),
        _vs("Price vs 50-day average", ind.get("latest_close"), ind.get("sma_50"),
            "Price is holding above its 50-day average.",
            "Price has slipped below its 50-day average."),
        _vs("3-month direction", ind.get("pct_change_3m"), 0.0,
            "The stock is up over the last three months.",
            "The stock is down over the last three months."),
        _vs("Bollinger position", ind.get("latest_close"), ind.get("bb_middle"),
            "Price sits in the upper half of its Bollinger range — buyers in control.",
            "Price sits in the lower half of its Bollinger range — sellers in control."),
    ]
    return f


def _long_factors(ind: dict, sma200_slope) -> list[dict]:
    f = [
        _vs("Price vs 200-day average", ind.get("latest_close"), ind.get("sma_200"),
            "Price is above its 200-day average — the classic long-term uptrend test passes.",
            "Price is below its 200-day average — the long-term trend is under pressure."),
        _vs("50 vs 200-day trend", ind.get("sma_50"), ind.get("sma_200"),
            "The 50-day average is above the 200-day (golden-cross state) — long-term structure is bullish.",
            "The 50-day average is below the 200-day (death-cross state) — long-term structure is bearish."),
        _vs("1-year direction", ind.get("pct_change_1y"), 0.0,
            "The stock is up over the last year.",
            "The stock is down over the last year."),
    ]

    off_high = ind.get("pct_from_52w_high")
    if off_high is None:
        f.append(_factor("Distance from 52-week high", UNAVAILABLE, "Not enough history to compute."))
    elif off_high >= -10:
        f.append(_factor("Distance from 52-week high", BULLISH,
                         f"Price is within {abs(off_high):.0f}% of its 52-week high — the uptrend is intact."))
    elif off_high <= -25:
        f.append(_factor("Distance from 52-week high", BEARISH,
                         f"Price is {abs(off_high):.0f}% below its 52-week high — a deep drawdown."))
    else:
        f.append(_factor("Distance from 52-week high", NEUTRAL,
                         f"Price is {abs(off_high):.0f}% below its 52-week high."))

    if sma200_slope is None:
        f.append(_factor("200-day trend direction", UNAVAILABLE, "Not enough history to compute."))
    elif sma200_slope > 0:
        f.append(_factor("200-day trend direction", BULLISH,
                         "The 200-day average itself is rising — the long-term base is improving."))
    else:
        f.append(_factor("200-day trend direction", BEARISH,
                         "The 200-day average itself is falling — the long-term base is deteriorating."))
    return f


def _fundamental_factors(fund: dict | None) -> list[dict]:
    """Long-horizon evidence from company fundamentals (phase 2). Thresholds are
    deliberately simple absolutes — crude but deterministic and explainable.
    All factors are 'unavailable' when fundamentals couldn't be fetched."""
    F = "fundamentals"
    if not fund:
        return [
            _factor("Fundamentals", UNAVAILABLE,
                    "Company fundamentals unavailable (no Finnhub key configured, or fetch failed).", F)
        ]
    f = []

    margin = fund.get("net_margin")
    if margin is None:
        f.append(_factor("Profitability", UNAVAILABLE, "Net margin unavailable.", F))
    elif margin > 0:
        f.append(_factor("Profitability", BULLISH,
                         f"The company is profitable (net margin {margin:.1f}%).", F))
    else:
        f.append(_factor("Profitability", BEARISH,
                         f"The company is losing money (net margin {margin:.1f}%).", F))

    eps_g = fund.get("eps_growth_yoy")
    if eps_g is None:
        f.append(_factor("Earnings growth", UNAVAILABLE, "EPS growth unavailable.", F))
    elif eps_g > 0:
        f.append(_factor("Earnings growth", BULLISH, f"Earnings per share are growing ({eps_g:.1f}%).", F))
    else:
        f.append(_factor("Earnings growth", BEARISH, f"Earnings per share are shrinking ({eps_g:.1f}%).", F))

    rev_g = fund.get("revenue_growth_yoy")
    if rev_g is None:
        f.append(_factor("Revenue growth", UNAVAILABLE, "Revenue growth unavailable.", F))
    elif rev_g > 0:
        f.append(_factor("Revenue growth", BULLISH, f"Revenue is growing ({rev_g:.1f}%).", F))
    else:
        f.append(_factor("Revenue growth", BEARISH, f"Revenue is shrinking ({rev_g:.1f}%).", F))

    pe = fund.get("pe_ttm")
    if pe is None or pe <= 0:
        f.append(_factor("Valuation (P/E)", UNAVAILABLE,
                         "P/E unavailable (often means no positive trailing earnings).", F))
    elif pe <= 25:
        f.append(_factor("Valuation (P/E)", BULLISH,
                         f"P/E of {pe:.1f} — reasonably valued by broad-market norms.", F))
    elif pe <= 50:
        f.append(_factor("Valuation (P/E)", NEUTRAL,
                         f"P/E of {pe:.1f} — a growth premium is priced in.", F))
    else:
        f.append(_factor("Valuation (P/E)", BEARISH,
                         f"P/E of {pe:.1f} — richly valued; a lot must go right.", F))

    de = fund.get("debt_to_equity")
    if de is None:
        f.append(_factor("Balance sheet", UNAVAILABLE, "Debt/equity unavailable.", F))
    elif de < 1:
        f.append(_factor("Balance sheet", BULLISH, f"Debt is modest relative to equity ({de:.2f}x).", F))
    elif de <= 2:
        f.append(_factor("Balance sheet", NEUTRAL, f"Moderate leverage ({de:.2f}x debt to equity).", F))
    else:
        f.append(_factor("Balance sheet", BEARISH, f"Heavy leverage ({de:.2f}x debt to equity).", F))

    roe = fund.get("roe")
    if roe is None:
        f.append(_factor("Return on equity", UNAVAILABLE, "ROE unavailable.", F))
    elif roe > 15:
        f.append(_factor("Return on equity", BULLISH, f"Strong returns on shareholder capital (ROE {roe:.1f}%).", F))
    elif roe >= 0:
        f.append(_factor("Return on equity", NEUTRAL, f"Modest returns on shareholder capital (ROE {roe:.1f}%).", F))
    else:
        f.append(_factor("Return on equity", BEARISH, f"Negative returns on shareholder capital (ROE {roe:.1f}%).", F))

    return f


def _grade(factors: list[dict]) -> dict:
    decidable = [f for f in factors if f["direction"] != UNAVAILABLE]
    score = sum(_VOTE[f["direction"]] for f in decidable)
    if len(decidable) < 2:
        verdict = "insufficient"
    elif score >= 2:
        verdict = "favorable"
    elif score <= -2:
        verdict = "unfavorable"
    else:
        verdict = "neutral"
    return {"verdict": verdict, "score": score, "max_score": len(decidable)}


def compute_verdict(
    df: pd.DataFrame, ind: dict, events: list[dict], fundamentals: dict | None = None
) -> dict:
    """Deterministic per-horizon verdict from the full daily frame + indicators.

    `ind` is the full compute_indicators dict; `events` the detect_signals list;
    `fundamentals` the normalized dict from fundamentals.get_fundamentals (or
    None — long horizon then grades on technicals alone).
    Returns a JSON-safe dict shaped for the API and the verdict card UI.
    """
    ind = dict(ind)
    ind["latest_close"] = float(df["close"].iloc[-1])

    # 200-day SMA slope over the last month — computed here (deterministic code,
    # same as signals.py computing its own series), not surfaced as an indicator.
    sma200 = ta.sma(df["close"], length=200)
    sma200_slope = None
    if sma200 is not None and len(sma200.dropna()) >= 22:
        sma200_slope = float(sma200.iloc[-1] - sma200.iloc[-22])

    recent_times = {format_time(ts, False) for ts in df.index[-10:]}
    recent_events = [e for e in events if e["time"] in recent_times]

    fund_factors = _fundamental_factors(fundamentals)
    has_fundamentals = any(f["direction"] != UNAVAILABLE for f in fund_factors)

    horizons = []
    for key, label, window, factors in (
        ("short", "Short term", "days to weeks", _short_factors(ind, recent_events)),
        ("medium", "Medium term", "weeks to months", _medium_factors(ind)),
        ("long", "Long term", "6+ months", _long_factors(ind, sma200_slope) + fund_factors),
    ):
        horizons.append({"key": key, "label": label, "window": window,
                         **_grade(factors), "factors": factors})

    return {
        "horizons": horizons,
        "basis": "technicals + fundamentals (long term)" if has_fundamentals else "technicals-only",
    }
