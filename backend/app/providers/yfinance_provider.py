"""yfinance price provider — zero setup (no API key), great for local testing.

WARNING: yfinance scrapes Yahoo's unofficial endpoints. It can break when Yahoo
changes things, and Yahoo frequently rate-limits/blocks datacenter IPs — so this
may fail once deployed to AWS. Prefer Twelve Data in production.
"""
import pandas as pd

from .base import PriceProvider, ProviderError


class YFinanceProvider(PriceProvider):
    name = "yfinance"

    # app interval -> (yfinance interval, history window, resample rule)
    # Windows are Yahoo's hard limits: ~8 days for 1m data, ~60 days for 5m/15m,
    # ~730 days for 1h. 3m and 4h aren't native — resampled from 1m / 1h.
    # Windows trimmed for payload size: 60-730d of fine-grained bars is 1MB+ of
    # JSON per request and nobody scrolls that far back on an intraday chart.
    _INTERVALS = {
        "1m": ("1m", "7d", None),
        "3m": ("1m", "7d", "3min"),
        "5m": ("5m", "30d", None),
        "15m": ("15m", "60d", None),
        "1h": ("1h", "180d", None),
        "4h": ("1h", "730d", "4h"),
        "1w": ("1wk", "5y", None),
    }

    def get_ohlcv(self, symbol: str, interval: str) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as e:
            raise ProviderError("yfinance is not installed. `pip install yfinance`.") from e

        spec = self._INTERVALS.get(interval)
        if spec is None:
            raise ProviderError(f"Unsupported interval {interval!r}.")
        yf_interval, period, resample_rule = spec

        try:
            df = yf.Ticker(symbol.upper()).history(
                period=period, interval=yf_interval, auto_adjust=False
            )
        except Exception as e:
            raise ProviderError(f"yfinance failed for {symbol!r} ({interval}): {e}") from e

        if df is None or df.empty:
            raise ProviderError(f"yfinance returned no {interval} data for {symbol!r}.")

        df = df.rename(
            columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        )
        df.index = pd.to_datetime(df.index, utc=True)  # keep intraday times, no normalize
        df = df[["open", "high", "low", "close", "volume"]].sort_index()
        df = df.dropna(subset=["open", "high", "low", "close"])
        df["volume"] = df["volume"].fillna(0)

        if resample_rule:
            df = (
                df.resample(resample_rule)
                .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
                .dropna()
            )
        return df

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
        df = df[["open", "high", "low", "close", "volume"]].sort_index()
        # Yahoo sometimes appends an in-progress/placeholder bar with NaN prices
        # (e.g. today's session before close) — incomplete bars never enter the app.
        df = df.dropna(subset=["open", "high", "low", "close"])
        df["volume"] = df["volume"].fillna(0)
        return df
