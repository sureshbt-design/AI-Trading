"""
PATCC Universe Manager
Version 1.0
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Universe:
    name: str
    symbols: List[str]


class UniverseManager:

    def __init__(self):

        self.universes: Dict[str, Universe] = {}

        self._load_default_universes()

    def _load_default_universes(self):

        self.universes["day_trading"] = Universe(
            "Day Trading",
            [
                "AAPL",
                "MSFT",
                "NVDA",
                "AMD",
                "META",
                "AMZN",
                "AVGO",
                "TSLA",
                "PLTR",
                "MSTR",
                "COIN"
            ]
        )

        self.universes["swing"] = Universe(
            "Swing Trading",
            [
                "AAPL",
                "MSFT",
                "NVDA",
                "META",
                "AMZN",
                "GOOGL",
                "NFLX",
                "MU"
            ]
        )

        self.universes["etf"] = Universe(
            "ETF",
            [
                "SPY",
                "QQQ",
                "SMH",
                "XLK",
                "XLF",
                "XLE",
                "IBIT",
                "SOXL",
                "TQQQ"
            ]
        )

        self.universes["index"] = Universe(
            "Indexes",
            [
                "SPY",
                "QQQ",
                "DIA",
                "IWM"
            ]
        )

    def get_universe_names(self):

        return list(self.universes.keys())

    def get_universe(self, name):

        return self.universes.get(name)

    def list_all(self):

        for key, universe in self.universes.items():

            print(f"\n{universe.name}")

            print("-" * len(universe.name))

            for symbol in universe.symbols:
                print(symbol)
