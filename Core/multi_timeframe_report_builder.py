"""
multi_timeframe_report_builder.py

Console report builder for PATCC hierarchical multi-timeframe analysis.
"""

from __future__ import annotations

from typing import Iterable

from Core.version import (
    BUILD_DATE,
    PATCC_VERSION,
    PROJECT_DESCRIPTION,
    PROJECT_NAME,
)


class MultiTimeframeReportBuilder:
    """
    Build the hierarchical PATCC console report.
    """

    WIDTH = 79
    SECTION_WIDTH = 69

    def build(
        self,
        *,
        ticker: str,
        profile: str,
        analyses: Iterable,
        fusion,
    ) -> str:
        analyses = list(analyses)

        lines: list[str] = []

        lines.append("=" * self.WIDTH)
        lines.append(
            f"{PROJECT_NAME} - {PROJECT_DESCRIPTION}"
        )
        lines.append(f"Version             : {PATCC_VERSION}")
        lines.append(f"Build Date          : {BUILD_DATE}")
        lines.append("=" * self.WIDTH)

        lines.append(f"Ticker              : {ticker}")
        lines.append(f"Profile             : {profile}")
        lines.append(
            "Analysis Model      : Hierarchical Multi-Timeframe"
        )
        lines.append("")

        lines.extend(
            self._build_executive_summary(fusion)
        )

        lines.extend(
            self._build_timeframe_matrix(analyses)
        )

        lines.extend(
            self._build_diagnostics(analyses)
        )

        lines.extend(
            self._build_daily_targets(analyses)
        )

        lines.extend(
            self._build_decision_reasons(fusion)
        )

        return "\n".join(lines)

    def _build_executive_summary(
        self,
        fusion,
    ) -> list[str]:
        return [
            "MULTI-TIMEFRAME DECISION",
            "-" * self.SECTION_WIDTH,
            f"Swing Bias          : {fusion.swing_bias}",
            f"Trend Alignment     : {fusion.alignment}",
            f"Entry Status        : {fusion.entry_status}",
            (
                f"Position Guidance   : "
                f"{fusion.position_guidance}"
            ),
            "",
            f"Fusion Score        : {fusion.fusion_score}/100",
            f"Confidence          : {fusion.confidence}",
            f"Decision State      : {fusion.decision_state}",
            "",
        ]

    def _build_timeframe_matrix(
        self,
        analyses: list,
    ) -> list[str]:
        lines = [
            "TIMEFRAME MATRIX",
            "-" * self.SECTION_WIDTH,
            (
                f"{'Timeframe':<13}"
                f"{'Role':<20}"
                f"{'Trend':<18}"
                f"{'Score':>7}"
                f"{'Bar':>11}"
            ),
            "-" * self.SECTION_WIDTH,
        ]

        for analysis in analyses:
            trend = analysis.market_state.trend
            score = analysis.score.overall_score

            bar_status = (
                "LIVE"
                if analysis.bar_validation.provisional
                else "CLOSED"
            )

            lines.append(
                f"{analysis.label:<13}"
                f"{analysis.role:<20}"
                f"{trend:<18}"
                f"{score:>7}"
                f"{bar_status:>11}"
            )

        lines.append("")

        return lines

    def _build_diagnostics(
        self,
        analyses: list,
    ) -> list[str]:
        lines = [
            "TIMEFRAME DIAGNOSTICS",
            "-" * self.SECTION_WIDTH,
        ]

        for analysis in analyses:
            state = analysis.market_state
            indicators = analysis.indicators
            footprint = analysis.institutional_footprint
            validation = analysis.bar_validation

            relative_strength = (
                f"{footprint.relative_strength_20d:+.2f}%"
                if footprint.relative_strength_20d is not None
                else "Unavailable"
            )

            lines.extend(
                [
                    (
                        f"{analysis.label.upper()} "
                        f"- {analysis.role}"
                    ),
                    (
                        f"  Data               : "
                        f"{analysis.period} / "
                        f"{analysis.interval}"
                    ),
                    (
                        f"  Analysis Bar       : "
                        f"{validation.analysis_bar}"
                    ),
                    (
                        f"  Bar Status         : "
                        f"{validation.status}"
                    ),
                    (
                        f"  Trend              : "
                        f"{state.trend}"
                    ),
                    (
                        f"  Momentum           : "
                        f"{state.momentum}"
                    ),
                    (
                        f"  Volatility         : "
                        f"{state.volatility}"
                    ),
                    (
                        f"  Volume             : "
                        f"{state.volume}"
                    ),
                    (
                        f"  Market Bias        : "
                        f"{state.market_bias}"
                    ),
                    (
                        f"  Risk Level         : "
                        f"{state.risk_level}"
                    ),
                    (
                        f"  PATCC Score        : "
                        f"{analysis.score.overall_score}/100 "
                        f"({analysis.score.grade})"
                    ),
                    (
                        f"  Footprint          : "
                        f"{footprint.score}/100 - "
                        f"{footprint.classification}"
                    ),
                    (
                        f"  DEMA-8             : "
                        f"{footprint.price_vs_dema8}, "
                        f"{footprint.dema8_slope}"
                    ),
                    (
                        f"  VWAP-20            : "
                        f"{footprint.price_vs_vwap20}"
                    ),
                    (
                        f"  RVOL               : "
                        f"{indicators.rvol:.2f}"
                    ),
                    (
                        f"  CMF-20             : "
                        f"{indicators.cmf20:+.3f}"
                    ),
                    (
                        f"  MFI-14             : "
                        f"{indicators.mfi14:.1f}"
                    ),
                    (
                        f"  RS vs SPY          : "
                        f"{relative_strength}"
                    ),
                    (
                        f"  Validation         : "
                        f"{validation.note}"
                    ),
                    "",
                ]
            )

        return lines

    def _build_daily_targets(
        self,
        analyses: list,
    ) -> list[str]:
        daily = next(
            (
                analysis
                for analysis in analyses
                if analysis.key == "daily"
            ),
            None,
        )

        if daily is None or daily.targets is None:
            return []

        targets = daily.targets

        return [
            "DAILY SWING REFERENCE LEVELS",
            "-" * self.SECTION_WIDTH,
            (
                f"Current Price       : "
                f"{targets.current_price:.2f}"
            ),
            (
                f"Support             : "
                f"{targets.support:.2f}"
            ),
            (
                f"Resistance          : "
                f"{targets.resistance:.2f}"
            ),
            (
                f"Target 1            : "
                f"{targets.target_1:.2f}"
            ),
            (
                f"Target 2            : "
                f"{targets.target_2:.2f}"
            ),
            (
                f"Target 3            : "
                f"{targets.target_3:.2f}"
            ),
            (
                f"Stop Loss           : "
                f"{targets.stop_loss:.2f}"
            ),
            "",
        ]

    def _build_decision_reasons(
        self,
        fusion,
    ) -> list[str]:
        lines = [
            "DECISION RATIONALE",
            "-" * self.SECTION_WIDTH,
        ]

        for index, reason in enumerate(
            fusion.reasons,
            start=1,
        ):
            lines.append(f"{index}. {reason}")

        if fusion.warnings:
            lines.extend(
                [
                    "",
                    "WARNINGS",
                    "-" * self.SECTION_WIDTH,
                ]
            )

            for warning in fusion.warnings:
                lines.append(f"- {warning}")

        lines.append("")

        return lines
        