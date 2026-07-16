"""
recommendation_engine.py

PATCC Explainable Recommendation Engine

Responsibilities
----------------
- Combine technical analysis with trusted contextual evidence
- Consume Data Quality, Market Clock, and Event Risk results
- Respect watchlist priority and asset role
- Detect contradictions and insufficient-data conditions
- Produce an explainable decision state and confidence score

This module does not:
- Download market data
- Calculate technical indicators
- Place or transmit orders
- Select a final Brokerage, IRA, or Roth IRA account
- Determine portfolio allocation or position size

Version: 0.1.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from Core.data_quality_engine import (
    DataQualityResult,
    FreshnessStatus,
    QualityStatus,
)
from Core.event_risk_engine import (
    EventRiskLevel,
    EventRiskResult,
)
from Core.market_clock import (
    MarketContext,
    MarketPhase,
    MarketStatus,
    ReadinessLevel,
)


class DecisionState(str, Enum):
    """PATCC decision-support state."""

    ACTION = "ACTION"
    WATCH = "WATCH"
    MONITOR = "MONITOR"
    HEDGE = "HEDGE"
    AVOID = "AVOID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ConfidenceLevel(str, Enum):
    """Readable confidence classification."""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True)
class TechnicalEvidence:
    """
    Technical-analysis input supplied by the scoring engine.

    The Recommendation Engine consumes this evidence but does not
    independently calculate indicators.
    """

    ticker: str
    score: int
    grade: str
    trend: str
    action: str
    momentum: str = "UNKNOWN"
    volatility: str = "UNKNOWN"
    volume: str = "UNKNOWN"
    risk_level: str = "UNKNOWN"


@dataclass(frozen=True)
class AssetContext:
    """Operational identity and role for one asset."""

    ticker: str
    priority: int
    asset_class: str
    category: str
    market_role: str
    tactical: bool = False
    inverse: bool = False
    leveraged: bool = False


@dataclass(frozen=True)
class RecommendationInput:
    """Complete input consumed by the Recommendation Engine."""

    technical: TechnicalEvidence
    asset: AssetContext
    data_quality: DataQualityResult
    market_context: MarketContext
    event_risk: EventRiskResult


@dataclass(frozen=True)
class EvidenceContribution:
    """One explainable contribution to recommendation confidence."""

    component: str
    points: int
    maximum_points: int
    status: str
    explanation: str


@dataclass(frozen=True)
class RecommendationResult:
    """Complete explainable PATCC recommendation."""

    generated_at_et: datetime
    ticker: str
    decision: DecisionState
    confidence_score: int
    confidence_level: ConfidenceLevel
    technical_score: int
    watchlist_priority: int
    market_role: str
    data_quality_status: QualityStatus
    data_freshness: FreshnessStatus
    market_status: MarketStatus
    market_phase: MarketPhase
    market_readiness: ReadinessLevel
    event_risk_level: EventRiskLevel
    event_risk_score: int
    human_review_required: bool
    execution_ready: bool
    evidence: tuple[EvidenceContribution, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    contradictions: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    recommendation: str


class RecommendationEngine:
    """
    Produce one explainable decision-support recommendation.

    Version 0.1 deliberately stops before portfolio-aware account
    selection and position sizing.
    """

    def evaluate(
        self,
        recommendation_input: RecommendationInput,
    ) -> RecommendationResult:
        """Evaluate one asset using all supplied evidence."""
        self._validate_input(recommendation_input)

        technical = recommendation_input.technical
        asset = recommendation_input.asset
        data_quality = recommendation_input.data_quality
        market = recommendation_input.market_context
        event_risk = recommendation_input.event_risk

        evidence: list[EvidenceContribution] = []
        reasons: list[str] = []
        warnings: list[str] = []
        contradictions: list[str] = []

        evidence.append(
            self._technical_contribution(technical)
        )
        evidence.append(
            self._data_quality_contribution(data_quality)
        )
        evidence.append(
            self._market_context_contribution(
                market=market,
                asset=asset,
            )
        )
        evidence.append(
            self._event_risk_contribution(event_risk)
        )
        evidence.append(
            self._priority_contribution(asset)
        )

        warnings.extend(data_quality.warnings)
        warnings.extend(data_quality.errors)
        warnings.extend(event_risk.warnings)
        warnings.extend(market.warnings)

        contradictions.extend(
            self._detect_contradictions(
                technical=technical,
                asset=asset,
                market=market,
                event_risk=event_risk,
            )
        )

        confidence_score = sum(
            item.points for item in evidence
        )

        confidence_score -= min(
            len(contradictions) * 8,
            24,
        )

        confidence_score = max(
            0,
            min(100, confidence_score),
        )

        decision = self._determine_decision(
            technical=technical,
            asset=asset,
            data_quality=data_quality,
            market=market,
            event_risk=event_risk,
            confidence_score=confidence_score,
            contradictions=contradictions,
        )

        confidence_level = self._confidence_level(
            confidence_score
        )

        reasons.extend(
            self._build_reasons(
                technical=technical,
                asset=asset,
                data_quality=data_quality,
                market=market,
                event_risk=event_risk,
                decision=decision,
            )
        )

        human_review_required = self._requires_human_review(
            decision=decision,
            asset=asset,
            event_risk=event_risk,
            market=market,
            contradictions=contradictions,
        )

        execution_ready = self._execution_ready(
            decision=decision,
            data_quality=data_quality,
            event_risk=event_risk,
            market=market,
            contradictions=contradictions,
        )

        invalidation_conditions = (
            self._build_invalidation_conditions(
                technical=technical,
                asset=asset,
                data_quality=data_quality,
                market=market,
                event_risk=event_risk,
            )
        )

        recommendation = self._build_recommendation_text(
            ticker=technical.ticker,
            decision=decision,
            confidence_score=confidence_score,
            data_quality=data_quality,
            market=market,
            event_risk=event_risk,
            asset=asset,
            execution_ready=execution_ready,
        )

        return RecommendationResult(
            generated_at_et=market.evaluated_at_et,
            ticker=technical.ticker.strip().upper(),
            decision=decision,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            technical_score=technical.score,
            watchlist_priority=asset.priority,
            market_role=asset.market_role,
            data_quality_status=data_quality.status,
            data_freshness=data_quality.freshness,
            market_status=market.market_status,
            market_phase=market.market_phase,
            market_readiness=market.readiness,
            event_risk_level=event_risk.risk_level,
            event_risk_score=event_risk.risk_score,
            human_review_required=human_review_required,
            execution_ready=execution_ready,
            evidence=tuple(evidence),
            reasons=tuple(reasons),
            warnings=tuple(dict.fromkeys(warnings)),
            contradictions=tuple(contradictions),
            invalidation_conditions=tuple(
                invalidation_conditions
            ),
            recommendation=recommendation,
        )

    def explain(
        self,
        result: RecommendationResult,
    ) -> str:
        """Return a concise explanation of one recommendation."""
        explanation = (
            f"PATCC classifies {result.ticker} as "
            f"{result.decision.value} with "
            f"{result.confidence_score}/100 confidence. "
            f"The technical score is "
            f"{result.technical_score}/100. "
            f"Data quality is "
            f"{result.data_quality_status.value} and "
            f"{result.data_freshness.value}. "
            f"The market is in the "
            f"{result.market_phase.value} phase with "
            f"{result.market_readiness.value} readiness. "
            f"Ticker-specific event risk is "
            f"{result.event_risk_level.value}. "
            f"{result.recommendation}"
        )

        return explanation

    def report(
        self,
        result: RecommendationResult,
    ) -> str:
        """Return a readable professional decision report."""
        lines: list[str] = []

        lines.append("=" * 92)
        lines.append("PATCC EXPLAINABLE RECOMMENDATION ENGINE v0.1")
        lines.append("=" * 92)
        lines.append(
            f"Generated at          : "
            f"{result.generated_at_et:%Y-%m-%d %I:%M:%S %p %Z}"
        )
        lines.append(
            f"Ticker                : {result.ticker}"
        )
        lines.append(
            f"Decision              : {result.decision.value}"
        )
        lines.append(
            f"Confidence            : "
            f"{result.confidence_score}/100 "
            f"({result.confidence_level.value})"
        )
        lines.append(
            f"Technical score       : "
            f"{result.technical_score}/100"
        )
        lines.append(
            f"Watchlist priority    : "
            f"P{result.watchlist_priority}"
        )
        lines.append(
            f"Market role           : {result.market_role}"
        )
        lines.append(
            f"Data quality          : "
            f"{result.data_quality_status.value}"
        )
        lines.append(
            f"Data freshness        : "
            f"{result.data_freshness.value}"
        )
        lines.append(
            f"Market status         : "
            f"{result.market_status.value}"
        )
        lines.append(
            f"Market phase          : "
            f"{result.market_phase.value}"
        )
        lines.append(
            f"Market readiness      : "
            f"{result.market_readiness.value}"
        )
        lines.append(
            f"Event risk            : "
            f"{result.event_risk_level.value} "
            f"({result.event_risk_score}/100)"
        )
        lines.append(
            f"Human review required : "
            f"{result.human_review_required}"
        )
        lines.append(
            f"Execution ready       : "
            f"{result.execution_ready}"
        )

        lines.append("-" * 92)
        lines.append("RECOMMENDATION")
        lines.append(result.recommendation)

        lines.append("-" * 92)
        lines.append("EVIDENCE BREAKDOWN")

        for item in result.evidence:
            lines.append(
                f"{item.component:<24}"
                f"{item.points:>3}/{item.maximum_points:<3} "
                f"{item.status:<16}"
                f"{item.explanation}"
            )

        if result.reasons:
            lines.append("-" * 92)
            lines.append("WHY PATCC REACHED THIS DECISION")

            for reason in result.reasons:
                lines.append(f"- {reason}")

        if result.contradictions:
            lines.append("-" * 92)
            lines.append("CONTRADICTIONS")

            for contradiction in result.contradictions:
                lines.append(f"- {contradiction}")

        if result.warnings:
            lines.append("-" * 92)
            lines.append("WARNINGS")

            for warning in result.warnings:
                lines.append(f"- {warning}")

        if result.invalidation_conditions:
            lines.append("-" * 92)
            lines.append(
                "WHAT COULD CHANGE THIS RECOMMENDATION?"
            )

            for condition in result.invalidation_conditions:
                lines.append(f"- {condition}")

        lines.append("=" * 92)

        return "\n".join(lines)

    @staticmethod
    def _validate_input(
        recommendation_input: RecommendationInput,
    ) -> None:
        """Validate cross-module ticker consistency."""
        technical_ticker = (
            recommendation_input.technical.ticker
            .strip()
            .upper()
        )
        asset_ticker = (
            recommendation_input.asset.ticker
            .strip()
            .upper()
        )
        quality_ticker = (
            recommendation_input.data_quality.symbol
            .strip()
            .upper()
        )

        if not technical_ticker:
            raise ValueError(
                "Technical evidence ticker cannot be empty."
            )

        if technical_ticker != asset_ticker:
            raise ValueError(
                "Technical and Asset Context tickers do not match."
            )

        if technical_ticker != quality_ticker:
            raise ValueError(
                "Technical and Data Quality tickers do not match."
            )

        event_ticker = recommendation_input.event_risk.ticker

        if event_ticker and event_ticker != technical_ticker:
            raise ValueError(
                "Ticker-specific Event Risk result does not match "
                "the Recommendation Engine ticker."
            )

        if not 0 <= recommendation_input.technical.score <= 100:
            raise ValueError(
                "Technical score must be between 0 and 100."
            )

        if recommendation_input.asset.priority < 1:
            raise ValueError(
                "Watchlist priority must be greater than zero."
            )

    @staticmethod
    def _technical_contribution(
        technical: TechnicalEvidence,
    ) -> EvidenceContribution:
        """Convert technical score to a maximum of 40 points."""
        points = round(technical.score * 0.40)

        return EvidenceContribution(
            component="Technical Analysis",
            points=points,
            maximum_points=40,
            status=technical.action,
            explanation=(
                f"Technical score {technical.score}/100; "
                f"trend {technical.trend}; grade {technical.grade}."
            ),
        )

    @staticmethod
    def _data_quality_contribution(
        data_quality: DataQualityResult,
    ) -> EvidenceContribution:
        """Convert data quality to a maximum of 20 points."""
        if data_quality.status == QualityStatus.FAIL:
            points = 0
        else:
            points = round(
                data_quality.quality_score * 0.20
            )

        return EvidenceContribution(
            component="Data Trust",
            points=points,
            maximum_points=20,
            status=(
                f"{data_quality.status.value}/"
                f"{data_quality.freshness.value}"
            ),
            explanation=(
                f"Provider {data_quality.provider}; "
                f"quality {data_quality.quality_score}/100; "
                f"age {data_quality.age_description}."
            ),
        )

    @staticmethod
    def _market_context_contribution(
        market: MarketContext,
        asset: AssetContext,
    ) -> EvidenceContribution:
        """Translate Market Clock context into 0–15 points."""
        readiness_points = {
            ReadinessLevel.HIGH: 15,
            ReadinessLevel.NORMAL: 12,
            ReadinessLevel.CAUTION: 8,
            ReadinessLevel.LOW: 4,
            ReadinessLevel.CLOSED: 2,
        }

        points = readiness_points[market.readiness]

        if asset.market_role.casefold() == "market context":
            points = max(points, 10)

        return EvidenceContribution(
            component="Market Context",
            points=points,
            maximum_points=15,
            status=(
                f"{market.market_phase.value}/"
                f"{market.readiness.value}"
            ),
            explanation=market.explanation,
        )

    @staticmethod
    def _event_risk_contribution(
        event_risk: EventRiskResult,
    ) -> EvidenceContribution:
        """
        Convert event risk into positive usable-confidence points.

        Low event risk receives more confidence points.
        """
        points_by_risk = {
            EventRiskLevel.NONE: 15,
            EventRiskLevel.LOW: 13,
            EventRiskLevel.MODERATE: 9,
            EventRiskLevel.HIGH: 5,
            EventRiskLevel.CRITICAL: 0,
        }

        points = points_by_risk[event_risk.risk_level]

        return EvidenceContribution(
            component="Event Environment",
            points=points,
            maximum_points=15,
            status=event_risk.risk_level.value,
            explanation=event_risk.recommendation,
        )

    @staticmethod
    def _priority_contribution(
        asset: AssetContext,
    ) -> EvidenceContribution:
        """Translate operational priority into 0–10 points."""
        if asset.priority == 1:
            points = 10
            status = "MANDATORY CONTEXT"
        elif asset.priority == 2:
            points = 8
            status = "STRATEGIC"
        elif asset.priority == 3:
            points = 5
            status = "TACTICAL"
        else:
            points = 2
            status = "RESEARCH"

        return EvidenceContribution(
            component="Operational Priority",
            points=points,
            maximum_points=10,
            status=status,
            explanation=(
                f"P{asset.priority} asset; role "
                f"{asset.market_role}."
            ),
        )

    @staticmethod
    def _detect_contradictions(
        *,
        technical: TechnicalEvidence,
        asset: AssetContext,
        market: MarketContext,
        event_risk: EventRiskResult,
    ) -> list[str]:
        """Detect important cross-module contradictions."""
        contradictions: list[str] = []

        trend = technical.trend.casefold()
        action = technical.action.casefold()

        bullish = (
            "bullish" in trend
            or "good candidate" in action
            or "strong buy" in action
        )
        bearish = (
            "bearish" in trend
            or "avoid" in action
            or "sell" in action
        )

        if bullish and bearish:
            contradictions.append(
                "Technical evidence contains both bullish and "
                "bearish classifications."
            )

        if (
            asset.inverse
            and bullish
            and market.readiness == ReadinessLevel.HIGH
        ):
            contradictions.append(
                "Inverse instrument is technically positive while "
                "the broader market environment is operationally "
                "strong; confirm the underlying bearish thesis."
            )

        if (
            asset.leveraged
            and technical.score < 75
        ):
            contradictions.append(
                "Leveraged instrument does not meet the preferred "
                "higher technical-score threshold."
            )

        if (
            event_risk.risk_level
            in {
                EventRiskLevel.HIGH,
                EventRiskLevel.CRITICAL,
            }
            and technical.score >= 75
        ):
            contradictions.append(
                "Strong technical evidence conflicts with elevated "
                "near-term event risk."
            )

        return contradictions

    @staticmethod
    def _determine_decision(
        *,
        technical: TechnicalEvidence,
        asset: AssetContext,
        data_quality: DataQualityResult,
        market: MarketContext,
        event_risk: EventRiskResult,
        confidence_score: int,
        contradictions: list[str],
    ) -> DecisionState:
        """Determine the final decision-support state."""
        if (
            data_quality.status == QualityStatus.FAIL
            or data_quality.freshness
            in {
                FreshnessStatus.STALE,
                FreshnessStatus.UNKNOWN,
            }
        ):
            return DecisionState.INSUFFICIENT_DATA

        if technical.score < 40:
            if asset.inverse and event_risk.risk_level in {
                EventRiskLevel.HIGH,
                EventRiskLevel.CRITICAL,
            }:
                return DecisionState.HEDGE

            return DecisionState.AVOID

        if asset.market_role.casefold() == "market context":
            if technical.score >= 75:
                return DecisionState.MONITOR

            if technical.score >= 55:
                return DecisionState.MONITOR

            return DecisionState.AVOID

        if asset.inverse:
            if (
                technical.score >= 75
                and confidence_score >= 75
            ):
                return DecisionState.HEDGE

            if technical.score >= 55:
                return DecisionState.WATCH

            return DecisionState.AVOID

        if (
            event_risk.risk_level
            in {
                EventRiskLevel.HIGH,
                EventRiskLevel.CRITICAL,
            }
        ):
            if technical.score >= 55:
                return DecisionState.WATCH

            return DecisionState.AVOID

        if market.market_status == MarketStatus.CLOSED:
            if technical.score >= 70:
                return DecisionState.WATCH

            return DecisionState.MONITOR

        if (
            technical.score >= 75
            and confidence_score >= 75
            and not contradictions
        ):
            return DecisionState.ACTION

        if technical.score >= 55:
            return DecisionState.WATCH

        if asset.priority == 1:
            return DecisionState.MONITOR

        return DecisionState.AVOID

    @staticmethod
    def _confidence_level(
        score: int,
    ) -> ConfidenceLevel:
        """Translate confidence score into a readable level."""
        if score < 35:
            return ConfidenceLevel.VERY_LOW

        if score < 50:
            return ConfidenceLevel.LOW

        if score < 70:
            return ConfidenceLevel.MODERATE

        if score < 85:
            return ConfidenceLevel.HIGH

        return ConfidenceLevel.VERY_HIGH

    @staticmethod
    def _build_reasons(
        *,
        technical: TechnicalEvidence,
        asset: AssetContext,
        data_quality: DataQualityResult,
        market: MarketContext,
        event_risk: EventRiskResult,
        decision: DecisionState,
    ) -> list[str]:
        """Build human-readable decision reasons."""
        return [
            (
                f"Technical scoring classified {technical.ticker} "
                f"at {technical.score}/100 with a "
                f"{technical.trend} trend."
            ),
            (
                f"Market data passed with "
                f"{data_quality.quality_score}/100 quality and "
                f"{data_quality.freshness.value} freshness."
            ),
            (
                f"The market is currently in the "
                f"{market.market_phase.value} phase with "
                f"{market.readiness.value} readiness."
            ),
            (
                f"Ticker-specific event risk is "
                f"{event_risk.risk_level.value} at "
                f"{event_risk.risk_score}/100."
            ),
            (
                f"{technical.ticker} is a P{asset.priority} "
                f"{asset.market_role} asset."
            ),
            (
                f"Combined evidence produced the "
                f"{decision.value} decision state."
            ),
        ]

    @staticmethod
    def _requires_human_review(
        *,
        decision: DecisionState,
        asset: AssetContext,
        event_risk: EventRiskResult,
        market: MarketContext,
        contradictions: list[str],
    ) -> bool:
        """Determine whether explicit human review is required."""
        return (
            decision
            in {
                DecisionState.ACTION,
                DecisionState.HEDGE,
                DecisionState.INSUFFICIENT_DATA,
            }
            or asset.leveraged
            or asset.inverse
            or event_risk.risk_level
            in {
                EventRiskLevel.HIGH,
                EventRiskLevel.CRITICAL,
            }
            or market.readiness
            in {
                ReadinessLevel.CAUTION,
                ReadinessLevel.LOW,
            }
            or bool(contradictions)
        )

    @staticmethod
    def _execution_ready(
        *,
        decision: DecisionState,
        data_quality: DataQualityResult,
        event_risk: EventRiskResult,
        market: MarketContext,
        contradictions: list[str],
    ) -> bool:
        """
        Return whether current evidence is ready for further execution
        validation.

        This does not mean an order may be submitted. Portfolio,
        account, quote, spread, position-size and compliance checks
        are still required.
        """
        return (
            decision == DecisionState.ACTION
            and data_quality.status == QualityStatus.PASS
            and data_quality.freshness
            in {
                FreshnessStatus.FRESH,
                FreshnessStatus.CURRENT,
            }
            and event_risk.risk_level
            in {
                EventRiskLevel.NONE,
                EventRiskLevel.LOW,
            }
            and market.market_status == MarketStatus.OPEN
            and market.readiness
            in {
                ReadinessLevel.HIGH,
                ReadinessLevel.NORMAL,
            }
            and not contradictions
        )

    @staticmethod
    def _build_invalidation_conditions(
        *,
        technical: TechnicalEvidence,
        asset: AssetContext,
        data_quality: DataQualityResult,
        market: MarketContext,
        event_risk: EventRiskResult,
    ) -> list[str]:
        """Build conditions that require recommendation reassessment."""
        conditions = [
            (
                "Technical score or trend materially deteriorates "
                "from the current assessment."
            ),
            (
                "Data freshness changes from "
                f"{data_quality.freshness.value} to AGING or STALE."
            ),
            (
                "Market phase or readiness changes materially from "
                f"{market.market_phase.value}/"
                f"{market.readiness.value}."
            ),
            (
                "Event risk remains elevated, rises above the current "
                f"{event_risk.risk_level.value} classification, or the "
                "post-event market reaction invalidates the current thesis."
            ),
        ]

        if asset.leveraged:
            conditions.append(
                "The underlying unleveraged asset no longer confirms "
                "the leveraged instrument's direction."
            )

        if asset.inverse:
            conditions.append(
                "The bearish or hedging thesis for the inverse "
                "instrument is no longer valid."
            )

        if technical.risk_level != "UNKNOWN":
            conditions.append(
                f"Technical risk changes materially from "
                f"{technical.risk_level}."
            )

        return conditions

    @staticmethod
    def _build_recommendation_text(
        *,
        ticker: str,
        decision: DecisionState,
        confidence_score: int,
        data_quality: DataQualityResult,
        market: MarketContext,
        event_risk: EventRiskResult,
        asset: AssetContext,
        execution_ready: bool,
    ) -> str:
        """Build the final concise recommendation text."""
        ticker = ticker.strip().upper()

        if decision == DecisionState.INSUFFICIENT_DATA:
            return (
                f"Do not rely on the current {ticker} signal. "
                f"Underlying data is not sufficiently current or "
                f"valid for this decision horizon."
            )

        if decision == DecisionState.AVOID:
            return (
                f"Avoid initiating or increasing {ticker} based on "
                f"the present evidence. Technical strength, context, "
                f"or risk conditions are insufficient."
            )

        if decision == DecisionState.MONITOR:
            return (
                f"Continue monitoring {ticker}. It is important for "
                f"market context, but the current result is not an "
                f"execution recommendation."
            )

        if decision == DecisionState.HEDGE:
            return (
                f"Treat {ticker} as a conditional hedge candidate. "
                f"Confirm the underlying risk-off thesis, exposure "
                f"limits, and exit conditions before any manual action."
            )

        if decision == DecisionState.WATCH:
            return (
                f"Keep {ticker} on the active watchlist. The setup "
                f"has useful evidence, but additional confirmation is "
                f"required because event risk is "
                f"{event_risk.risk_level.value}, market readiness is "
                f"{market.readiness.value}, or evidence conflicts remain."
            )

        readiness_text = (
            "Current contextual checks passed."
            if execution_ready
            else (
                "Market evidence supports further review, but live "
                "quote, portfolio, account-allocation, tax, position-"
                "size and compliance checks remain outstanding."
            )
        )

        return (
            f"{ticker} is an ACTION candidate with "
            f"{confidence_score}/100 confidence. "
            f"{readiness_text} Asset role: {asset.market_role}."
        )


def main() -> int:
    """
    Run a standalone deterministic XLE recommendation example.

    This test intentionally places XLE 15 minutes before the EIA
    inventory report to verify that constructive technical evidence
    is reduced to WATCH because event risk is HIGH.
    """
    from datetime import timedelta

    from Core.data_quality_engine import (
        DataQualityEngine,
        DataQualityRecord,
        EASTERN_TIME,
    )
    from Core.economic_calendar import (
        EconomicCalendarEngine,
        build_test_timestamp,
    )
    from Core.event_risk_engine import EventRiskEngine
    from Core.market_clock import MarketClock

    test_time = build_test_timestamp(
        2026,
        7,
        15,
        10,
        15,
    )

    quality_record = DataQualityRecord(
        symbol="XLE",
        provider="Yahoo Finance",
        timeframe="5m",
        observation_time=test_time - timedelta(minutes=4),
        fetched_at=test_time,
        market_session="REGULAR",
        data_mode="Intraday test data",
        price=109.25,
        volume=1_250_000,
        expected_real_time=False,
        provider_reliability=90,
    )

    data_quality = DataQualityEngine().evaluate(
        quality_record
    )

    market_context = MarketClock().evaluate(test_time)

    calendar_engine = EconomicCalendarEngine()
    calendar_engine.load()
    calendar = calendar_engine.evaluate(test_time)

    event_risk = EventRiskEngine().evaluate_ticker(
        calendar,
        "XLE",
    )

    recommendation_input = RecommendationInput(
        technical=TechnicalEvidence(
            ticker="XLE",
            score=78,
            grade="B",
            trend="Bullish",
            action="Good Candidate",
            momentum="Bullish",
            volatility="Normal",
            volume="Above Average",
            risk_level="Moderate",
        ),
        asset=AssetContext(
            ticker="XLE",
            priority=2,
            asset_class="Equity",
            category="Sector ETF",
            market_role="Sector Monitor",
            tactical=False,
            inverse=False,
            leveraged=False,
        ),
        data_quality=data_quality,
        market_context=market_context,
        event_risk=event_risk,
    )

    engine = RecommendationEngine()
    result = engine.evaluate(recommendation_input)

    print(engine.report(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
