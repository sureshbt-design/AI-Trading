"""
watchlist_loader.py

PATCC Asset Universe and Watchlist Loader

Responsibilities
----------------
- Load asset-universe JSON configuration
- Validate required asset fields
- Return enabled assets
- Merge asset collections
- Remove duplicate ticker symbols
- Provide ticker lists to reporting modules

This module performs no market analysis, scoring, or data downloading.

Version: 0.1.0
"""

from __future__ import annotations

import argparse
import json

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WATCHLIST_DIR = PROJECT_ROOT / "Config" / "watchlists"
DEFAULT_UNIVERSE_FILE = WATCHLIST_DIR / "asset_classes.json"

REQUIRED_ASSET_FIELDS = {
    "ticker",
    "name",
    "asset_class",
    "category",
    "priority",
    "enabled",
    "source",
    "operational_profile",
    "intelligence",
}


class WatchlistError(Exception):
    """Raised when asset-universe configuration is invalid."""


@dataclass(frozen=True)
class AssetRecord:
    """Normalized PATCC asset-universe entry."""

    ticker: str
    name: str
    asset_class: str
    category: str
    priority: int
    enabled: bool
    source_type: str
    reason: str
    raw: dict[str, Any]


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Reject duplicate object keys while parsing JSON."""
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise WatchlistError(
                f"Duplicate JSON key detected: {key}"
            )

        result[key] = value

    return result


def load_json_file(path: Path) -> dict[str, Any]:
    """Load one JSON file with duplicate-key detection."""
    if not path.exists():
        raise WatchlistError(
            f"Watchlist file not found: {path}"
        )

    if not path.is_file():
        raise WatchlistError(
            f"Watchlist path is not a file: {path}"
        )

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WatchlistError(
            f"Unable to read {path}: {exc}"
        ) from exc

    if not text.strip():
        raise WatchlistError(
            f"Watchlist file is empty: {path}"
        )

    try:
        data = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except json.JSONDecodeError as exc:
        raise WatchlistError(
            f"Invalid JSON in {path}: "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise WatchlistError(
            f"Top-level JSON value must be an object: {path}"
        )

    return data


def validate_asset(
    asset: Any,
    position: int,
) -> AssetRecord:
    """Validate and normalize one asset entry."""
    if not isinstance(asset, dict):
        raise WatchlistError(
            f"Asset #{position} must be a JSON object."
        )

    missing_fields = REQUIRED_ASSET_FIELDS - asset.keys()

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))

        raise WatchlistError(
            f"Asset #{position} is missing fields: {missing}"
        )

    ticker = str(asset["ticker"]).strip().upper()

    if not ticker:
        raise WatchlistError(
            f"Asset #{position} has an empty ticker."
        )

    try:
        priority = int(asset["priority"])
    except (TypeError, ValueError) as exc:
        raise WatchlistError(
            f"{ticker}: priority must be an integer."
        ) from exc

    if priority < 1:
        raise WatchlistError(
            f"{ticker}: priority must be at least 1."
        )

    if not isinstance(asset["enabled"], bool):
        raise WatchlistError(
            f"{ticker}: enabled must be true or false."
        )

    source = asset["source"]

    if not isinstance(source, dict):
        raise WatchlistError(
            f"{ticker}: source must be an object."
        )

    source_type = str(
        source.get("type", "unknown")
    ).strip()

    reason = str(
        source.get("reason", "Not specified")
    ).strip()

    return AssetRecord(
        ticker=ticker,
        name=str(asset["name"]).strip(),
        asset_class=str(asset["asset_class"]).strip(),
        category=str(asset["category"]).strip(),
        priority=priority,
        enabled=asset["enabled"],
        source_type=source_type,
        reason=reason,
        raw=asset,
    )


def load_asset_universe(
    path: Path = DEFAULT_UNIVERSE_FILE,
) -> list[AssetRecord]:
    """Load and validate the PATCC core asset universe."""
    data = load_json_file(path)

    schema_version = data.get("schema_version")

    if schema_version != "1.0.0":
        raise WatchlistError(
            "Unsupported asset-universe schema version: "
            f"{schema_version!r}"
        )

    assets = data.get("assets")

    if not isinstance(assets, list):
        raise WatchlistError(
            "Asset-universe configuration must contain "
            "an 'assets' list."
        )

    records = [
        validate_asset(asset, position)
        for position, asset in enumerate(assets, start=1)
    ]

    return merge_assets([records])


def merge_assets(
    collections: Iterable[Iterable[AssetRecord]],
) -> list[AssetRecord]:
    """
    Merge asset collections and remove duplicate ticker symbols.

    When duplicates exist, the lowest numeric priority wins.
    """
    selected: dict[str, AssetRecord] = {}

    for collection in collections:
        for asset in collection:
            current = selected.get(asset.ticker)

            if current is None or asset.priority < current.priority:
                selected[asset.ticker] = asset

    return sorted(
        selected.values(),
        key=lambda item: (
            item.priority,
            item.asset_class,
            item.category,
            item.ticker,
        ),
    )


def get_enabled_assets(
    assets: Iterable[AssetRecord],
) -> list[AssetRecord]:
    """Return enabled assets only."""
    return [
        asset
        for asset in assets
        if asset.enabled
    ]


def get_tickers(
    assets: Iterable[AssetRecord],
) -> list[str]:
    """Return normalized ticker symbols."""
    return [
        asset.ticker
        for asset in assets
    ]


def filter_by_asset_class(
    assets: Iterable[AssetRecord],
    asset_classes: Iterable[str],
) -> list[AssetRecord]:
    """Return assets matching selected asset classes."""
    requested = {
        value.strip().casefold()
        for value in asset_classes
        if value.strip()
    }

    if not requested:
        return list(assets)

    return [
        asset
        for asset in assets
        if asset.asset_class.casefold() in requested
    ]


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate and inspect the PATCC asset universe."
    )

    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_UNIVERSE_FILE,
        help="Asset-universe JSON file.",
    )

    parser.add_argument(
        "--asset-class",
        nargs="+",
        default=[],
        help=(
            "Optional asset-class filters. "
            "Example: --asset-class Equity Commodity"
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Command-line validation and inspection entry point."""
    args = parse_arguments()

    try:
        assets = load_asset_universe(args.file)
        enabled = get_enabled_assets(assets)
        filtered = filter_by_asset_class(
            enabled,
            args.asset_class,
        )
    except WatchlistError as exc:
        print("=" * 72)
        print("PATCC ASSET UNIVERSE VALIDATION — FAILED")
        print("=" * 72)
        print(exc)
        return 1

    print("=" * 72)
    print("PATCC ASSET UNIVERSE LOADER v0.1")
    print("=" * 72)
    print(f"Configuration : {args.file}")
    print(f"Total assets  : {len(assets)}")
    print(f"Enabled assets: {len(enabled)}")
    print(f"Selected      : {len(filtered)}")
    print("-" * 72)

    for asset in filtered:
        print(
            f"{asset.ticker:<10}"
            f"{asset.asset_class:<18}"
            f"{asset.category:<30}"
            f"Priority {asset.priority}"
        )

    print("=" * 72)
    print("Asset universe validation PASSED.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
