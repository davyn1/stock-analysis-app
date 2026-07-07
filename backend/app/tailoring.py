"""Rules-based tailoring layer: which indicators are surfaced per experience level.

Levels are cumulative: intermediate sees everything beginner sees, plus more;
advanced sees everything.
"""
from .schemas import ExperienceLevel

# Indicator keys (from indicators.compute_indicators) grouped by the level at
# which they first appear.
_BEGINNER_KEYS = ["sma_20", "sma_50", "rsi_14", "support", "resistance"]

_INTERMEDIATE_KEYS = [
    "macd", "macd_signal", "macd_histogram",
    "bb_lower", "bb_middle", "bb_upper",
    "volume_latest", "volume_avg_20",
    "volume_at_support", "volume_at_resistance",
    "ema_20",
]

_ADVANCED_KEYS = [
    "candle_doji",
    "fib_236", "fib_382", "fib_500", "fib_618", "fib_786",
]


def keys_for_level(level: ExperienceLevel) -> list[str]:
    keys = list(_BEGINNER_KEYS)
    if level in (ExperienceLevel.intermediate, ExperienceLevel.advanced):
        keys += _INTERMEDIATE_KEYS
    if level == ExperienceLevel.advanced:
        keys += _ADVANCED_KEYS
    return keys


def filter_indicators(all_indicators: dict, level: ExperienceLevel) -> dict:
    """Return only the indicators appropriate for the given level (preserving order)."""
    wanted = keys_for_level(level)
    return {k: all_indicators[k] for k in wanted if k in all_indicators}


# --- Chart overlays ---------------------------------------------------------
# Line series drawn over the candles, and horizontal price levels, per level.
# Keys share the indicator vocabulary above.

_CHART_LINES_BEGINNER = ["sma_20", "sma_50"]
_CHART_LINES_INTERMEDIATE = ["bb_upper", "bb_lower"]

_CHART_LEVELS_BEGINNER = ["support", "resistance"]
_CHART_LEVELS_ADVANCED = ["fib_236", "fib_382", "fib_500", "fib_618", "fib_786"]


def chart_line_keys(level: ExperienceLevel) -> list[str]:
    keys = list(_CHART_LINES_BEGINNER)
    if level in (ExperienceLevel.intermediate, ExperienceLevel.advanced):
        keys += _CHART_LINES_INTERMEDIATE
    return keys


def chart_level_keys(level: ExperienceLevel) -> list[str]:
    keys = list(_CHART_LEVELS_BEGINNER)
    if level == ExperienceLevel.advanced:
        keys += _CHART_LEVELS_ADVANCED
    return keys
