"""
asset_classifier.py

Asset classification layer for PATCC.

This module identifies the broad asset type and trading profile
for common stocks, ETFs, leveraged ETFs, crypto assets, futures,
indexes, and currency instruments.

The initial version uses transparent symbol rules and curated lists.
Later versions may enrich classifications with provider metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class AssetInfo:
    ticker: str
    asset_type: str
    profile: str
    category: str
    leverage: int
    underlying: str | None
    trading_hours: str
    market: str


class AssetClassifier:
    """
    Classify instruments using deterministic symbol rules.

    The classifier is intentionally conservative:
    when no special rule matches, the instrument is treated as a stock.
    """

    _LEVERAGED_ETFS: Dict[str, tuple[int, str]] = {
        "TQQQ": (3, "QQQ"),
        "SQQQ": (-3, "QQQ"),
        "SOXL": (3, "SOXX"),
        "SOXS": (-3, "SOXX"),
        "UPRO": (3, "SPY"),
        "SPXU": (-3, "SPY"),
        "UDOW": (3, "DIA"),
        "SDOW": (-3, "DIA"),
        "TNA": (3, "IWM"),
        "TZA": (-3, "IWM"),
        "FAS": (3, "XLF"),
        "FAZ": (-3, "XLF"),
        "LABU": (3, "XBI"),
        "LABD": (-3, "XBI"),
        "NUGT": (2, "GDX"),
        "DUST": (-2, "GDX"),
        "JNUG": (2, "GDXJ"),
        "JDST": (-2, "GDXJ"),
        "GUSH": (2, "XOP"),
        "DRIP": (-2, "XOP"),
        "UCO": (2, "USO"),
        "SCO": (-2, "USO"),
        "BOIL": (2, "UNG"),
        "KOLD": (-2, "UNG"),
        "FNGU": (3, "FANG+"),
        "FNGD": (-3, "FANG+"),
    }

    _KNOWN_ETFS: Set[str] = {
        "SPY",
        "QQQ",
        "DIA",
        "IWM",
        "VTI",
        "VOO",
        "VT",
        "VXUS",
        "SCHD",
        "JEPI",
        "JEPQ",
        "TLT",
        "IEF",
        "SHY",
        "BND",
        "GLD",
        "SLV",
        "USO",
        "UNG",
        "XLE",
        "XLF",
        "XLK",
        "XLV",
        "XLI",
        "XLP",
        "XLY",
        "XLU",
        "XLB",
        "XLRE",
        "SOXX",
        "SMH",
        "ARKK",
        "DBMF",
        "CTA",
        "CAOS",
        "FTLS",
    }

    _INDEX_SYMBOLS: Set[str] = {
        "^GSPC",
        "^NDX",
        "^DJI",
        "^RUT",
        "^VIX",
        "^IXIC",
    }

    _CURRENCY_INDEX_SYMBOLS: Set[str] = {
        "DX-Y.NYB",
        "^DXY",
    }

    @classmethod
    def classify(cls, ticker: str) -> AssetInfo:
        """
        Return classification information for a ticker.
        """

        normalized = cls._normalize(ticker)

        if normalized in cls._LEVERAGED_ETFS:
            leverage, underlying = cls._LEVERAGED_ETFS[normalized]

            return AssetInfo(
                ticker=normalized,
                asset_type="leveraged_etf",
                profile="leveraged_etf",
                category="Leveraged or inverse ETF",
                leverage=leverage,
                underlying=underlying,
                trading_hours="Regular and extended US market hours",
                market="US",
            )

        if cls._is_crypto(normalized):
            return AssetInfo(
                ticker=normalized,
                asset_type="crypto",
                profile="crypto",
                category="Cryptocurrency",
                leverage=1,
                underlying=None,
                trading_hours="24x7",
                market="Global",
            )

        if normalized in cls._INDEX_SYMBOLS:
            return AssetInfo(
                ticker=normalized,
                asset_type="index",
                profile="index",
                category="Market index",
                leverage=1,
                underlying=None,
                trading_hours="Index-dependent market hours",
                market="US",
            )

        if normalized in cls._CURRENCY_INDEX_SYMBOLS:
            return AssetInfo(
                ticker=normalized,
                asset_type="currency_index",
                profile="currency",
                category="Currency index",
                leverage=1,
                underlying=None,
                trading_hours="Extended global market hours",
                market="Global",
            )

        if cls._is_future(normalized):
            return AssetInfo(
                ticker=normalized,
                asset_type="future",
                profile="future",
                category="Futures contract",
                leverage=1,
                underlying=None,
                trading_hours="Contract-dependent extended hours",
                market="Global",
            )

        if normalized in cls._KNOWN_ETFS:
            return AssetInfo(
                ticker=normalized,
                asset_type="etf",
                profile="etf",
                category=cls._etf_category(normalized),
                leverage=1,
                underlying=None,
                trading_hours="Regular and extended US market hours",
                market="US",
            )

        return AssetInfo(
            ticker=normalized,
            asset_type="stock",
            profile="stock",
            category="Common stock or unclassified equity",
            leverage=1,
            underlying=None,
            trading_hours="Regular and extended US market hours",
            market="US",
        )

    @staticmethod
    def _normalize(ticker: str) -> str:
        if ticker is None:
            raise ValueError("Ticker cannot be None.")

        normalized = ticker.strip().upper()

        if not normalized:
            raise ValueError("Ticker cannot be empty.")

        return normalized

    @staticmethod
    def _is_crypto(ticker: str) -> bool:
        crypto_quotes = ("-USD", "-USDT", "-EUR", "-BTC")

        return ticker.endswith(crypto_quotes)

    @staticmethod
    def _is_future(ticker: str) -> bool:
        return ticker.endswith("=F")

    @staticmethod
    def _etf_category(ticker: str) -> str:
        categories = {
            "SPY": "Broad-market equity ETF",
            "QQQ": "Technology-heavy equity ETF",
            "DIA": "Large-cap equity ETF",
            "IWM": "Small-cap equity ETF",
            "TLT": "Long-duration Treasury ETF",
            "IEF": "Intermediate Treasury ETF",
            "GLD": "Gold commodity ETF",
            "SLV": "Silver commodity ETF",
            "USO": "Crude-oil commodity ETF",
            "UNG": "Natural-gas commodity ETF",
            "DBMF": "Managed-futures ETF",
            "CTA": "Managed-futures ETF",
            "CAOS": "Tail-risk ETF",
            "FTLS": "Long-short equity ETF",
        }

        return categories.get(ticker, "Exchange-traded fund")

    @classmethod
    def describe(cls, ticker: str) -> str:
        """
        Return a readable asset-classification report.
        """

        info = cls.classify(ticker)

        leverage_text = (
            f"{info.leverage}x"
            if info.leverage != 1
            else "Unleveraged"
        )

        return (
            f"Ticker: {info.ticker}\n"
            f"Asset type: {info.asset_type}\n"
            f"Profile: {info.profile}\n"
            f"Category: {info.category}\n"
            f"Leverage: {leverage_text}\n"
            f"Underlying: {info.underlying or 'N/A'}\n"
            f"Trading hours: {info.trading_hours}\n"
            f"Market: {info.market}"
        )


def main() -> None:
    """
    Command-line smoke test.
    """

    import argparse

    parser = argparse.ArgumentParser(
        description="Classify a PATCC ticker or symbol."
    )

    parser.add_argument(
        "ticker",
        help="Ticker such as MSFT, QQQ, TQQQ, BTC-USD, ^GSPC, or GC=F.",
    )

    args = parser.parse_args()

    try:
        print(AssetClassifier.describe(args.ticker))
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
    