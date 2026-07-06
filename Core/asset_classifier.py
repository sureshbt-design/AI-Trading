"""
asset_classifier.py

Classifies a ticker into one of the supported asset types.
"""

from pathlib import Path
from typing import Dict, Set


class AssetClassifier:
    """Classify a ticker based on universe files."""

    def __init__(self, universes_path: Path | None = None):
        if universes_path is None:
            universes_path = Path(__file__).parent / "universes"

        self.universes_path = universes_path
        self.lookup: Dict[str, Set[str]] = {}

        self._load_universes()

    def _load_universes(self):
        """Load every *.txt file under Core/universes."""

        if not self.universes_path.exists():
            return

        for file in self.universes_path.glob("*.txt"):
            symbols = set()

            for line in file.read_text().splitlines():
                line = line.strip().upper()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                symbols.add(line)

            self.lookup[file.stem.lower()] = symbols

    def classify(self, ticker: str) -> str:
        """Return the asset class for a ticker."""

        ticker = ticker.upper()

        if ticker in self.lookup.get("leveraged", set()):
            return "leveraged_etf"

        if ticker in self.lookup.get("etfs", set()):
            return "etf"

        return "stock"

    def is_leveraged(self, ticker: str) -> bool:
        return self.classify(ticker) == "leveraged_etf"

    def is_etf(self, ticker: str) -> bool:
        return self.classify(ticker) in (
            "etf",
            "leveraged_etf",
        )


if __name__ == "__main__":

    classifier = AssetClassifier()

    tests = [
        "AAPL",
        "SPY",
        "QQQ",
        "TQQQ",
        "SOXL",
        "NVDL",
        "TSLA",
        "MSFT",
    ]

    for ticker in tests:
        print(f"{ticker:6} -> {classifier.classify(ticker)}")
        