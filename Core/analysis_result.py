"""
analysis_result.py

Unified analysis result object for one ticker.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class AnalysisResult:
    ticker: str
    profile: str
    market_data: Any
    indicators: Any
    market_state: Any
    score: Any
    targets: Any
    