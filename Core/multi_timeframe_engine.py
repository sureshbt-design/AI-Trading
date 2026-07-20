"""
multi_timeframe_engine.py

PATCC hierarchical multi-timeframe orchestration engine.

Default output is a compact operational table. Use --detail for the
full diagnostic report and --json for machine-readable output.

The underlying timeframe hierarchy and fusion methodology are unchanged.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from typing import Any, Iterable

from Core.asset_classifier import AssetClassifier
from Core.multi_timeframe_report_builder import (
    MultiTimeframeReportBuilder,
)
from Core.single_timeframe_analyzer import (
    SingleTimeframeAnalyzer,
    TimeframeAnalysis,
)
from Core.timeframe_fusion_engine import (
    FusionResult,
    TimeframeFusionEngine,
)


PROFILE_OVERRIDES = {
    "HYG": "etf",
    "URA": "etf",
    "URNM": "etf",
    "UNG": "etf",
}


@dataclass(frozen=True)
class TimeframeConfig:
    """Configuration for one hierarchical analysis layer."""

    key: str
    label: str
    role: str

    timeframe: str
    period: str
    interval: str

    calculate_targets: bool = False


TIMEFRAME_CONFIGS: tuple[TimeframeConfig, ...] = (
    TimeframeConfig(
        key="weekly",
        label="Weekly",
        role="Structural regime",
        timeframe="1wk",
        period="5y",
        interval="1wk",
    ),
    TimeframeConfig(
        key="daily",
        label="Daily",
        role="Swing direction",
        timeframe="1d",
        period="1y",
        interval="1d",
        calculate_targets=True,
    ),
    TimeframeConfig(
        key="hourly",
        label="60-Minute",
        role="Setup quality",
        timeframe="1h",
        period="60d",
        interval="60m",
    ),
    TimeframeConfig(
        key="setup",
        label="15-Minute",
        role="Entry confirmation",
        timeframe="15m",
        period="30d",
        interval="15m",
    ),
    TimeframeConfig(
        key="entry",
        label="5-Minute",
        role="Execution timing",
        timeframe="5m",
        period="5d",
        interval="5m",
    ),
)


class MultiTimeframeEngine:
    """Run PATCC analysis across all configured timeframes."""

    def __init__(
        self,
        analyzer: SingleTimeframeAnalyzer | None = None,
        fusion_engine: TimeframeFusionEngine | None = None,
        report_builder: MultiTimeframeReportBuilder | None = None,
    ) -> None:
        self.analyzer = (
            analyzer or SingleTimeframeAnalyzer()
        )

        self.fusion_engine = (
            fusion_engine or TimeframeFusionEngine()
        )

        self.report_builder = (
            report_builder or MultiTimeframeReportBuilder()
        )

    def run(
        self,
        *,
        ticker: str,
        profile: str,
        live_entry: bool = False,
    ) -> tuple[list[TimeframeAnalysis], FusionResult]:
        normalized_ticker = ticker.upper().strip()

        if not normalized_ticker:
            raise ValueError("Ticker cannot be empty.")

        analyses: list[TimeframeAnalysis] = []

        for config in TIMEFRAME_CONFIGS:
            allow_live_bar = (
                live_entry
                and config.key == "entry"
            )

            analysis = self.analyzer.analyze(
                ticker=normalized_ticker,
                profile=profile,
                key=config.key,
                label=config.label,
                role=config.role,
                timeframe=config.timeframe,
                period=config.period,
                interval=config.interval,
                benchmark_ticker="SPY",
                use_completed_bar=True,
                allow_live_bar=allow_live_bar,
                calculate_targets=config.calculate_targets,
            )

            analyses.append(analysis)

        fusion = self.fusion_engine.fuse(analyses)

        return analyses, fusion

    def build_report(
        self,
        *,
        ticker: str,
        profile: str,
        analyses: list[TimeframeAnalysis],
        fusion: FusionResult,
    ) -> str:
        return self.report_builder.build(
            ticker=ticker,
            profile=profile,
            analyses=analyses,
            fusion=fusion,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PATCC hierarchical multi-timeframe analysis engine"
        )
    )

    ticker_group = parser.add_mutually_exclusive_group()

    ticker_group.add_argument(
        "--ticker",
        default=None,
        help="Single ticker symbol. Default: SPY",
    )

    ticker_group.add_argument(
        "--tickers",
        default=None,
        help=(
            "Comma-separated ticker symbols, for example "
            "XLV,XLF,HYG."
        ),
    )

    parser.add_argument(
        "--profile",
        choices=[
            "stock",
            "etf",
            "leveraged_etf",
            "crypto",
            "index",
            "future",
            "currency",
        ],
        default=None,
        help=(
            "Optional profile override. PATCC automatically "
            "classifies the ticker when omitted."
        ),
    )

    parser.add_argument(
        "--live-entry",
        action="store_true",
        help=(
            "Use the current incomplete 5-minute bar as a "
            "provisional execution signal."
        ),
    )

    parser.add_argument(
        "--detail",
        action="store_true",
        help="Print the full multi-timeframe diagnostic report.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )

    return parser.parse_args()


def parse_tickers(args: argparse.Namespace) -> list[str]:
    raw = args.tickers or args.ticker or "SPY"

    tickers: list[str] = []

    for item in raw.split(","):
        normalized = item.upper().strip()

        if normalized and normalized not in tickers:
            tickers.append(normalized)

    if not tickers:
        raise SystemExit("At least one ticker is required.")

    return tickers


def resolve_profile(
    ticker: str,
    explicit_profile: str | None = None,
) -> str:
    if explicit_profile:
        return explicit_profile

    if ticker in PROFILE_OVERRIDES:
        return PROFILE_OVERRIDES[ticker]

    return AssetClassifier.classify(ticker).profile


def _safe_attr(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:
    return getattr(obj, name, default)


def _analysis_map(
    analyses: Iterable[TimeframeAnalysis],
) -> dict[str, TimeframeAnalysis]:
    result: dict[str, TimeframeAnalysis] = {}

    for analysis in analyses:
        key = str(
            _safe_attr(analysis, "key", "")
        ).lower()

        if key:
            result[key] = analysis

    return result


def _score(
    analysis: TimeframeAnalysis | None,
) -> int:
    if analysis is None:
        return 0

    direct = _safe_attr(
        analysis,
        "score",
        None,
    )

    if isinstance(direct, (int, float)):
        return int(direct)

    if direct is not None:
        nested = _safe_attr(
            direct,
            "overall_score",
            None,
        )
        if nested is not None:
            return int(nested)

    return int(
        _safe_attr(
            analysis,
            "patcc_score",
            0,
        )
        or 0
    )


def _footprint_classification(
    analysis: TimeframeAnalysis | None,
) -> str:
    if analysis is None:
        return "Unavailable"

    footprint = _safe_attr(
        analysis,
        "institutional_footprint",
        None,
    )

    if footprint is None:
        footprint = _safe_attr(
            analysis,
            "footprint",
            None,
        )

    if footprint is None:
        return "Unavailable"

    return str(
        _safe_attr(
            footprint,
            "classification",
            "Unavailable",
        )
    )


def _fusion_score(fusion: FusionResult) -> int:
    return int(
        _safe_attr(
            fusion,
            "fusion_score",
            _safe_attr(
                fusion,
                "score",
                0,
            ),
        )
        or 0
    )


def normalized_entry_status(
    analyses: list[TimeframeAnalysis],
    fusion: FusionResult,
) -> str:
    """
    Return a compact label derived directly from the authoritative
    TimeframeFusionEngine decision.
    """

    raw = str(
        _safe_attr(
            fusion,
            "entry_status",
            "Unavailable",
        )
    )

    if raw == "Entry Confirmed":
        return "QUALIFIED"

    if raw == "Wait - 60-Minute Confirmation":
        return "WAIT - 60m confirmation"

    if raw.startswith("Wait"):
        return "WAIT"

    if raw.startswith("Watch"):
        return "WATCH"

    if raw.startswith("Avoid"):
        return "AVOID"

    if raw.startswith("No New"):
        return "AVOID"

    return raw

def compact_row(
    ticker: str,
    analyses: list[TimeframeAnalysis],
    fusion: FusionResult,
) -> dict[str, Any]:
    mapping = _analysis_map(analyses)

    return {
        "ticker": ticker,
        "weekly": _score(mapping.get("weekly")),
        "daily": _score(mapping.get("daily")),
        "hourly": _score(mapping.get("hourly")),
        "setup": _score(mapping.get("setup")),
        "entry": _score(mapping.get("entry")),
        "fusion": _fusion_score(fusion),
        "alignment": str(
            _safe_attr(
                fusion,
                "alignment",
                "Unavailable",
            )
        ),
        "daily_flow": _footprint_classification(
            mapping.get("daily")
        ),
        "hourly_flow": _footprint_classification(
            mapping.get("hourly")
        ),
        "status": normalized_entry_status(
            analyses,
            fusion,
        ),
        "confidence": str(
            _safe_attr(
                fusion,
                "confidence",
                "Unavailable",
            )
        ),
    }


def build_compact_table(
    rows: Iterable[dict[str, Any]],
) -> str:
    rows = list(rows)

    output = [
        "PATCC MULTI-TIMEFRAME OPPORTUNITY TABLE",
        "-" * 121,
        (
            "Ticker  Wk  Day  60m  15m   5m  Fusion  "
            "Alignment              Daily Flow           "
            "60m Flow             Status"
        ),
        "-" * 121,
    ]

    for row in rows:
        output.append(
            f"{row['ticker']:<7}"
            f"{row['weekly']:>3} "
            f"{row['daily']:>4} "
            f"{row['hourly']:>4} "
            f"{row['setup']:>4} "
            f"{row['entry']:>4} "
            f"{row['fusion']:>7}  "
            f"{row['alignment']:<22.22} "
            f"{row['daily_flow']:<20.20} "
            f"{row['hourly_flow']:<20.20} "
            f"{row['status']}"
        )

    output.append("-" * 121)
    output.append(
        "WAIT = higher-timeframe candidate requiring setup or "
        "entry confirmation; AVOID = risk-control block."
    )

    return "\n".join(output)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if is_dataclass(value):
        return {
            key: _json_safe(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if hasattr(value, "__dict__"):
        return {
            key: _json_safe(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


def main() -> None:
    args = parse_args()
    tickers = parse_tickers(args)

    engine = MultiTimeframeEngine()

    results: list[
        tuple[
            str,
            str,
            list[TimeframeAnalysis],
            FusionResult,
        ]
    ] = []

    failures: list[dict[str, str]] = []

    for ticker in tickers:
        profile = resolve_profile(
            ticker,
            args.profile,
        )

        try:
            analyses, fusion = engine.run(
                ticker=ticker,
                profile=profile,
                live_entry=args.live_entry,
            )

            results.append(
                (
                    ticker,
                    profile,
                    analyses,
                    fusion,
                )
            )

        except KeyboardInterrupt:
            raise SystemExit(
                "\nAnalysis cancelled by user."
            )

        except Exception as exc:
            failures.append(
                {
                    "ticker": ticker,
                    "profile": profile,
                    "error": str(exc),
                }
            )

    if args.json:
        payload = {
            "results": [
                {
                    "ticker": ticker,
                    "profile": profile,
                    "summary": compact_row(
                        ticker,
                        analyses,
                        fusion,
                    ),
                    "analyses": _json_safe(analyses),
                    "fusion": _json_safe(fusion),
                }
                for ticker, profile, analyses, fusion
                in results
            ],
            "failures": failures,
        }

        print(
            json.dumps(
                payload,
                indent=2,
                default=str,
            )
        )
        return

    if args.detail:
        for index, (
            ticker,
            profile,
            analyses,
            fusion,
        ) in enumerate(results):
            if index:
                print("\n" + "=" * 79 + "\n")

            print(
                engine.build_report(
                    ticker=ticker,
                    profile=profile,
                    analyses=analyses,
                    fusion=fusion,
                )
            )
    else:
        if results:
            rows = [
                compact_row(
                    ticker,
                    analyses,
                    fusion,
                )
                for ticker, _, analyses, fusion
                in results
            ]
            print(build_compact_table(rows))

    if failures:
        print("")
        print("FAILED TICKERS")
        print("-" * 65)

        for failure in failures:
            print(
                f"{failure['ticker']}: "
                f"{failure['error']}"
            )

    if not results:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
