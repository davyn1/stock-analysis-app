"""Price-data providers. Add new sources by implementing PriceProvider."""
from .base import PriceProvider, ProviderError
from .finnhub import FinnhubProvider
from .twelvedata import TwelveDataProvider
from .yfinance_provider import YFinanceProvider
from ..config import settings


def get_provider() -> PriceProvider:
    """Factory: return the price provider selected by PRICE_PROVIDER."""
    name = settings.price_provider.lower()
    if name == "twelvedata":
        return TwelveDataProvider(settings.twelve_data_api_key)
    if name == "yfinance":
        return YFinanceProvider()
    if name == "finnhub":
        return FinnhubProvider(settings.finnhub_api_key)
    raise ProviderError(
        f"Unknown PRICE_PROVIDER: {settings.price_provider!r}. "
        "Use one of: twelvedata, yfinance, finnhub."
    )


__all__ = [
    "PriceProvider", "ProviderError",
    "FinnhubProvider", "TwelveDataProvider", "YFinanceProvider",
    "get_provider",
]
