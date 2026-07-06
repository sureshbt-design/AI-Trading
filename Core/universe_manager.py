"""
universe_manager.py

Loads ticker universes from Core/universes/*.txt.
"""

from pathlib import Path
from typing import Dict, List


class UniverseManager:
    """Manage ticker universe files."""

    def __init__(self, universes_path: Path | None = None):
        if universes_path is None:
            universes_path = Path(__file__).parent / "universes"

        self.universes_path = universes_path
        self._cache: Dict[str, List[str]] = {}

    def available_universes(self) -> List[str]:
        """Return available universe names."""
        if not self.universes_path.exists():
            return []

        return sorted(file.stem for file in self.universes_path.glob("*.txt"))

    def load(self, name: str) -> List[str]:
        """Load one universe by file stem name."""
        name = name.lower().strip()

        if name in self._cache:
            return self._cache[name]

        file_path = self.universes_path / f"{name}.txt"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Universe '{name}' not found at {file_path}"
            )

        symbols = []

        for line in file_path.read_text().splitlines():
            ticker = line.strip().upper()

            if not ticker or ticker.startswith("#"):
                continue

            if self._is_valid_ticker(ticker):
                symbols.append(ticker)

        unique_sorted = sorted(set(symbols))
        self._cache[name] = unique_sorted
        return unique_sorted

    def load_many(self, names: List[str]) -> List[str]:
        """Load and combine multiple universes."""
        combined = []

        for name in names:
            combined.extend(self.load(name))

        return sorted(set(combined))

    def _is_valid_ticker(self, ticker: str) -> bool:
        """Basic ticker validation."""
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
        return bool(ticker) and all(char in allowed_chars for char in ticker)


if __name__ == "__main__":
    manager = UniverseManager()

    print("Available universes:")
    print(manager.available_universes())

    print("\nLeveraged universe:")
    print(manager.load("leveraged"))

    print("\nCombined ETF + leveraged universe:")
    print(manager.load_many(["etfs", "leveraged"]))
    