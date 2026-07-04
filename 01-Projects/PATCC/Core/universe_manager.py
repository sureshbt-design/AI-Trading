"""
PATCC Universe Manager
Version 2.0

Loads watchlists from JSON files.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class Universe:
    name: str
    market: str
    asset_class: str
    provider: str
    scan_frequency: str
    symbols: List[str]


class UniverseManager:

    def __init__(self):
        self.watchlist_dir = Path("01-Projects/PATCC/Data/Watchlists")
        self.universes: Dict[str, Universe] = {}
        self.load_watchlists()

    def load_watchlists(self):
        for file_path in self.watchlist_dir.glob("*.json"):
            with open(file_path, "r") as file:
                data = json.load(file)

            key = file_path.stem

            self.universes[key] = Universe(
                name=data["name"],
                market=data["market"],
                asset_class=data["asset_class"],
                provider=data["provider"],
                scan_frequency=data["scan_frequency"],
                symbols=data["symbols"],
            )

    def get_universe_names(self):
        return list(self.universes.keys())

    def get_universe(self, name):
        return self.universes.get(name)

    def list_all(self):
        for key, universe in self.universes.items():
            print(f"\n{universe.name}")
            print("-" * len(universe.name))
            print(f"Market        : {universe.market}")
            print(f"Asset Class   : {universe.asset_class}")
            print(f"Provider      : {universe.provider}")
            print(f"Scan Frequency: {universe.scan_frequency}")
            print("Symbols:")
            for symbol in universe.symbols:
                print(f"  - {symbol}")
