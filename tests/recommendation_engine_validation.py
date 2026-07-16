"""
recommendation_engine_validation.py

PATCC Recommendation Engine operational validation.

Run:
    python -m Tests.recommendation_engine_validation
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

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
from Core.recommendation_engine import (
    AssetContext,
    DecisionState,
    RecommendationEngine,
    RecommendationInput,
    TechnicalEvidence,
)


EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class ValidationScenario:
    name: str
    expected: DecisionState
    recommendation_input: RecommendationInput


def enum_member(
    enum_class: type[Enum],
    *candidates: str,
) -> Enum:
    """
    Resolve an enum member by either its name or value.

    This keeps the validation script tolerant of descriptive enum values
    while still failing clearly when the expected operating state is absent.
    """
    normalized_candidates = {
        candidate.strip().upper().replace(" ", "_")
        for candidate in candidates
    }

    for member in enum_class:
        normalized_name = member.name.upper().replace(" ", "_")
        normalized_value = str(member.value).upper().replace(" ", "_")

        if (
            normalized_name in normalized_candidates
            or normalized_value in normalized_candidates
        ):
            return member

    available = ", ".join(
        f"{member.name}={member.value}"
        for member in enum_class
    )

    raise ValueError(
        f"Unable to resolve {enum_class.__name__} from "
        f"{candidates}. Available members: {available}"
    )


def build_market_context(
    *,
    readiness: ReadinessLevel | None = None,
    market_status: MarketStatus | None = None,
) -> MarketContext:
    now = datetime.now(EASTERN)

    resolved_status = market_status or enum_member(
        MarketStatus,
        "OPEN",
        "REGULAR_OPEN",
        "REGULAR_MARKET_OPEN",
    )

    resolved_phase = enum_member(
        MarketPhase,
        "REGULAR",
        "REGULAR_MARKET",
        "MARKET_OPEN",
        "OPEN",
    )

    resolved_readiness = readiness or enum_member(
        ReadinessLevel,
        "HIGH",
        "NORMAL",
    )

    market_open = now.replace(
        hour=9,
        minute=30,
        second=0,
        microsecond=0,
    )
    market_close = now.replace(
        hour=16,
        minute=0,
        second=0,
        microsecond=0,
    )

    return MarketContext(
        evaluated_at_et=now,
        market_date=date.today(),
        weekday_name=now.strftime("%A"),
        market_status=resolved_status,
        market_phase=resolved_phase,
        readiness=resolved_readiness,
        next_transition_name="Regular market close",
        next_transition_at_et=market_close,
        minutes_to_next_transition=max(
            0,
            int((market_close - now).total_seconds() / 60),
        ),
        regular_market_open_at_et=market_open,
        regular_market_close_at_et=market_close,
        is_regular_market_day=True,
        is_weekend=False,
        is_holiday=False,
        is_early_close=False,
        explanation="Synthetic regular-market validation context.",
        warnings=(),
    )


def build_data_quality(
    ticker: str,
    *,
    status: QualityStatus,
    freshness: FreshnessStatus,
    quality_score: int,
) -> DataQualityResult:
    now = datetime.now(EASTERN)

    if freshness == FreshnessStatus.STALE:
        age = timedelta(days=3)
    elif freshness == FreshnessStatus.UNKNOWN:
        age = timedelta.max
    else:
        age = timedelta(minutes=2)

    return DataQualityResult(
        symbol=ticker,
        status=status,
        freshness=freshness,
        quality_score=quality_score,
        age=age,
        age_description=(
            "Unknown"
            if age == timedelta.max
            else str(age)
        ),
        provider="Validation Provider",
        timeframe="1d",
        market_session="Regular",
        data_mode="Validation",
        observation_time=now - timedelta(minutes=2),
        fetched_at=now,
        warnings=(),
        errors=(
            ("Synthetic data-quality failure.",)
            if status == QualityStatus.FAIL
            else ()
        ),
    )


def build_event_risk(
    ticker: str,
    *,
    level: EventRiskLevel,
    score: int,
) -> EventRiskResult:
    now = datetime.now(EASTERN)

    has_risk = score > 0

    return EventRiskResult(
        evaluated_at_et=now,
        scope="TICKER",
        ticker=ticker,
        risk_level=level,
        risk_score=score,
        confidence=95,
        active_event_count=1 if has_risk else 0,
        relevant_event_count=1 if has_risk else 0,
        highest_risk_event=(
            "Synthetic Validation Event"
            if has_risk
            else None
        ),
        contributions=(),
        reasons=(
            (
                f"Synthetic {level.value} event-risk scenario."
            )
            if has_risk
            else (
                "No meaningful configured event risk.",
            )
        ),
        warnings=(),
        recommendation="Synthetic event-risk validation result.",
    )


def build_input(
    *,
    ticker: str,
    technical_score: int,
    inverse: bool = False,
    event_level: EventRiskLevel,
    event_score: int,
    quality_status: QualityStatus = QualityStatus.PASS,
    freshness: FreshnessStatus = FreshnessStatus.FRESH,
    quality_score: int = 100,
) -> RecommendationInput:
    technical = TechnicalEvidence(
        ticker=ticker,
        score=technical_score,
        grade=(
            "A"
            if technical_score >= 85
            else "B"
            if technical_score >= 70
            else "F"
        ),
        trend=(
            "Strong Bullish"
            if technical_score >= 75
            else "Bearish"
        ),
        action=(
            "Good Candidate"
            if technical_score >= 70
            else "Avoid"
        ),
        momentum=(
            "Bullish"
            if technical_score >= 70
            else "Weak"
        ),
        volatility="Low",
        volume="Above Average",
        risk_level=(
            "Aggressive"
            if inverse
            else "Conservative"
        ),
    )

    asset = AssetContext(
        ticker=ticker,
        priority=1,
        asset_class="ETF",
        category=(
            "Inverse ETF"
            if inverse
            else "Validation ETF"
        ),
        market_role=(
            "Hedge"
            if inverse
            else "Tactical Opportunity"
        ),
        tactical=True,
        inverse=inverse,
        leveraged=inverse,
    )

    return RecommendationInput(
        technical=technical,
        asset=asset,
        data_quality=build_data_quality(
            ticker,
            status=quality_status,
            freshness=freshness,
            quality_score=quality_score,
        ),
        market_context=build_market_context(),
        event_risk=build_event_risk(
            ticker,
            level=event_level,
            score=event_score,
        ),
    )


def build_scenarios() -> tuple[ValidationScenario, ...]:
    low_event = enum_member(
        EventRiskLevel,
        "LOW",
        "NONE",
    )
    high_event = enum_member(
        EventRiskLevel,
        "HIGH",
    )

    return (
        ValidationScenario(
            name="Strong setup with low event risk",
            expected=DecisionState.ACTION,
            recommendation_input=build_input(
                ticker="SPY",
                technical_score=95,
                event_level=low_event,
                event_score=5,
            ),
        ),
        ValidationScenario(
            name="Strong setup with high event risk",
            expected=DecisionState.WATCH,
            recommendation_input=build_input(
                ticker="QQQ",
                technical_score=90,
                event_level=high_event,
                event_score=75,
            ),
        ),
        ValidationScenario(
            name="Weak technical setup",
            expected=DecisionState.AVOID,
            recommendation_input=build_input(
                ticker="UNG",
                technical_score=30,
                event_level=low_event,
                event_score=5,
            ),
        ),
        ValidationScenario(
            name="Stale data blocks recommendation",
            expected=DecisionState.INSUFFICIENT_DATA,
            recommendation_input=build_input(
                ticker="TLT",
                technical_score=90,
                event_level=low_event,
                event_score=5,
                quality_status=QualityStatus.WARN,
                freshness=FreshnessStatus.STALE,
                quality_score=45,
            ),
        ),
        ValidationScenario(
            name="Inverse ETF under event stress",
            expected=DecisionState.HEDGE,
            recommendation_input=build_input(
                ticker="SQQQ",
                technical_score=35,
                inverse=True,
                event_level=high_event,
                event_score=80,
            ),
        ),
    )


def main() -> int:
    engine = RecommendationEngine()
    scenarios = build_scenarios()

    passed = 0
    failed = 0

    print("=" * 92)
    print("PATCC RECOMMENDATION ENGINE VALIDATION v0.1")
    print("=" * 92)

    for number, scenario in enumerate(scenarios, start=1):
        try:
            result = engine.evaluate(
                scenario.recommendation_input
            )

            success = result.decision == scenario.expected

            if success:
                passed += 1
                status = "PASS"
            else:
                failed += 1
                status = "FAIL"

            print(
                f"[{number}/{len(scenarios)}] "
                f"{scenario.name:<42} "
                f"{status}"
            )
            print(
                f"    Expected   : {scenario.expected.value}"
            )
            print(
                f"    Actual     : {result.decision.value}"
            )
            print(
                f"    Confidence : "
                f"{result.confidence_score}/100 "
                f"({result.confidence_level.value})"
            )
            print(
                f"    Ready      : {result.execution_ready}"
            )

            if result.contradictions:
                print(
                    "    Conflicts  : "
                    + "; ".join(result.contradictions)
                )

        except Exception as exc:
            failed += 1

            print(
                f"[{number}/{len(scenarios)}] "
                f"{scenario.name:<42} ERROR"
            )
            print(
                f"    {type(exc).__name__}: {exc}"
            )

        print("-" * 92)

    total = len(scenarios)

    print(f"Scenarios passed : {passed}")
    print(f"Scenarios failed : {failed}")
    print(f"Total scenarios  : {total}")

    if failed == 0:
        print("OVERALL STATUS   : PASS")
        print("RECOMMENDATION ENGINE VALIDATION COMPLETE")
        exit_code = 0
    else:
        print("OVERALL STATUS   : FAIL")
        print("INVESTIGATION REQUIRED")
        exit_code = 1

    print("=" * 92)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
    