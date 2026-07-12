"""
watchlist_builder.py

PATCC Dynamic Watchlist Builder

Responsibilities
----------------
- Load the PATCC Asset Universe
- Convert assets into watchlist candidates
- Apply operational priority rules
- Preserve selected and excluded candidates
- Explain why each asset is included or excluded
- Produce grouped watchlist metadata

Priority meaning
----------------
P1 = Mandatory market context; always selected
P2 = Strategic monitoring; selected by default
P3 = Tactical opportunity; selected only when policy permits
P4+ = Research / low urgency; excluded by default

Priority is not an investment score.

Version: 0.3.0
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from zoneinfo import ZoneInfo

from Core.watchlist_loader import (
    AssetRecord,
    get_enabled_assets,
    load_asset_universe,
)


EASTERN_TIME = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class WatchlistCandidate:
    """Asset evaluated for inclusion in today's watchlist."""

    asset: AssetRecord
    selected: bool
    selection_reason: str
    market_role: str

    @property
    def ticker(self) -> str:
        return self.asset.ticker

    @property
    def priority(self) -> int:
        return self.asset.priority


@dataclass(frozen=True)
class WatchlistCategory:
    """One category within an asset class."""

    category: str
    candidates: List[WatchlistCandidate]


@dataclass(frozen=True)
class WatchlistGroup:
    """One asset-class group containing categories."""

    asset_class: str
    categories: List[WatchlistCategory]


@dataclass(frozen=True)
class WatchlistResult:
    """Complete watchlist result with selected and excluded assets."""

    generated_at_et: str
    total_assets: int
    selected_assets: int
    excluded_assets: int
    asset_class_count: int
    category_count: int
    groups: List[WatchlistGroup]


class WatchlistBuilder:
    """Build today's structured PATCC watchlist."""

    def __init__(
        self,
        include_tactical: bool = True,
        maximum_priority: int = 3,
    ) -> None:
        universe = load_asset_universe()
        self.assets = get_enabled_assets(universe)
        self.include_tactical = include_tactical
        self.maximum_priority = maximum_priority

    @staticmethod
    def determine_market_role(asset: AssetRecord) -> str:
        """Infer the operational role from asset metadata."""
        category = asset.category.casefold()
        asset_class = asset.asset_class.casefold()

        if "benchmark" in category:
            return "Market Context"

        if "sector" in category:
            return "Sector Monitor"

        if "treasury bill" in category:
            return "Cash / Defensive"

        if "treasury" in category:
            return "Rates / Defensive"

        if "high-yield" in category:
            return "Credit Risk Sensor"

        if "precious metals" in category:
            return "Diversifier / Hedge"

        if "energy commodity" in category:
            return "Inflation / Commodity Monitor"

        if "leveraged inverse" in category:
            return "Tactical Hedge"

        if "leveraged long" in category:
            return "Tactical Risk-On"

        if asset_class == "crypto":
            return "Digital Asset Monitor"

        return "Strategic Monitor"

    def evaluate_asset(
        self,
        asset: AssetRecord,
    ) -> WatchlistCandidate:
        """
        Apply version 0.3 operational selection rules.

        Market intelligence will replace some of these rules later.
        """
        role = self.determine_market_role(asset)

        if asset.priority == 1:
            return WatchlistCandidate(
                asset=asset,
                selected=True,
                selection_reason=(
                    "P1 mandatory market-context asset."
                ),
                market_role=role,
            )

        if asset.priority == 2:
            return WatchlistCandidate(
                asset=asset,
                selected=True,
                selection_reason=(
                    "P2 strategic monitoring asset."
                ),
                market_role=role,
            )

        if asset.priority == 3:
            if self.include_tactical:
                return WatchlistCandidate(
                    asset=asset,
                    selected=True,
                    selection_reason=(
                        "P3 tactical asset included by current policy."
                    ),
                    market_role=role,
                )

            return WatchlistCandidate(
                asset=asset,
                selected=False,
                selection_reason=(
                    "P3 tactical asset excluded because "
                    "tactical scanning is disabled."
                ),
                market_role=role,
            )

        if asset.priority <= self.maximum_priority:
            return WatchlistCandidate(
                asset=asset,
                selected=True,
                selection_reason=(
                    f"P{asset.priority} included within configured "
                    "maximum priority."
                ),
                market_role=role,
            )

        return WatchlistCandidate(
            asset=asset,
            selected=False,
            selection_reason=(
                f"P{asset.priority} exceeds configured maximum "
                f"priority P{self.maximum_priority}."
            ),
            market_role=role,
        )

    def build_candidates(self) -> List[WatchlistCandidate]:
        """Evaluate every enabled asset."""
        candidates = [
            self.evaluate_asset(asset)
            for asset in self.assets
        ]

        return sorted(
            candidates,
            key=lambda item: (
                item.priority,
                item.asset.asset_class,
                item.asset.category,
                item.ticker,
            ),
        )

    def group_candidates(
        self,
        candidates: List[WatchlistCandidate],
    ) -> Dict[str, Dict[str, List[WatchlistCandidate]]]:
        """Group candidates by asset class and category."""
        groups: Dict[
            str,
            Dict[str, List[WatchlistCandidate]],
        ] = defaultdict(lambda: defaultdict(list))

        for candidate in candidates:
            asset = candidate.asset
            groups[asset.asset_class][asset.category].append(candidate)

        return {
            asset_class: dict(categories)
            for asset_class, categories in groups.items()
        }

    def build_watchlist(self) -> WatchlistResult:
        """Build the complete structured watchlist result."""
        candidates = self.build_candidates()
        grouped = self.group_candidates(candidates)

        watchlist_groups: List[WatchlistGroup] = []
        category_count = 0

        for asset_class in sorted(grouped):
            categories: List[WatchlistCategory] = []

            for category in sorted(grouped[asset_class]):
                category_candidates = grouped[asset_class][category]

                categories.append(
                    WatchlistCategory(
                        category=category,
                        candidates=category_candidates,
                    )
                )
                category_count += 1

            watchlist_groups.append(
                WatchlistGroup(
                    asset_class=asset_class,
                    categories=categories,
                )
            )

        selected_count = sum(
            1 for candidate in candidates if candidate.selected
        )

        now_et = datetime.now(EASTERN_TIME)

        return WatchlistResult(
            generated_at_et=now_et.strftime(
                "%Y-%m-%d %I:%M:%S %p ET"
            ),
            total_assets=len(candidates),
            selected_assets=selected_count,
            excluded_assets=len(candidates) - selected_count,
            asset_class_count=len(watchlist_groups),
            category_count=category_count,
            groups=watchlist_groups,
        )

    def get_selected_candidates(self) -> List[WatchlistCandidate]:
        """Return selected candidates only."""
        return [
            candidate
            for candidate in self.build_candidates()
            if candidate.selected
        ]

    def get_selected_tickers(self) -> List[str]:
        """Return selected ticker symbols for Morning Report."""
        return [
            candidate.ticker
            for candidate in self.get_selected_candidates()
        ]

    def summary(self) -> dict:
        """Return builder summary statistics."""
        result = self.build_watchlist()

        priority_counts: Dict[str, int] = defaultdict(int)
        role_counts: Dict[str, int] = defaultdict(int)

        for candidate in self.build_candidates():
            priority_counts[f"P{candidate.priority}"] += 1
            role_counts[candidate.market_role] += 1

        return {
            "generated_at_et": result.generated_at_et,
            "total_assets": result.total_assets,
            "selected_assets": result.selected_assets,
            "excluded_assets": result.excluded_assets,
            "asset_classes": result.asset_class_count,
            "categories": result.category_count,
            "priority_counts": dict(priority_counts),
            "role_counts": dict(role_counts),
        }


