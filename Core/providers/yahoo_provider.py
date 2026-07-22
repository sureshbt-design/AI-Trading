"""
yahoo_provider.py

Yahoo Finance implementation of the PATCC market-data provider contract.
"""

import yfinance as yf

from Core.market_data_provider import (
    MarketDataProvider,
    ProviderRequest,
    ProviderResponse,
)


class YahooMarketDataProvider(MarketDataProvider):
    """
    Research and watchlist market-data provider using Yahoo Finance.
    """

    def get_price_history(self, request: ProviderRequest) -> ProviderResponse:
        ticker = request.ticker.upper().strip()

        data = yf.download(
            ticker,
            period=request.period,
            interval=request.interval,
            auto_adjust=request.auto_adjust,
            progress=False,
        )

        return ProviderResponse(
            data=data,
            source="Yahoo Finance",
            mode="Research / Watchlist",
            realtime=False,
        )
