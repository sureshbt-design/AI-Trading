"""
PATCC Provider Interface

Every market data provider must implement this interface.
"""

from abc import ABC, abstractmethod


class IDataProvider(ABC):

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        period: str = "6mo",
        interval: str = "1d",
    ):
        """Return historical market data."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str):
        """Return the latest quote."""
        pass

    @abstractmethod
    def search(self, text: str):
        """Search for symbols."""
        pass
