"""
PATCC Universe Models

Shared data models for watchlists and universes.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Universe:
    name: str
    market: str
    asset_class: str
    provider: str
    scan_frequency: str
    symbols: List[str]
    