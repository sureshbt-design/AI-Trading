"""
PATCC Data Service

Acts as the single gateway for market data.
"""

from Providers.yahoo_provider import YahooProvider
from Services.cache_service import CacheService


class DataService:

    def __init__(self, provider=None, cache_service=None):
        self.provider = provider or YahooProvider()
        self.cache = cache_service or CacheService()

    def get_history(
        self,
        symbol: str,
        period: str = "6mo",
        interval: str = "1d",
        use_cache: bool = True,
    ):
        cache_key = f"history_{symbol}_{period}_{interval}"

        if use_cache and not self.cache.is_expired(
            cache_key,
            max_age_minutes=60,
        ):
            print(f"Loading {symbol} from cache...")
            return self.cache.load(cache_key)

        print(f"Downloading {symbol} from Yahoo Finance...")

        data = self.provider.get_history(
            symbol,
            period,
            interval,
        )

        if use_cache:
            self.cache.save(cache_key, data)

        return data

    def get_quote(self, symbol: str):
        return self.provider.get_quote(symbol)

    def search(self, text: str):
        return self.provider.search(text)