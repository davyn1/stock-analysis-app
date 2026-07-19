"""Google Gemini explanation provider (free tier via https://aistudio.google.com/).

Uses the REST API over httpx so it goes through the same TLS path as the rest of
the app (truststore covers the corporate proxy) and needs no extra SDK.
"""
import httpx

from ..config import settings
from ..schemas import ExperienceLevel
from .base import Explainer, SYSTEM_PROMPT, build_user_content, raw_fallback

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiExplainer(Explainer):
    name = "gemini"

    def generate(
        self, symbol: str, level: ExperienceLevel, indicators: dict,
        verdict: dict | None = None,
    ) -> str:
        if not settings.google_api_key:
            return raw_fallback(symbol, level, indicators, "Google API key not set")

        url = f"{BASE_URL}/{settings.gemini_model}:generateContent"
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {"role": "user", "parts": [{"text": build_user_content(symbol, level, indicators, verdict)}]}
            ],
            "generationConfig": {
                "maxOutputTokens": 1200,
                "temperature": 0.4,
                # Gemini 2.5 models "think" by default, and those thought tokens
                # count against maxOutputTokens — which truncates the answer.
                # Explaining pre-computed numbers needs no chain-of-thought, so
                # turn thinking off for speed, cost, and full-length output.
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        try:
            resp = httpx.post(
                url,
                params={"key": settings.google_api_key},
                json=payload,
                timeout=30.0,
            )
            if resp.status_code != 200:
                return raw_fallback(
                    symbol, level, indicators,
                    f"Gemini error {resp.status_code}: {resp.text[:160]}",
                )
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except Exception as e:
            return raw_fallback(symbol, level, indicators, f"Gemini call failed: {e}")
