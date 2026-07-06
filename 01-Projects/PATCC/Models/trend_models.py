"""
PATCC Trend Models
"""

from dataclasses import dataclass
from typing import List


@dataclass
class TrendSignal:
    direction: str
    strength: str
    score: int
    reasons: List[str]
    