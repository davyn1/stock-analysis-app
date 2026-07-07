"""Pydantic request/response models for the API."""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExperienceLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])
    level: ExperienceLevel = ExperienceLevel.beginner
    days: int = Field(180, ge=60, le=730, description="Lookback window in calendar days")


class AnalyzeResponse(BaseModel):
    symbol: str
    as_of: str
    level: ExperienceLevel
    latest_close: float
    indicators: dict[str, Any]   # only the indicators surfaced for this level
    explanation: str
    data_source: str
    cached_explanation: bool
