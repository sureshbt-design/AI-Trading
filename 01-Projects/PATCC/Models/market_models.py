"""
PATCC Market Data Models
"""

from dataclasses import dataclass
import pandas as pd


@dataclass
class MarketData:
    symbol: str
    provider: str
    period: str
    interval: str
    data: pd.DataFrame
    