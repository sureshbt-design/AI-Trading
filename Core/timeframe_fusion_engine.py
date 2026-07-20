"""
timeframe_fusion_engine.py

Decision-fusion logic for PATCC hierarchical multi-timeframe analysis.

The engine combines:

Weekly     - Structural regime
Daily      - Primary swing direction
60-minute  - Setup quality
15-minute  - Entry confirmation
5-minute   - Execution timing

Lower timeframes refine timing but cannot override materially bearish
higher-timeframe structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FusionResult:
    """
    Final decision produced from the five timeframe analyses.
    """

    fusion_score: int
    swing_bias: str
    alignment: str
    entry_status: str
    position_guidance: str
    confidence: str
    decision_state: str

    bullish_timeframes: int
    bearish_timeframes: int
    neutral_timeframes: int

    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


class TimeframeFusionEngine:
    """
    Combine PATCC timeframe evidence into one hierarchical decision.
    """

    DEFAULT_WEIGHTS = {
        "weekly": 0.20,
        "daily": 0.30,
        "hourly": 0.20,
        "setup": 0.20,
        "entry": 0.10,
    }

    REQUIRED_KEYS = {
        "weekly",
        "daily",
        "hourly",
        "setup",
        "entry",
    }

    BULLISH_TRENDS = {
        "Strong Bullish",
        "Bullish",
    }

    BEARISH_TRENDS = {
        "Strong Bearish",
        "Bearish",
    }

    DISTRIBUTION_CLASSES = {
        "Distribution",
        "Weak / Distribution Risk",
    }

    def fuse(
        self,
        analyses: Iterable,
    ) -> FusionResult:
        """
        Fuse all required timeframe analyses.
        """

        analysis_list = list(analyses)

        if not analysis_list:
            raise ValueError(
                "At least one timeframe analysis is required."
            )

        by_key = {
            analysis.key: analysis
            for analysis in analysis_list
        }

        missing = self.REQUIRED_KEYS - set(by_key)

        if missing:
            raise ValueError(
                "Missing required timeframe analyses: "
                f"{sorted(missing)}"
            )

        weekly = by_key["weekly"]
        daily = by_key["daily"]
        hourly = by_key["hourly"]
        setup = by_key["setup"]
        entry = by_key["entry"]

        counts = self._count_trends(analysis_list)

        fusion_score = self._weighted_score(
            analysis_list
        )

        swing_bias = self._swing_bias(
            weekly=weekly,
            daily=daily,
        )

        alignment = self._alignment(
            bullish=counts["bullish"],
            bearish=counts["bearish"],
            neutral=counts["neutral"],
            total=len(analysis_list),
        )

        entry_status = self._entry_status(
            swing_bias=swing_bias,
            weekly=weekly,
            daily=daily,
            hourly=hourly,
            setup=setup,
            entry=entry,
        )

        position_guidance = self._position_guidance(
            swing_bias=swing_bias,
            entry_status=entry_status,
            daily=daily,
            hourly=hourly,
        )

        confidence = self._confidence(
            analyses=analysis_list,
            alignment=alignment,
            weekly=weekly,
            daily=daily,
        )

        decision_state = self._decision_state(
            swing_bias=swing_bias,
            entry_status=entry_status,
        )

        reasons = self._reasons(
            weekly=weekly,
            daily=daily,
            hourly=hourly,
            setup=setup,
            entry=entry,
            swing_bias=swing_bias,
            entry_status=entry_status,
        )

        warnings = self._warnings(
            analyses=analysis_list,
            weekly=weekly,
            daily=daily,
            hourly=hourly,
        )

        return FusionResult(
            fusion_score=fusion_score,
            swing_bias=swing_bias,
            alignment=alignment,
            entry_status=entry_status,
            position_guidance=position_guidance,
            confidence=confidence,
            decision_state=decision_state,
            bullish_timeframes=counts["bullish"],
            bearish_timeframes=counts["bearish"],
            neutral_timeframes=counts["neutral"],
            reasons=tuple(reasons),
            warnings=tuple(warnings),
        )

    def _weighted_score(
        self,
        analyses: list,
    ) -> int:
        weighted_total = 0.0
        total_weight = 0.0

        for analysis in analyses:
            weight = self.DEFAULT_WEIGHTS.get(
                analysis.key,
                0.0,
            )

            weighted_total += (
                float(analysis.score.overall_score)
                * weight
            )

            total_weight += weight

        if total_weight <= 0:
            return 0

        result = round(
            weighted_total / total_weight
        )

        return max(
            0,
            min(100, int(result)),
        )

    def _count_trends(
        self,
        analyses: list,
    ) -> dict[str, int]:
        bullish = 0
        bearish = 0
        neutral = 0

        for analysis in analyses:
            trend = analysis.market_state.trend

            if trend in self.BULLISH_TRENDS:
                bullish += 1
            elif trend in self.BEARISH_TRENDS:
                bearish += 1
            else:
                neutral += 1

        return {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
        }

    def _swing_bias(
        self,
        *,
        weekly,
        daily,
    ) -> str:
        weekly_trend = weekly.market_state.trend
        daily_trend = daily.market_state.trend

        if (
            weekly_trend in self.BEARISH_TRENDS
            and daily_trend in self.BEARISH_TRENDS
        ):
            return "Bearish"

        if daily_trend in self.BEARISH_TRENDS:
            return "Cautiously Bearish"

        if (
            weekly_trend in self.BULLISH_TRENDS
            and daily_trend in self.BULLISH_TRENDS
        ):
            return "Bullish"

        if daily_trend in self.BULLISH_TRENDS:
            return "Cautiously Bullish"

        if (
            daily_trend == "Neutral"
            and weekly_trend in self.BULLISH_TRENDS
        ):
            return "Neutral / Bullish Structure"

        if (
            daily_trend == "Neutral"
            and weekly_trend in self.BEARISH_TRENDS
        ):
            return "Neutral / Bearish Structure"

        return "Neutral"

    def _alignment(
        self,
        *,
        bullish: int,
        bearish: int,
        neutral: int,
        total: int,
    ) -> str:
        if bullish == total:
            return "Full Bullish"

        if bearish == total:
            return "Full Bearish"

        if bullish >= 4:
            return "Strong Bullish Alignment"

        if bearish >= 4:
            return "Strong Bearish Alignment"

        if bullish >= 3:
            return "Partial Bullish"

        if bearish >= 3:
            return "Partial Bearish"

        if neutral >= 3:
            return "Mostly Neutral"

        return "Mixed / Transitional"

    def _entry_status(
        self,
        *,
        swing_bias: str,
        weekly,
        daily,
        hourly,
        setup,
        entry,
    ) -> str:
        weekly_trend = weekly.market_state.trend
        daily_trend = daily.market_state.trend
        hourly_trend = hourly.market_state.trend
        setup_trend = setup.market_state.trend
        entry_trend = entry.market_state.trend

        daily_footprint = (
            daily.institutional_footprint.classification
        )

        hourly_footprint = (
            hourly.institutional_footprint.classification
        )

        setup_footprint = (
            setup.institutional_footprint.classification
        )

        if (
            weekly_trend in self.BEARISH_TRENDS
            and daily_trend in self.BEARISH_TRENDS
        ):
            return "No New Long Entry"

        if daily_footprint == "Distribution":
            return "Avoid - Daily Distribution"

        if hourly_footprint == "Distribution":
            return "Avoid - 60-Minute Distribution"

        if daily_trend in self.BEARISH_TRENDS:
            return "No New Long Entry"

        if hourly_trend in self.BEARISH_TRENDS:
            return "Wait - 60-Minute Trend Bearish"

        if setup_trend in self.BEARISH_TRENDS:
            return "Wait - 15-Minute Breakdown"

        higher_timeframes_supportive = (
            swing_bias
            in {
                "Bullish",
                "Cautiously Bullish",
                "Neutral / Bullish Structure",
            }
        )

        hourly_supportive = (
            hourly_trend in self.BULLISH_TRENDS
            and hourly_footprint
            not in self.DISTRIBUTION_CLASSES
        )

        setup_supportive = (
            setup_trend in self.BULLISH_TRENDS
            and setup_footprint
            not in self.DISTRIBUTION_CLASSES
            and setup.indicators.price_above_dema8
        )

        entry_trigger = (
            entry_trend in self.BULLISH_TRENDS
            and entry.indicators.price_above_dema8
            and entry.indicators.price_above_vwap20
            and entry.indicators.dema8_slope > 0
        )

        if (
            higher_timeframes_supportive
            and hourly_supportive
            and setup_supportive
            and entry_trigger
        ):
            return "Entry Confirmed"

        if (
            higher_timeframes_supportive
            and hourly_supportive
            and setup_supportive
        ):
            return "Wait for 5-Minute Trigger"

        if (
            higher_timeframes_supportive
            and hourly_supportive
        ):
            return "Wait for 15-Minute Confirmation"

        if higher_timeframes_supportive:
            return "Watch Pullback - 60-Minute Not Ready"

        return "No Action"

    def _position_guidance(
        self,
        *,
        swing_bias: str,
        entry_status: str,
        daily,
        hourly,
    ) -> str:
        if entry_status == "Entry Confirmed":
            return (
                "Consider a new position using defined risk controls"
            )

        if entry_status == "Wait for 5-Minute Trigger":
            return (
                "Setup is constructive; defer entry until "
                "execution confirmation"
            )

        if entry_status == "Wait for 15-Minute Confirmation":
            return (
                "Hold existing position if risk permits; "
                "do not add yet"
            )

        if entry_status.startswith("Wait -"):
            return (
                "Defer new entry until the adverse timeframe improves"
            )

        if entry_status.startswith("Watch Pullback"):
            return "Monitor only; do not chase price"

        if entry_status.startswith("Avoid"):
            return "Remain out or reduce exposure"

        if entry_status == "No New Long Entry":
            return "Avoid initiating a new long position"

        if swing_bias in {
            "Bearish",
            "Cautiously Bearish",
            "Neutral / Bearish Structure",
        }:
            return "Maintain a defensive posture"

        daily_classification = (
            daily.institutional_footprint.classification
        )

        hourly_classification = (
            hourly.institutional_footprint.classification
        )

        if (
            daily_classification
            in self.DISTRIBUTION_CLASSES
            or hourly_classification
            in self.DISTRIBUTION_CLASSES
        ):
            return (
                "Protect capital until money-flow evidence improves"
            )

        return "Observe until timeframe alignment improves"

    def _confidence(
        self,
        *,
        analyses: list,
        alignment: str,
        weekly,
        daily,
    ) -> str:
        provisional_count = sum(
            bool(analysis.bar_validation.provisional)
            for analysis in analyses
        )

        benchmark_missing_count = sum(
            (
                analysis.institutional_footprint
                .relative_strength_20d
                is None
            )
            for analysis in analyses
        )

        higher_timeframe_agreement = (
            (
                weekly.market_state.trend
                in self.BULLISH_TRENDS
                and daily.market_state.trend
                in self.BULLISH_TRENDS
            )
            or (
                weekly.market_state.trend
                in self.BEARISH_TRENDS
                and daily.market_state.trend
                in self.BEARISH_TRENDS
            )
        )

        strong_alignments = {
            "Full Bullish",
            "Full Bearish",
            "Strong Bullish Alignment",
            "Strong Bearish Alignment",
        }

        if (
            alignment in strong_alignments
            and higher_timeframe_agreement
            and provisional_count == 0
            and benchmark_missing_count == 0
        ):
            return "High"

        if provisional_count <= 1:
            return "Moderate"

        return "Limited"

    def _decision_state(
        self,
        *,
        swing_bias: str,
        entry_status: str,
    ) -> str:
        if entry_status == "Entry Confirmed":
            return "ACTIONABLE"

        if (
            entry_status.startswith("Wait")
            or entry_status.startswith("Watch")
        ):
            return "PENDING CONFIRMATION"

        if (
            entry_status.startswith("Avoid")
            or entry_status == "No New Long Entry"
        ):
            return "RISK CONTROL"

        if swing_bias in {
            "Bearish",
            "Cautiously Bearish",
            "Neutral / Bearish Structure",
        }:
            return "DEFENSIVE"

        return "OBSERVATION"

    def _reasons(
        self,
        *,
        weekly,
        daily,
        hourly,
        setup,
        entry,
        swing_bias: str,
        entry_status: str,
    ) -> list[str]:
        dema_state = (
            "above"
            if entry.indicators.price_above_dema8
            else "below"
        )

        vwap_state = (
            "above"
            if entry.indicators.price_above_vwap20
            else "below"
        )

        return [
            (
                f"Weekly structural trend is "
                f"{weekly.market_state.trend}."
            ),
            (
                f"Daily swing trend is "
                f"{daily.market_state.trend}, producing a "
                f"{swing_bias.lower()} bias."
            ),
            (
                f"Daily institutional footprint is "
                f"{daily.institutional_footprint.classification} "
                f"with a score of "
                f"{daily.institutional_footprint.score}/100."
            ),
            (
                f"60-minute setup trend is "
                f"{hourly.market_state.trend}; footprint is "
                f"{hourly.institutional_footprint.classification}."
            ),
            (
                f"15-minute confirmation trend is "
                f"{setup.market_state.trend}."
            ),
            (
                f"5-minute price is {dema_state} DEMA-8 "
                f"and {vwap_state} VWAP-20."
            ),
            f"Final entry decision is {entry_status}.",
        ]

    def _warnings(
        self,
        *,
        analyses: list,
        weekly,
        daily,
        hourly,
    ) -> list[str]:
        warnings: list[str] = []

        for analysis in analyses:
            if analysis.bar_validation.provisional:
                warnings.append(
                    f"{analysis.label} uses an incomplete live bar; "
                    f"its result may change before bar close."
                )

            if analysis.indicators.rvol < 0.50:
                warnings.append(
                    f"{analysis.label} RVOL is "
                    f"{analysis.indicators.rvol:.2f}; "
                    f"participation is unusually low."
                )

            classification = (
                analysis.institutional_footprint.classification
            )

            if classification == "Distribution":
                warnings.append(
                    f"{analysis.label} footprint indicates "
                    f"distribution."
                )

            relative_strength = (
                analysis.institutional_footprint
                .relative_strength_20d
            )

            if relative_strength is None:
                warnings.append(
                    f"{analysis.label} relative strength "
                    f"against SPY is unavailable."
                )

        if (
            weekly.market_state.trend
            in self.BEARISH_TRENDS
            and daily.market_state.trend
            in self.BULLISH_TRENDS
        ):
            warnings.append(
                "Daily bullishness conflicts with the bearish "
                "weekly structure."
            )

        if (
            daily.market_state.trend
            in self.BULLISH_TRENDS
            and hourly.market_state.trend
            in self.BEARISH_TRENDS
        ):
            warnings.append(
                "Daily trend is bullish, but the 60-minute "
                "setup is bearish."
            )

        return self._deduplicate(warnings)

    @staticmethod
    def _deduplicate(
        values: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)

        return result
        