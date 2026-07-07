"""Twelve Data price provider — official API, works reliably from AWS/datacenter IPs.

Free tier: 800 calls/day, 8 calls/min. With daily caching that's far more than a
two-user app needs. Get a free key at https://twelvedata.com/.
"""
import httpx
import pandas as pd

from .base import PriceProvider, ProviderError

BASE_URL = "https://api.twelvedata.com/time_series"


class TwelveDataProvider(PriceProvider):
    name = "twelvedata"

    def __init__(self, api_key: str):
        if not api_key:
            raise ProviderError("TWELVE_DATA_API_KEY is not set.")
        self.api_key = api_key

    def get_daily_ohlcv(self, symbol: str, days: int) -> pd.DataFrame:
        params = {
            "symbol": symbol.upper(),
            "interval": "1day",
            # outputsize is a bar count; days is calendar days, so this is a safe
            # upper bound (markets are closed weekends/holidays). Cap at API max.
            "outputsize": min(days, 5000),
            "apikey": self.api_key,
            "format": "JSON",
        }
        try:
            resp = httpx.get(BASE_URL, params=params, timeout=20.0)
        except httpx.HTTPError as e:
            raise ProviderError(f"Network error contacting Twelve Data: {e}") from e

        if resp.status_code == 429:
            raise ProviderError("Twelve Data rate limit hit (8 calls/min / 800/day on free). Try again shortly.")
        if resp.status_code != 200:
            raise ProviderError(f"Twelve Data error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        if data.get("status") == "error":
            raise ProviderError(f"Twelve Data: {data.get('message', 'unknown error')}")

        values = data.get("values")
        if not values:
            raise ProviderError(f"Twelve Data returned no data for {symbol!r}.")

        df = pd.DataFrame(values)
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.normalize()
        df = df.set_index("datetime")
        df.index.name = "date"
        # Values arrive newest-first as strings; cast and sort ascending.
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df[["open", "high", "low", "close", "volume"]].sort_index()
