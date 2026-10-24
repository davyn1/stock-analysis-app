"""Application settings, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Data providers
    finnhub_api_key: str = ""
    twelve_data_api_key: str = ""
    price_provider: str = "twelvedata"

    # Explanation layer — which LLM generates the narrative
    explain_provider: str = "gemini"  # gemini | claude

    # Claude
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # Google Gemini (free tier via https://aistudio.google.com/)
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Storage
    database_url: str = "sqlite:///./stock_cache.db"

    # Trading endpoints (/trading/*). Leave empty for open local dev; set on
    # deploy to require `Authorization: Bearer <token>`. See app/auth.py.
    trading_token: str = ""


settings = Settings()
