"""Provider interface. Implement this to add a new data source (Twelve Data, yfinance, ...)."""
from abc import ABC, abstractmethod

import pandas as pd


class ProviderError(Exception):
    """Raised when a provider can't return usable data (auth, no_data, rate limit, etc.)."""


class PriceProvider(ABC):
    name: str = "base"

    @abstractmethod
    def get_daily_ohlcv(self, symbol: str, days: int) -> pd.DataFrame:
        """Return a DataFrame indexed by date with columns:
        open, high, low, close, volume — ascending by date, daily resolution.

        Raise ProviderError on any failure so the caller can surface a clear message.
        """
        raise NotImplementedError

    def get_ohlcv(self, symbol: str, interval: str) -> pd.DataFrame:
        """Return OHLCV at an app-level interval ('1m','3m','5m','15m','1h','4h','1w').

        Optional capability — providers that can't serve intraday/weekly data keep
        this default, which fails with a clear message.
        """
        raise ProviderError(
            f"The {self.name!r} provider does not support interval data; "
            "set PRICE_PROVIDER=yfinance for intraday timeframes."
        )
