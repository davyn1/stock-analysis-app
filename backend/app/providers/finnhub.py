"""Finnhub price provider.

IMPORTANT: Finnhub moved the historical candle endpoint (/stock/candle) to paid
plans for US equities. On a free key this may return HTTP 403 or {"s": "no_data"}.
If you hit that, either upgrade the Finnhub plan or implement another PriceProvider
(Twelve Data / yfinance) and set PRICE_PROVIDER accordingly — the rest of the app
doesn't care which provider produced the DataFrame.
"""
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd

from .base import PriceProvider, ProviderError

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubProvider(PriceProvider):
    name = "finnhub"

    def __init__(self, api_key: str):
        if not api_key:
            raise ProviderError("FINNHUB_API_KEY is not set.")
        self.api_key = api_key

    def get_daily_ohlcv(self, symbol: str, days: int) -> pd.DataFrame:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        params = {
            "symbol": symbol.upper(),
            "resolution": "D",
            "from": int(start.timestamp()),
            "to": int(now.timestamp()),
            "token": self.api_key,
        }
        try:
            resp = httpx.get(f"{BASE_URL}/stock/candle", params=params, timeout=20.0)
        except httpx.HTTPError as e:
            raise ProviderError(f"Network error contacting Finnhub: {e}") from e

        if resp.status_code == 403:
            raise ProviderError(
                "Finnhub returned 403 — the historical candle endpoint requires a "
                "paid plan for US stocks. Upgrade your Finnhub plan or switch "
                "PRICE_PROVIDER to another source."
            )
        if resp.status_code == 429:
            raise ProviderError("Finnhub rate limit hit (60 calls/min on free tier). Try again shortly.")
        if resp.status_code != 200:
            raise ProviderError(f"Finnhub error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        if data.get("s") != "ok":
            raise ProviderError(
                f"Finnhub returned no usable data for {symbol!r} (status={data.get('s')!r}). "
                "Check the ticker, or the free tier may not cover candles for this symbol."
            )

        df = pd.DataFrame(
            {
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            },
            index=pd.to_datetime(data["t"], unit="s", utc=True).normalize(),
        )
        df.index.name = "date"
        return df.sort_index()
