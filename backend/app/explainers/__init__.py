"""Explanation providers. Add a new LLM by implementing Explainer."""
from ..config import settings
from ..schemas import ExperienceLevel
from .base import Explainer, to_plain_text
from .claude import ClaudeExplainer
from .gemini import GeminiExplainer


def get_explainer() -> Explainer:
    """Factory: return the explainer selected by EXPLAIN_PROVIDER."""
    name = settings.explain_provider.lower()
    if name == "gemini":
        return GeminiExplainer()
    if name == "claude":
        return ClaudeExplainer()
    # Unknown value -> safe default rather than crashing the request.
    return ClaudeExplainer()


def generate_explanation(
    symbol: str, level: ExperienceLevel, indicators: dict, verdict: dict | None = None
) -> str:
    return to_plain_text(get_explainer().generate(symbol, level, indicators, verdict))


__all__ = ["Explainer", "ClaudeExplainer", "GeminiExplainer", "get_explainer", "generate_explanation"]
