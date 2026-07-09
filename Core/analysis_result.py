"""
analysis_result.py

Unified analysis result object for one ticker.
"""

from dataclasses import dataclass
from typing import Any

from Core.market_data_service import MarketDataResponse


@dataclass
class AnalysisResult:
    ticker: str
    profile: str

    # Market data
    market_data: MarketDataResponse

    # Analysis modules
    indicators: Any
    market_state: Any
    score: Any
    targets: Any

    # Market structure
    market_trend: str = "Unknown"
    market_structure: str = ""
    market_event: str = ""
    market_confidence: int = 0
    