def print_watchlist(builder: WatchlistBuilder) -> None:
    """Print selected and excluded watchlist candidates."""
    result = builder.build_watchlist()

    print("=" * 78)
    print("PATCC DYNAMIC WATCHLIST v0.3")
    print("=" * 78)
    print(f"Generated       : {result.generated_at_et}")
    print(f"Total assets    : {result.total_assets}")
    print(f"Selected assets : {result.selected_assets}")
    print(f"Excluded assets : {result.excluded_assets}")
    print(f"Asset classes   : {result.asset_class_count}")
    print(f"Categories      : {result.category_count}")
    print("=" * 78)

    for group in result.groups:
        print()
        print(group.asset_class.upper())
        print("=" * len(group.asset_class))

        for category in group.categories:
            print()
            print(category.category)
            print("-" * len(category.category))

            for candidate in category.candidates:
                status = "SELECTED" if candidate.selected else "EXCLUDED"

                print(
                    f"{candidate.ticker:<10}"
                    f"P{candidate.priority:<3}"
                    f"{status:<11}"
                    f"{candidate.market_role:<24}"
                    f"{candidate.selection_reason}"
                )

    summary = builder.summary()

    print()
    print("=" * 78)
    print("PRIORITY SUMMARY")
    print("-" * 78)

    for priority, count in sorted(
        summary["priority_counts"].items()
    ):
        print(f"{priority:<8}{count:>4}")

    print()
    print("MARKET ROLE SUMMARY")
    print("-" * 78)

    for role, count in sorted(
        summary["role_counts"].items()
    ):
        print(f"{role:<30}{count:>4}")

    print("=" * 78)


def main() -> int:
    """Command-line entry point."""
    builder = WatchlistBuilder(
        include_tactical=True,
        maximum_priority=3,
    )

    print_watchlist(builder)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    