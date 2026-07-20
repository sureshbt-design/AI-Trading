"""
executive_brief_engine.py

PATCC Executive Brief Engine v0.3

This version replaces deterministic sample values with authoritative
results from the scoring and multi-timeframe engines.

Methodology is unchanged. The engine only orchestrates, classifies,
and presents existing PATCC evidence in a concise one-screen report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List
from zoneinfo import ZoneInfo

from Core.multi_timeframe_engine import (
    MultiTimeframeEngine,
    compact_row as mtf_compact_row,
    resolve_profile,
)
from Core.scoring_engine import (
    analyze_ticker,
    compact_row as daily_compact_row,
)


EASTERN = ZoneInfo("America/New_York")


DEFAULT_UNIVERSE = (
    "SPY",
    "QQQ",
    "XLV",
    "XLF",
    "XLK",
    "XLE",
    "HYG",
    "TQQQ",
    "TLT",
    "SOXL",
    "UNG",
    "GLD",
    "SLV",
    "URA",
    "URNM",
)


@dataclass(frozen=True)
class ExecutiveAction:
    """One prioritized action for the next decision window."""

    priority: str
    title: str
    explanation: str


@dataclass(frozen=True)
class Candidate:
    ticker: str
    daily_score: int
    fusion_score: int | None
    trend: str
    footprint: str
    status: str


@dataclass(frozen=True)
class ExecutiveBrief:
    """Compact PATCC executive briefing model."""

    generated_at: datetime

    day_name: str
    market_status: str
    operating_mode: str
    recommended_activity: str

    system_health: str
    market_bias: str
    market_readiness: str
    highest_event_risk: str

    leading_candidates: List[Candidate] = field(
        default_factory=list
    )
    watch_list: List[Candidate] = field(
        default_factory=list
    )
    avoid_list: List[Candidate] = field(
        default_factory=list
    )
    action_items: List[ExecutiveAction] = field(
        default_factory=list
    )

    confidence_score: int = 0
    failures: List[str] = field(default_factory=list)


class ExecutiveBriefEngine:
    """PATCC executive-summary orchestrator."""

    VERSION = "0.3"

    def __init__(
        self,
        universe: tuple[str, ...] = DEFAULT_UNIVERSE,
        mtf_top_n: int = 3,
    ) -> None:
        self.universe = universe
        self.mtf_top_n = mtf_top_n

    @staticmethod
    def market_status(
        now: datetime,
    ) -> str:
        """
        Determine regular U.S. equity-session status in Eastern Time.

        This intentionally does not claim holiday awareness. On a
        weekday holiday it reports CLOSED / CALENDAR CHECK.
        """

        local = now.astimezone(EASTERN)

        if local.weekday() >= 5:
            return "CLOSED"

        current = local.time()

        if time(9, 30) <= current < time(16, 0):
            return "OPEN"

        if time(4, 0) <= current < time(9, 30):
            return "PRE-MARKET"

        if time(16, 0) <= current < time(20, 0):
            return "AFTER HOURS"

        return "CLOSED"

    def generate(self) -> ExecutiveBrief:
        now = datetime.now(EASTERN)

        daily_results: list[dict] = []
        failures: list[str] = []

        for ticker in self.universe:
            try:
                analysis = analyze_ticker(
                    ticker=ticker,
                    mode="swing",
                    timeframe="1d",
                )
                daily_results.append(
                    {
                        "analysis": analysis,
                        "summary": daily_compact_row(
                            analysis
                        ),
                    }
                )
            except Exception as exc:
                failures.append(
                    f"{ticker}: {exc}"
                )

        daily_results.sort(
            key=lambda item: item["summary"]["score"],
            reverse=True,
        )

        mtf_engine = MultiTimeframeEngine()
        mtf_by_ticker: dict[str, dict] = {}

        mtf_candidates = [
            item
            for item in daily_results
            if item["summary"]["score"] >= 55
        ][: self.mtf_top_n]

        for item in mtf_candidates:
            ticker = item["summary"]["ticker"]

            try:
                profile = resolve_profile(ticker)
                analyses, fusion = mtf_engine.run(
                    ticker=ticker,
                    profile=profile,
                    live_entry=False,
                )
                mtf_by_ticker[ticker] = mtf_compact_row(
                    ticker,
                    analyses,
                    fusion,
                )
            except Exception as exc:
                failures.append(
                    f"{ticker} MTF: {exc}"
                )

        leading: list[Candidate] = []
        watch: list[Candidate] = []
        avoid: list[Candidate] = []

        for item in daily_results:
            summary = item["summary"]
            ticker = summary["ticker"]
            mtf = mtf_by_ticker.get(ticker)

            fusion_score = (
                mtf["fusion"]
                if mtf is not None
                else None
            )

            mtf_status = (
                mtf["status"]
                if mtf is not None
                else summary["status"]
            )

            candidate = Candidate(
                ticker=ticker,
                daily_score=summary["score"],
                fusion_score=fusion_score,
                trend=summary["trend"],
                footprint=summary["footprint"],
                status=mtf_status,
            )

            if mtf_status.startswith("QUALIFIED"):
                leading.append(candidate)
            elif (
                summary["score"] >= 70
                and mtf_status.startswith("WAIT")
            ):
                leading.append(candidate)
            elif (
                summary["score"] >= 55
                and not mtf_status.startswith("AVOID")
            ):
                watch.append(candidate)
            elif summary["score"] < 40 or mtf_status.startswith(
                "AVOID"
            ):
                avoid.append(candidate)
            else:
                watch.append(candidate)

        leading = leading[:3]
        watch = watch[:4]
        avoid = sorted(
            avoid,
            key=lambda item: item.daily_score,
        )[:6]

        spy = next(
            (
                item["summary"]
                for item in daily_results
                if item["summary"]["ticker"] == "SPY"
            ),
            None,
        )

        qqq = next(
            (
                item["summary"]
                for item in daily_results
                if item["summary"]["ticker"] == "QQQ"
            ),
            None,
        )

        benchmark_scores = [
            item["score"]
            for item in (spy, qqq)
            if item is not None
        ]

        average_benchmark = (
            sum(benchmark_scores) / len(benchmark_scores)
            if benchmark_scores
            else 50
        )

        if average_benchmark >= 70:
            market_bias = "BULLISH"
        elif average_benchmark >= 55:
            market_bias = "MIXED BULLISH"
        elif average_benchmark >= 40:
            market_bias = "NEUTRAL / MIXED"
        else:
            market_bias = "DEFENSIVE"

        if leading:
            readiness = "MODERATE"
            activity = "SELECTIVE - WAIT FOR CONFIRMATION"
        else:
            readiness = "LOW"
            activity = "RISK CONTROL - NO FORCED TRADES"

        health = "PASS" if not failures else "PARTIAL"

        confidence = max(
            0,
            min(
                100,
                int(
                    80
                    - min(len(failures) * 5, 30)
                ),
            ),
        )

        actions: list[ExecutiveAction] = []

        if leading:
            names = ", ".join(
                item.ticker
                for item in leading[:2]
            )

            actions.append(
                ExecutiveAction(
                    priority="HIGH",
                    title=f"Validate {names}",
                    explanation=(
                        "Require live price above VWAP, rising DEMA-8, "
                        "and improving participation before entry."
                    ),
                )
            )
        else:
            actions.append(
                ExecutiveAction(
                    priority="HIGH",
                    title="Preserve capital",
                    explanation=(
                        "No candidate has complete confirmation. "
                        "Do not force a trade."
                    ),
                )
            )

        actions.append(
            ExecutiveAction(
                priority="HIGH",
                title="Use the Opportunity Queue",
                explanation=(
                    "Review daily score, fusion score, footprint, "
                    "and final status together; do not use score alone."
                ),
            )
        )

        actions.append(
            ExecutiveAction(
                priority="MEDIUM",
                title="Respect session context",
                explanation=(
                    "Daily Yahoo Finance data qualifies candidates; "
                    "live execution requires next-session confirmation."
                ),
            )
        )

        return ExecutiveBrief(
            generated_at=now,
            day_name=now.strftime("%A"),
            market_status=self.market_status(now),
            operating_mode="RESEARCH / WATCHLIST",
            recommended_activity=activity,
            system_health=health,
            market_bias=market_bias,
            market_readiness=readiness,
            highest_event_risk=(
                "ENERGY / LEVERAGED ETF VOLATILITY"
            ),
            leading_candidates=leading,
            watch_list=watch,
            avoid_list=avoid,
            action_items=actions,
            confidence_score=confidence,
            failures=failures,
        )

    @staticmethod
    def _candidate_line(
        item: Candidate,
    ) -> str:
        fusion = (
            f"{item.fusion_score:>3}"
            if item.fusion_score is not None
            else "  -"
        )

        return (
            f"{item.ticker:<6} "
            f"{item.daily_score:>5} "
            f"{fusion:>6} "
            f"{item.trend:<15.15} "
            f"{item.footprint:<20.20} "
            f"{item.status}"
        )

    def report(self, brief: ExecutiveBrief) -> str:
        lines: List[str] = []

        separator = "=" * 112
        divider = "-" * 112

        lines.append(separator)
        lines.append(
            f"PATCC EXECUTIVE BRIEF v{self.VERSION}"
            f"  |  {brief.generated_at:%Y-%m-%d %I:%M %p %Z}"
        )
        lines.append(separator)

        lines.append(
            f"Day: {brief.day_name:<10} "
            f"Market: {brief.market_status:<12} "
            f"Mode: {brief.operating_mode}"
        )

        lines.append(
            f"Health: {brief.system_health:<7} "
            f"Bias: {brief.market_bias:<16} "
            f"Readiness: {brief.market_readiness:<10} "
            f"Confidence: {brief.confidence_score}%"
        )

        lines.append(
            f"Activity: {brief.recommended_activity}"
        )
        lines.append(
            f"Highest Risk: {brief.highest_event_risk}"
        )

        lines.append("")
        lines.append(
            "LEADING CANDIDATES - REQUIRE CONFIRMATION"
        )
        lines.append(divider)
        lines.append(
            "Ticker Daily Fusion Trend           "
            "Footprint            Final Status"
        )

        if brief.leading_candidates:
            for item in brief.leading_candidates:
                lines.append(
                    self._candidate_line(item)
                )
        else:
            lines.append(
                "None currently meet the leading-candidate gate."
            )

        lines.append("")
        lines.append("WATCH / WAIT")
        lines.append(divider)

        if brief.watch_list:
            for item in brief.watch_list:
                lines.append(
                    self._candidate_line(item)
                )
        else:
            lines.append("None.")

        lines.append("")
        lines.append("AVOID / RISK CONTROL")
        lines.append(divider)

        if brief.avoid_list:
            compact = " | ".join(
                (
                    f"{item.ticker} "
                    f"D{item.daily_score}"
                )
                for item in brief.avoid_list
            )
            lines.append(compact)
        else:
            lines.append("None.")

        lines.append("")
        lines.append("NEXT ACTIONS")
        lines.append(divider)

        for index, action in enumerate(
            brief.action_items,
            start=1,
        ):
            lines.append(
                f"{index}. [{action.priority}] {action.title}"
            )
            lines.append(
                f"   {action.explanation}"
            )

        if brief.failures:
            lines.append("")
            lines.append(
                f"Data warnings: {len(brief.failures)} "
                "ticker/timeframe failure(s)."
            )

        lines.append("")
        lines.append(
            "NOTE: Daily Yahoo Finance data is decision support, "
            "not a real-time entry signal."
        )
        lines.append(separator)

        return "\n".join(lines)


def main() -> None:
    engine = ExecutiveBriefEngine()
    brief = engine.generate()
    print(engine.report(brief))


if __name__ == "__main__":
    main()
