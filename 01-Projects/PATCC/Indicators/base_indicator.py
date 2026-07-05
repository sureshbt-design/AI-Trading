"""
PATCC Base Indicator

Every technical indicator derives from this class.
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseIndicator(ABC):
    """
    Abstract base class for all PATCC indicators.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def calculate(self, data: pd.DataFrame):
        """
        Calculate indicator values from OHLCV market data.
        """
        pass

    def __str__(self):
        return self.name
        