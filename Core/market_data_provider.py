"""
market_data_provider.py

Provider contract for PATCC market-data sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ProviderRequest:
    """
    Provider-neutral request passed to a market-data provider.
    """

    ticker: str
    period: str
    interval: str
    auto_adjust: bool = True


@dataclass
class ProviderResponse:
    """
    Raw response returned by a market-data provider.

    Validation and normalization remain the responsibility of
    MarketDataService.
    """

    data: pd.DataFrame
    source: str
    mode: str
    realtime: bool


class MarketDataProvider(ABC):
    """
    Abstract contract implemented by every PATCC market-data provider.
    """

    @abstractmethod
    def get_price_history(self, request: ProviderRequest) -> ProviderResponse:
        """
        Retrieve raw OHLCV price history.
        """
        raise NotImplementedError
