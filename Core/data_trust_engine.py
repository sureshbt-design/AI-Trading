"""
data_trust_engine.py

Evaluates the operational trust characteristics of a validated
MarketDataResponse.

Version 0.1 intentionally distinguishes between:

1. Retrieval trust
   Whether PATCC successfully retrieved and validated data through
   a known provider without operational degradation.

2. Execution suitability
   Whether the provider identifies the response as real-time.

3. Freshness
   Whether the most recent bar is the expected completed bar.

Freshness is reported as NOT EVALUATED until PATCC has interval-aware,
session-aware, holiday-aware market-calendar logic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from Core.market_data_service import (
    MarketDataRequest,
    MarketDataResponse,
    MarketDataService,
)


class TrustLevel(str, Enum):
    """
    Operational trust classification.
    """

    HIGH = "HIGH"
    MODERATE = "MODERATE"
    REDUCED = "REDUCED"
    BLOCKED = "BLOCKED"


class ExecutionSuitability(str, Enum):
    """
    Suitability of the data for execution decisions.
    """

    REAL_TIME = "REAL-TIME"
    RESEARCH_ONLY = "RESEARCH / WATCHLIST"
    UNKNOWN = "UNKNOWN"


class FreshnessStatus(str, Enum):
    """
    Freshness classification.

    Version 0.1 does not infer freshness from a raw bar timestamp.
    """

    NOT_EVALUATED = "NOT EVALUATED"
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DataTrustResult:
    """
    Trust assessment derived from one MarketDataResponse.
    """

    ticker: str
    provider: str
    mode: str
    realtime: bool

    trust_level: TrustLevel
    execution_suitability: ExecutionSuitability
    freshness_status: FreshnessStatus

    requested_at: datetime
    received_at: datetime
    retrieval_seconds: float

    requested_period: str
    requested_interval: str

    last_bar: datetime
    rows: int

    provider_attempt: int
    fallback_used: bool

    checks_passed: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)

    @property
    def can_support_live_entry(self) -> bool:
        """
        Return True only when the response identifies itself as real-time
        and no blocking condition exists.

        Freshness still requires separate validation in a later version.
        """

        return (
            self.realtime
            and not self.blockers
            and self.trust_level != TrustLevel.BLOCKED
        )


class DataTrustEngine:
    """
    Evaluate provider and retrieval metadata without modifying market data.

    This engine does not score price action, indicators, trends, or trade
    opportunities. It evaluates only the operational characteristics of
    the supplied MarketDataResponse.
    """

    FAST_RETRIEVAL_SECONDS = 2.0
    DEGRADED_RETRIEVAL_SECONDS = 5.0

    def evaluate(
        self,
        response: MarketDataResponse,
    ) -> DataTrustResult:
        """
        Evaluate one validated MarketDataResponse.
        """

        checks_passed: list[str] = []
        warnings: list[str] = []
        blockers: list[str] = []

        self._validate_response(
            response=response,
            checks_passed=checks_passed,
            warnings=warnings,
            blockers=blockers,
        )

        trust_level = self._determine_trust_level(
            response=response,
            blockers=blockers,
            warnings=warnings,
        )

        execution_suitability = self._execution_suitability(
            response
        )

        if not response.realtime:
            warnings.append(
                "Provider identifies this response as non-real-time. "
                "Use for research and candidate qualification, not as "
                "a live entry trigger."
            )

        warnings.append(
            "Bar freshness and completion have not yet been evaluated. "
            "Interval-aware market-calendar validation is required."
        )

        return DataTrustResult(
            ticker=response.ticker,
            provider=response.source,
            mode=response.mode,
            realtime=response.realtime,
            trust_level=trust_level,
            execution_suitability=execution_suitability,
            freshness_status=FreshnessStatus.NOT_EVALUATED,
            requested_at=response.requested_at,
            received_at=response.received_at,
            retrieval_seconds=response.retrieval_seconds,
            requested_period=response.requested_period,
            requested_interval=response.requested_interval,
            last_bar=response.last_bar,
            rows=response.rows,
            provider_attempt=response.provider_attempt,
            fallback_used=response.fallback_used,
            checks_passed=tuple(checks_passed),
            warnings=tuple(warnings),
            blockers=tuple(blockers),
        )

    def _validate_response(
        self,
        response: MarketDataResponse,
        checks_passed: list[str],
        warnings: list[str],
        blockers: list[str],
    ) -> None:
        """
        Validate operational response characteristics.
        """

        if not response.ticker:
            blockers.append("Ticker is missing.")
        else:
            checks_passed.append("Ticker identified")

        if not response.source:
            blockers.append("Provider source is missing.")
        else:
            checks_passed.append("Provider identified")

        if response.data is None or response.data.empty:
            blockers.append("Validated market-data frame is empty.")
        else:
            checks_passed.append("Validated market data available")

        if response.rows <= 0:
            blockers.append("Response row count is zero.")
        else:
            checks_passed.append(
                f"{response.rows} validated rows available"
            )

        if response.last_bar is None:
            blockers.append("Latest bar timestamp is unavailable.")
        else:
            checks_passed.append("Latest bar timestamp available")

        if response.received_at < response.requested_at:
            blockers.append(
                "Received timestamp precedes requested timestamp."
            )
        else:
            checks_passed.append("Retrieval timestamps are consistent")

        if response.retrieval_seconds < 0:
            blockers.append("Retrieval duration is negative.")
        elif (
            response.retrieval_seconds
            <= self.FAST_RETRIEVAL_SECONDS
        ):
            checks_passed.append("Provider response time is normal")
        elif (
            response.retrieval_seconds
            <= self.DEGRADED_RETRIEVAL_SECONDS
        ):
            warnings.append(
                "Provider response time is slower than preferred."
            )
        else:
            warnings.append(
                "Provider response time is operationally degraded."
            )

        if response.provider_attempt < 1:
            blockers.append("Provider-attempt number is invalid.")
        elif response.provider_attempt == 1:
            checks_passed.append("Primary provider succeeded")
        else:
            warnings.append(
                f"Data was obtained on provider attempt "
                f"{response.provider_attempt}."
            )

        if response.fallback_used:
            warnings.append(
                "Fallback provider was used after an earlier "
                "provider failure."
            )
        else:
            checks_passed.append("No provider fallback used")

        if not response.requested_interval:
            blockers.append("Requested interval is missing.")
        else:
            checks_passed.append(
                f"Requested interval recorded: "
                f"{response.requested_interval}"
            )

        if not response.requested_period:
            blockers.append("Requested period is missing.")
        else:
            checks_passed.append(
                f"Requested period recorded: "
                f"{response.requested_period}"
            )

    def _determine_trust_level(
        self,
        response: MarketDataResponse,
        blockers: list[str],
        warnings: list[str],
    ) -> TrustLevel:
        """
        Determine operational trust without claiming data freshness.
        """

        if blockers:
            return TrustLevel.BLOCKED

        if (
            response.fallback_used
            or response.provider_attempt > 1
            or response.retrieval_seconds
            > self.DEGRADED_RETRIEVAL_SECONDS
        ):
            return TrustLevel.REDUCED

        if warnings:
            return TrustLevel.MODERATE

        return TrustLevel.HIGH

    @staticmethod
    def _execution_suitability(
        response: MarketDataResponse,
    ) -> ExecutionSuitability:
        """
        Classify the provider-declared execution suitability.
        """

        if response.realtime:
            return ExecutionSuitability.REAL_TIME

        if response.mode:
            return ExecutionSuitability.RESEARCH_ONLY

        return ExecutionSuitability.UNKNOWN

    @staticmethod
    def format_report(
        result: DataTrustResult,
    ) -> str:
        """
        Format the trust assessment for console or report output.
        """

        lines = [
            "=" * 80,
            "PATCC DATA TRUST ASSESSMENT v0.1",
            "=" * 80,
            f"Ticker               : {result.ticker}",
            f"Provider             : {result.provider}",
            f"Provider Mode        : {result.mode}",
            f"Real-Time            : {result.realtime}",
            f"Operational Trust    : {result.trust_level.value}",
            (
                f"Execution Suitability: "
                f"{result.execution_suitability.value}"
            ),
            f"Freshness            : {result.freshness_status.value}",
            "-" * 80,
            (
                f"Requested At         : "
                f"{result.requested_at:%Y-%m-%d %I:%M:%S %p %Z}"
            ),
            (
                f"Received At          : "
                f"{result.received_at:%Y-%m-%d %I:%M:%S %p %Z}"
            ),
            (
                f"Retrieval Time       : "
                f"{result.retrieval_seconds:.3f} seconds"
            ),
            f"Provider Attempt     : {result.provider_attempt}",
            f"Fallback Used        : {result.fallback_used}",
            f"Requested Period     : {result.requested_period}",
            f"Requested Interval   : {result.requested_interval}",
            f"Last Available Bar   : {result.last_bar}",
            f"Validated Rows       : {result.rows}",
            "-" * 80,
            "CHECKS PASSED",
        ]

        if result.checks_passed:
            lines.extend(
                f"  [PASS] {check}"
                for check in result.checks_passed
            )
        else:
            lines.append("  None")

        lines.append("-" * 80)
        lines.append("WARNINGS")

        if result.warnings:
            lines.extend(
                f"  [WARN] {warning}"
                for warning in result.warnings
            )
        else:
            lines.append("  None")

        lines.append("-" * 80)
        lines.append("BLOCKERS")

        if result.blockers:
            lines.extend(
                f"  [BLOCK] {blocker}"
                for blocker in result.blockers
            )
        else:
            lines.append("  None")

        lines.append("-" * 80)
        lines.append(
            f"Live Entry Support   : "
            f"{'YES' if result.can_support_live_entry else 'NO'}"
        )

        if not result.can_support_live_entry:
            lines.append(
                "Decision              : Do not treat this dataset as "
                "a standalone live-entry signal."
            )

        lines.append("=" * 80)

        return "\n".join(lines)


if __name__ == "__main__":
    service = MarketDataService()

    response = service.get_price_history(
        MarketDataRequest(
            ticker="TQQQ",
            period="3mo",
            interval="1d",
        )
    )

    engine = DataTrustEngine()
    result = engine.evaluate(response)

    print(engine.format_report(result))
    