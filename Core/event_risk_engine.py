"""
event_risk_engine.py

PATCC Event Risk Engine

Responsibilities
----------------
- Consume evaluated events from EconomicCalendarEngine
- Convert event timing, impact and asset sensitivity into risk
- Produce market-wide and ticker-specific event-risk assessments
- Explain every risk classification
- Preserve warnings and evidence for later Decision Engine use

This module does not:
- Download economic-calendar data
- Produce technical scores
- Generate buy or sell orders
- Select brokerage or retirement accounts

Version: 0.1.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from Core.economic_calendar import (
    CalendarEvaluation,
    EconomicCalendarEngine,
    EvaluatedEvent,
    EventStatus,
    ImpactLevel,
    SensitivityLevel,
)


class EventRiskLevel(str, Enum):
    """PATCC event-risk classification."""

    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class EventRiskContribution:
    """One event contributing to an overall risk result."""

    event_id: str
    event_name: str
    short_name: str
    event_status: EventStatus
    impact: ImpactLevel
    ticker: Optional[str]
    sensitivity: Optional[SensitivityLevel]
    risk_points: int
    explanation: str
    guidance: str


@dataclass(frozen=True)
class EventRiskResult:
    """Complete event-risk assessment."""

    evaluated_at_et: datetime
    scope: str
    ticker: Optional[str]
    risk_level: EventRiskLevel
    risk_score: int
    confidence: int
    active_event_count: int
    relevant_event_count: int
    highest_risk_event: Optional[str]
    contributions: tuple[EventRiskContribution, ...]
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    recommendation: str


IMPACT_POINTS: dict[ImpactLevel, int] = {
    ImpactLevel.LOW: 5,
    ImpactLevel.MEDIUM: 12,
    ImpactLevel.HIGH: 22,
    ImpactLevel.CRITICAL: 32,
    ImpactLevel.EXTREME: 40,
}

STATUS_MULTIPLIERS: dict[EventStatus, float] = {
    EventStatus.UPCOMING: 0.25,
    EventStatus.IMMINENT: 1.00,
    EventStatus.REACTION: 1.15,
    EventStatus.STABILIZATION: 0.65,
    EventStatus.COMPLETED: 0.00,
}

SENSITIVITY_MULTIPLIERS: dict[SensitivityLevel, float] = {
    SensitivityLevel.LOW: 0.50,
    SensitivityLevel.MEDIUM: 0.75,
    SensitivityLevel.HIGH: 1.00,
    SensitivityLevel.VERY_HIGH: 1.25,
}


class EventRiskEngine:
    """Evaluate event-driven market and ticker risk."""

    def evaluate_market(
        self,
        calendar: CalendarEvaluation,
    ) -> EventRiskResult:
        """Evaluate market-wide event risk."""
        contributions: list[EventRiskContribution] = []
        reasons: list[str] = []
        warnings: list[str] = list(calendar.warnings)

        for item in calendar.events:
            contribution = self._build_market_contribution(item)

            if contribution.risk_points > 0:
                contributions.append(contribution)

        return self._build_result(
            evaluated_at=calendar.evaluated_at_et,
            scope="MARKET",
            ticker=None,
            contributions=contributions,
            reasons=reasons,
            warnings=warnings,
        )

    def evaluate_ticker(
        self,
        calendar: CalendarEvaluation,
        ticker: str,
    ) -> EventRiskResult:
        """Evaluate event risk for one ticker."""
        normalized = ticker.strip().upper()

        if not normalized:
            raise ValueError("Ticker cannot be empty.")

        contributions: list[EventRiskContribution] = []
        reasons: list[str] = []
        warnings: list[str] = list(calendar.warnings)
        relevant_events = 0

        for item in calendar.events:
            affected_asset = next(
                (
                    asset
                    for asset in item.event.affected_assets
                    if asset.ticker == normalized
                ),
                None,
            )

            if affected_asset is None:
                continue

            relevant_events += 1

            contribution = self._build_ticker_contribution(
                item=item,
                ticker=normalized,
                sensitivity=affected_asset.sensitivity,
                transmission_channel=(
                    affected_asset.transmission_channel
                ),
            )

            if contribution.risk_points > 0:
                contributions.append(contribution)

        if relevant_events == 0:
            reasons.append(
                f"No configured economic or market events currently "
                f"map directly to {normalized}."
            )

        return self._build_result(
            evaluated_at=calendar.evaluated_at_et,
            scope="TICKER",
            ticker=normalized,
            contributions=contributions,
            reasons=reasons,
            warnings=warnings,
            relevant_event_count=relevant_events,
        )

    def explain(
        self,
        result: EventRiskResult,
    ) -> str:
        """Return a concise explanation of one risk result."""
        subject = result.ticker or "the overall market"

        if not result.contributions:
            return (
                f"Event risk for {subject} is {result.risk_level.value}. "
                f"No active configured events currently contribute "
                f"meaningful risk. {result.recommendation}"
            )

        strongest = max(
            result.contributions,
            key=lambda item: item.risk_points,
        )

        return (
            f"Event risk for {subject} is "
            f"{result.risk_level.value} "
            f"with a score of {result.risk_score}/100. "
            f"The largest contribution comes from "
            f"{strongest.short_name}, currently in the "
            f"{strongest.event_status.value} state. "
            f"{strongest.explanation} "
            f"{result.recommendation}"
        )

    def report(
        self,
        result: EventRiskResult,
    ) -> str:
        """Return a readable event-risk report."""
        lines: list[str] = []

        lines.append("=" * 88)
        lines.append("PATCC EVENT RISK ENGINE v0.1")
        lines.append("=" * 88)
        lines.append(
            f"Evaluated at       : "
            f"{result.evaluated_at_et:%Y-%m-%d %I:%M:%S %p %Z}"
        )
        lines.append(f"Scope              : {result.scope}")
        lines.append(
            f"Ticker             : {result.ticker or 'MARKET-WIDE'}"
        )
        lines.append(
            f"Risk level         : {result.risk_level.value}"
        )
        lines.append(
            f"Risk score         : {result.risk_score}/100"
        )
        lines.append(
            f"Confidence         : {result.confidence}/100"
        )
        lines.append(
            f"Relevant events    : {result.relevant_event_count}"
        )
        lines.append(
            f"Active events      : {result.active_event_count}"
        )
        lines.append(
            f"Highest-risk event : "
            f"{result.highest_risk_event or 'None'}"
        )
        lines.append("-" * 88)
        lines.append("RECOMMENDATION")
        lines.append(result.recommendation)

        if result.reasons:
            lines.append("-" * 88)
            lines.append("REASONS")

            for reason in result.reasons:
                lines.append(f"- {reason}")

        if result.contributions:
            lines.append("-" * 88)
            lines.append("EVENT CONTRIBUTIONS")

            for item in result.contributions:
                lines.append("")
                lines.append(
                    f"{item.short_name} "
                    f"[{item.event_status.value}]"
                )
                lines.append(
                    f"Impact             : {item.impact.value}"
                )
                lines.append(
                    f"Sensitivity        : "
                    f"{item.sensitivity.value if item.sensitivity else 'MARKET'}"
                )
                lines.append(
                    f"Risk contribution  : {item.risk_points}"
                )
                lines.append(
                    f"Explanation        : {item.explanation}"
                )
                lines.append(
                    f"Guidance           : {item.guidance}"
                )

        if result.warnings:
            lines.append("-" * 88)
            lines.append("WARNINGS")

            for warning in result.warnings:
                lines.append(f"- {warning}")

        lines.append("=" * 88)

        return "\n".join(lines)

    def _build_market_contribution(
        self,
        item: EvaluatedEvent,
    ) -> EventRiskContribution:
        """Build market-wide contribution from one event."""
        base = IMPACT_POINTS[item.event.impact]
        multiplier = STATUS_MULTIPLIERS[item.status]
        points = round(base * multiplier)

        explanation = (
            f"{item.event.short_name} has "
            f"{item.event.impact.value} configured impact and is "
            f"currently {item.status.value}. "
            f"{item.status_explanation}"
        )

        return EventRiskContribution(
            event_id=item.event.event_id,
            event_name=item.event.name,
            short_name=item.event.short_name,
            event_status=item.status,
            impact=item.event.impact,
            ticker=None,
            sensitivity=None,
            risk_points=points,
            explanation=explanation,
            guidance=item.event.patcc_guidance,
        )

    def _build_ticker_contribution(
        self,
        item: EvaluatedEvent,
        ticker: str,
        sensitivity: SensitivityLevel,
        transmission_channel: str,
    ) -> EventRiskContribution:
        """Build ticker-specific contribution from one event."""
        base = IMPACT_POINTS[item.event.impact]
        status_multiplier = STATUS_MULTIPLIERS[item.status]
        sensitivity_multiplier = (
            SENSITIVITY_MULTIPLIERS[sensitivity]
        )

        points = round(
            base
            * status_multiplier
            * sensitivity_multiplier
        )

        explanation = (
            f"{ticker} has {sensitivity.value} sensitivity to "
            f"{item.event.short_name}. "
            f"{transmission_channel} "
            f"{item.status_explanation}"
        )

        return EventRiskContribution(
            event_id=item.event.event_id,
            event_name=item.event.name,
            short_name=item.event.short_name,
            event_status=item.status,
            impact=item.event.impact,
            ticker=ticker,
            sensitivity=sensitivity,
            risk_points=points,
            explanation=explanation,
            guidance=item.event.patcc_guidance,
        )

    def _build_result(
        self,
        *,
        evaluated_at: datetime,
        scope: str,
        ticker: Optional[str],
        contributions: list[EventRiskContribution],
        reasons: list[str],
        warnings: list[str],
        relevant_event_count: Optional[int] = None,
    ) -> EventRiskResult:
        """Build the final risk result."""
        active = [
            item
            for item in contributions
            if item.risk_points > 0
        ]

        raw_score = sum(
            item.risk_points
            for item in active
        )

        risk_score = min(100, raw_score)

        highest = (
            max(active, key=lambda item: item.risk_points)
            if active
            else None
        )

        risk_level = self._classify_risk(
            risk_score,
            highest,
        )


        if active:
            reasons.extend(
                self._build_reasons(
                    risk_level=risk_level,
                    highest=highest,
                    active_count=len(active),
                )
            )
        else:
            reasons.append(
                "No active configured events currently contribute "
                "meaningful event risk."
            )

        confidence = self._calculate_confidence(
            contributions=active,
            warnings=warnings,
        )

        recommendation = self._recommendation(
            risk_level=risk_level,
            scope=scope,
            ticker=ticker,
        )

        return EventRiskResult(
            evaluated_at_et=evaluated_at,
            scope=scope,
            ticker=ticker,
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=confidence,
            active_event_count=len(active),
            relevant_event_count=(
                relevant_event_count
                if relevant_event_count is not None
                else len(contributions)
            ),
            highest_risk_event=(
                highest.short_name if highest else None
            ),
            contributions=tuple(
                sorted(
                    active,
                    key=lambda item: item.risk_points,
                    reverse=True,
                )
            ),
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            recommendation=recommendation,
        )

    @staticmethod
    def _classify_risk(
        score: int,
        highest: Optional[EventRiskContribution],
    ) -> EventRiskLevel:
        """Translate score and strongest event into operational risk."""

        if highest is None or score == 0:
            return EventRiskLevel.NONE

        if (
            highest.event_status in {
                EventStatus.IMMINENT,
                EventStatus.REACTION,
            }
            and highest.impact in {
                ImpactLevel.HIGH,
                ImpactLevel.CRITICAL,
                ImpactLevel.EXTREME,
            }
        ):
            if highest.risk_points >= 40:
                return EventRiskLevel.CRITICAL

            return EventRiskLevel.HIGH

        if score < 15:
            return EventRiskLevel.LOW

        if score < 35:
            return EventRiskLevel.MODERATE

        if score < 65:
            return EventRiskLevel.HIGH

        return EventRiskLevel.CRITICAL


    @staticmethod
    def _calculate_confidence(
        contributions: list[EventRiskContribution],
        warnings: list[str],
    ) -> int:
        """Calculate confidence in the event-risk result."""
        score = 95

        if not contributions:
            score -= 10

        score -= min(len(warnings) * 5, 25)

        return max(0, min(100, score))

    @staticmethod
    def _build_reasons(
        *,
        risk_level: EventRiskLevel,
        highest: EventRiskContribution,
        active_count: int,
    ) -> list[str]:
        """Build explainable risk reasons."""
        return [
            (
                f"{active_count} active configured event(s) "
                f"contribute to the current assessment."
            ),
            (
                f"The highest-risk active event is "
                f"{highest.short_name}, contributing "
                f"{highest.risk_points} points."
            ),
            (
                f"The combined event-risk classification is "
                f"{risk_level.value}."
            ),
        ]

    @staticmethod
    def _recommendation(
        *,
        risk_level: EventRiskLevel,
        scope: str,
        ticker: Optional[str],
    ) -> str:
        """Return decision-support guidance, not an execution order."""
        subject = ticker or "market decisions"

        if risk_level == EventRiskLevel.NONE:
            return (
                f"No meaningful configured event risk currently "
                f"affects {subject}. Continue normal validation."
            )

        if risk_level == EventRiskLevel.LOW:
            return (
                f"Event risk for {subject} is low. Continue standard "
                f"data-freshness and technical confirmation checks."
            )

        if risk_level == EventRiskLevel.MODERATE:
            return (
                f"Event risk for {subject} is moderate. Review the "
                f"next event and require normal confirmation before "
                f"acting."
            )

        if risk_level == EventRiskLevel.HIGH:
            return (
                f"Event risk for {subject} is high. Treat existing "
                f"signals as provisional and refresh affected market "
                f"data after the event or reaction window."
            )

        return (
            f"Event risk for {subject} is critical. Require explicit "
            f"human review, fresh post-event data and renewed technical "
            f"confirmation before assigning high confidence."
        )


def main() -> int:
    """Run a standalone market-wide and XLE event-risk report."""
    calendar_engine = EconomicCalendarEngine()
    calendar_engine.load()
    calendar = calendar_engine.evaluate()

    risk_engine = EventRiskEngine()

    market_result = risk_engine.evaluate_market(calendar)
    xle_result = risk_engine.evaluate_ticker(
        calendar,
        "XLE",
    )

    print(risk_engine.report(market_result))
    print()
    print(risk_engine.report(xle_result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
