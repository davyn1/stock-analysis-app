"""yfinance price provider — zero setup (no API key), great for local testing.

WARNING: yfinance scrapes Yahoo's unofficial endpoints. It can break when Yahoo
changes things, and Yahoo frequently rate-limits/blocks datacenter IPs — so this
may fail once deployed to AWS. Prefer Twelve Data in production.
"""
import pandas as pd

from .base import PriceProvider, ProviderError


class YFinanceProvider(PriceProvider):
    name = "yfinance"

    def get_daily_ohlcv(self, symbol: str, days: int) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as e:
            raise ProviderError("yfinance is not installed. `pip install yfinance`.") from e

        try:
            df = yf.Ticker(symbol.upper()).history(
                period=f"{days}d", interval="1d", auto_adjust=False
            )
        except Exception as e:
            raise ProviderError(f"yfinance failed for {symbol!r}: {e}") from e

        if df is None or df.empty:
            raise ProviderError(
                f"yfinance returned no data for {symbol!r} (bad ticker, or Yahoo "
                "blocked this IP — common on AWS/datacenter hosts)."
            )

        df = df.rename(
            columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        )
        # Normalize to a tz-aware UTC date index to match the other providers.
        df.index = pd.to_datetime(df.index, utc=True).normalize()
        df.index.name = "date"
        return df[["open", "high", "low", "close", "volume"]].sort_index()
