"""Shared prompt construction + interface for explanation providers.

The LLM ONLY explains pre-computed numbers — it never calculates anything. All
providers share the same system prompt and per-level guidance so swapping models
doesn't change the behavior, only the voice/cost.
"""
import json
import math
import re
from abc import ABC, abstractmethod

from ..schemas import ExperienceLevel

LEVEL_GUIDANCE = {
    ExperienceLevel.beginner: (
        "The reader is a BEGINNER. Use plain, friendly language and avoid heavy jargon. "
        "Keep it to ~2-3 short paragraphs. Focus on the big picture: is the trend up or "
        "down, and is the stock looking stretched or calm right now?"
    ),
    ExperienceLevel.intermediate: (
        "The reader is an INTERMEDIATE investor who knows the basics. You can reference "
        "MACD, Bollinger Bands and volume without defining them in depth. Connect the "
        "indicators into a coherent read of momentum and trend. ~3-4 paragraphs."
    ),
    ExperienceLevel.advanced: (
        "The reader is ADVANCED. Be concise and precise, cite the raw values, note "
        "confluences/divergences (e.g. price vs. MACD, Fib levels near support), and "
        "skip basic definitions. Bullet points are fine."
    ),
}

SYSTEM_PROMPT = (
    "You are a technical-analysis explainer for a personal stock app. You are given "
    "pre-computed indicator values for one stock. Explain what they collectively suggest "
    "about the stock's technical picture, tailored to the reader's experience level.\n\n"
    "HARD RULES:\n"
    "- Use ONLY the numbers provided. Never calculate, estimate, or invent any value.\n"
    "- Do NOT define or explain what each indicator is (e.g. don't write 'RSI is a "
    "momentum indicator that measures...'). The app already shows a definition when "
    "the user hovers over each value. Start directly from interpretation — what the "
    "values imply together (trend, momentum, stretched vs. calm, key levels).\n"
    "- You may name indicators and cite their values, just don't teach what they are.\n"
    "- Values are already rounded for display. Quote them exactly as given; never add "
    "decimal places. Write large numbers with thousands separators (39,496,500).\n"
    "- Never comment on what data you were or weren't given. Explain only from the "
    "values present; if a verdict factor cites something not in the values, explain "
    "it in words without a number.\n"
    "- Write plain text only. No Markdown: no **bold**, no *italics*, no # headings, no "
    "backticks. Separate sections with a blank line; a section title goes on its own "
    "line ending in a colon. For a list, start each line with '• '.\n"
    "- If an indicator value is null/missing, say it's unavailable rather than guessing.\n"
    "- If a pre-computed VERDICT is provided, it was decided by the app's deterministic "
    "rules. Explain WHY its factors point the way they do, per horizon. Never override, "
    "re-grade, soften, or contradict the verdict, and never produce your own rating.\n"
    "- This is educational analysis, NOT financial advice. Do not tell the reader to "
    "buy or sell. End with a one-line reminder that this isn't financial advice."
)


def round_for_prompt(value):
    """Round every float the LLM will see: whole numbers from 1,000 up (volumes,
    large prices), 2 decimals below. Rounding happens here in code so the model
    only ever quotes display-ready numbers — it never rounds (calculates) itself."""
    if isinstance(value, float):
        if not math.isfinite(value):
            return value
        return round(value) if abs(value) >= 1000 else round(value, 2)
    if isinstance(value, dict):
        return {k: round_for_prompt(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [round_for_prompt(v) for v in value]
    return value


_BULLET = re.compile(r"^(\s*)[*\-+]\s+", re.MULTILINE)
_HEADING = re.compile(r"^\s*#{1,6}\s*", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*\*|__|`)")


def to_plain_text(text: str) -> str:
    """Safety net for models that emit Markdown despite the prompt: the UI shows
    the explanation as plain pre-wrapped text, so raw ** / * / # would be visible."""
    text = _HEADING.sub("", text)
    text = _BULLET.sub(r"\1• ", text)
    return _EMPHASIS.sub("", text)


def build_user_content(
    symbol: str, level: ExperienceLevel, indicators: dict, verdict: dict | None = None
) -> str:
    indicators = round_for_prompt(indicators)
    verdict_block = (
        f"App-computed verdict (deterministic — interpret it, do not change it):\n"
        f"{json.dumps(round_for_prompt(verdict), indent=2)}\n\n"
        if verdict
        else ""
    )
    return (
        f"Stock: {symbol}\n"
        f"Reader level guidance: {LEVEL_GUIDANCE[level]}\n\n"
        f"Pre-computed indicator values (JSON):\n{json.dumps(indicators, indent=2)}\n\n"
        f"{verdict_block}"
        f"Write the explanation now."
    )


def raw_fallback(symbol: str, level: ExperienceLevel, indicators: dict, reason: str) -> str:
    """Returned when no API key is configured or a provider call fails, so the
    pipeline still produces *something* and /analyze never hard-fails on the LLM."""
    return (
        f"[{reason}] Computed indicators for {symbol} ({level.value}): "
        f"{json.dumps(indicators)}"
    )


class Explainer(ABC):
    name: str = "base"

    @abstractmethod
    def generate(
        self, symbol: str, level: ExperienceLevel, indicators: dict,
        verdict: dict | None = None,
    ) -> str:
        """Return a plain-language explanation of the given indicator values
        (and, when provided, the app's pre-decided verdict)."""
        raise NotImplementedError
