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
