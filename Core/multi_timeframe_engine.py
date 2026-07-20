"""
multi_timeframe_engine.py

PATCC hierarchical multi-timeframe orchestration engine.

This module coordinates five independent timeframe analyses and sends
their results to the TimeframeFusionEngine.

Hierarchy
---------
Weekly       Structural regime
Daily        Swing direction
60-minute    Setup quality
15-minute    Entry confirmation
5-minute     Execution timing
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

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


@dataclass(frozen=True)
class TimeframeConfig:
    """
    Configuration for one hierarchical analysis layer.
    """

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
    """
    Run PATCC analysis across all configured timeframes.
    """

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
        """
        Analyze every configured timeframe and fuse the results.

        Parameters
        ----------
        ticker:
            Symbol to analyze.

        profile:
            PATCC asset profile.

        live_entry:
            When True, the current incomplete 5-minute bar may be
            included as a provisional execution signal.

        Returns
        -------
        tuple
            List of TimeframeAnalysis objects and one FusionResult.
        """

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
        """
        Build the final hierarchical console report.
        """

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

    parser.add_argument(
        "--ticker",
        default="SPY",
        help="Ticker symbol to analyze. Default: SPY",
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

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ticker = args.ticker.upper().strip()

    if not ticker:
        raise SystemExit("Ticker cannot be empty.")

    asset_info = AssetClassifier.classify(ticker)
    profile = args.profile or asset_info.profile

    engine = MultiTimeframeEngine()

    try:
        analyses, fusion = engine.run(
            ticker=ticker,
            profile=profile,
            live_entry=args.live_entry,
        )

        report = engine.build_report(
            ticker=ticker,
            profile=profile,
            analyses=analyses,
            fusion=fusion,
        )

        print(report)

    except KeyboardInterrupt:
        raise SystemExit(
            "\nAnalysis cancelled by user."
        )

    except Exception as exc:
        print("=" * 79)
        print("PATCC MULTI-TIMEFRAME ANALYSIS FAILED")
        print("=" * 79)
        print(f"Ticker              : {ticker}")
        print(f"Profile             : {profile}")
        print(f"Error               : {exc}")
        print("")
        print(
            "Review the exception, data availability, and timeframe "
            "configuration before changing scoring thresholds."
        )

        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
    