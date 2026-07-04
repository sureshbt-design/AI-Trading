"""
PATCC Yahoo Finance Provider
"""

import yfinance as yf

from Providers.provider_interface import IDataProvider


class YahooProvider(IDataProvider):

    def get_history(
        self,
        symbol: str,
        period: str = "6mo",
        interval: str = "1d",
    ):

        return yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )

    def get_quote(self, symbol: str):

        ticker = yf.Ticker(symbol)

        return ticker.fast_info

    def search(self, text: str):

        # Placeholder until we add a richer search provider.
        return []
