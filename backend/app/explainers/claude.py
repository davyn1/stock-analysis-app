"""Claude (Anthropic) explanation provider."""
from anthropic import Anthropic

from ..config import settings
from ..schemas import ExperienceLevel
from .base import Explainer, SYSTEM_PROMPT, build_user_content, raw_fallback


class ClaudeExplainer(Explainer):
    name = "claude"

    def generate(
        self, symbol: str, level: ExperienceLevel, indicators: dict,
        verdict: dict | None = None,
    ) -> str:
        if not settings.anthropic_api_key:
            return raw_fallback(symbol, level, indicators, "Anthropic API key not set")

        try:
            client = Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=900,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_content(symbol, level, indicators, verdict)}],
            )
            return "".join(b.text for b in msg.content if b.type == "text").strip()
        except Exception as e:
            return raw_fallback(symbol, level, indicators, f"Claude call failed: {e}")
