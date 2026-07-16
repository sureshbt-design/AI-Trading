"""
market_clock.py

PATCC Market Clock Engine

Responsibilities
----------------
- Determine the current US equity-market phase
- Distinguish market status from market phase
- Calculate the next scheduled market transition
- Describe the operational meaning of the current phase
- Return structured, explainable market-time context
- Support deterministic testing with supplied timestamps

This module does not:
- Download market data
- Load economic-calendar events
- Determine exchange holidays or early closes yet
- Generate trading recommendations
- Submit orders

Version: 0.1.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo


EASTERN_TIME = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


class MarketStatus(str, Enum):
    """High-level US equity-market status."""

    CLOSED = "CLOSED"
    PRE_MARKET = "PRE_MARKET"
    OPEN = "OPEN"
    AFTER_HOURS = "AFTER_HOURS"


class MarketPhase(str, Enum):
    """Operational phase of the US equity-market day."""

    WEEKEND = "WEEKEND"
    OVERNIGHT = "OVERNIGHT"
    PRE_MARKET = "PRE_MARKET"
    PRE_OPEN = "PRE_OPEN"
    OPENING = "OPENING"
    REGULAR = "REGULAR"
    MIDDAY = "MIDDAY"
    GLOBAL_TRANSITION = "GLOBAL_TRANSITION"
    POWER_HOUR = "POWER_HOUR"
    CLOSING_PHASE = "CLOSING_PHASE"
    AFTER_HOURS = "AFTER_HOURS"
    POST_MARKET = "POST_MARKET"
    HOLIDAY = "HOLIDAY"
    EARLY_CLOSE = "EARLY_CLOSE"
    UNKNOWN = "UNKNOWN"


class ReadinessLevel(str, Enum):
    """
    Decision-support readiness.

    This is informational. It does not authorize or prohibit trading.
    """

    HIGH = "HIGH"
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    LOW = "LOW"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class SessionBoundary:
    """One named market-time boundary."""

    name: str
    boundary_time: time


@dataclass(frozen=True)
class MarketContext:
    """Structured market-time context for PATCC modules."""

    evaluated_at_et: datetime
    market_date: date
    weekday_name: str
    market_status: MarketStatus
    market_phase: MarketPhase
    readiness: ReadinessLevel
    next_transition_name: str
    next_transition_at_et: Optional[datetime]
    minutes_to_next_transition: Optional[int]
    regular_market_open_at_et: datetime
    regular_market_close_at_et: datetime
    is_regular_market_day: bool
    is_weekend: bool
    is_holiday: bool
    is_early_close: bool
    explanation: str
    warnings: tuple[str, ...]


SESSION_BOUNDARIES: tuple[SessionBoundary, ...] = (
    SessionBoundary("US pre-market begins", time(4, 0)),
    SessionBoundary("Pre-open review phase begins", time(9, 0)),
    SessionBoundary("US regular market opens", time(9, 30)),
    SessionBoundary("Opening phase ends", time(10, 0)),
    SessionBoundary("Midday phase begins", time(11, 30)),
    SessionBoundary("Global transition phase begins", time(13, 30)),
    SessionBoundary("Power hour begins", time(15, 0)),
    SessionBoundary("Closing phase begins", time(15, 30)),
    SessionBoundary("US regular market closes", time(16, 0)),
    SessionBoundary("US after-hours ends", time(20, 0)),
)


class MarketClock:
    """
    Determine explainable US market-session context.

    Version 0.1 assumes a normal Monday-through-Friday US session.
    Holiday and early-close calendars will be integrated later.
    """

    def evaluate(
        self,
        evaluated_at: Optional[datetime] = None,
        *,
        holiday_name: Optional[str] = None,
        early_close_time: Optional[time] = None,
    ) -> MarketContext:
        """
        Evaluate market context at a supplied or current timestamp.

        Parameters
        ----------
        evaluated_at:
            Timezone-aware timestamp. If omitted, current Eastern time
            is used. A naive supplied timestamp is rejected.

        holiday_name:
            Optional externally supplied holiday description. This allows
            deterministic testing before a full holiday calendar exists.

        early_close_time:
            Optional externally supplied early closing time.
        """
        now_et = self._normalize_timestamp(evaluated_at)
        market_date = now_et.date()
        is_weekend = now_et.weekday() >= 5
        is_holiday = bool(holiday_name)
        is_early_close = early_close_time is not None

        regular_open = self._at_time(market_date, time(9, 30))
        normal_close = self._at_time(market_date, time(16, 0))
        regular_close = (
            self._at_time(market_date, early_close_time)
            if early_close_time is not None
            else normal_close
        )

        warnings: list[str] = []

        if holiday_name is None:
            warnings.append(
                "Exchange holiday calendar is not integrated in v0.1."
            )

        if early_close_time is None:
            warnings.append(
                "Early-close calendar is not integrated in v0.1."
            )

        if is_holiday:
            status = MarketStatus.CLOSED
            phase = MarketPhase.HOLIDAY
            readiness = ReadinessLevel.CLOSED
            next_name = "Next regular trading day"
            next_at = self._next_weekday_open(now_et)
            explanation = (
                f"US regular equities are treated as closed because "
                f"{holiday_name} was supplied as a market holiday."
            )

        elif is_weekend:
            status = MarketStatus.CLOSED
            phase = MarketPhase.WEEKEND
            readiness = ReadinessLevel.CLOSED
            next_name = "Next weekday pre-market begins"
            next_at = self._next_weekday_at(now_et, time(4, 0))
            explanation = (
                "It is a weekend. US regular equity trading is closed. "
                "PATCC may perform research, crypto monitoring, report "
                "maintenance, and preparation for the next market day."
            )

        else:
            (
                status,
                phase,
                readiness,
                explanation,
            ) = self._classify_normal_day(
                now_et=now_et,
                regular_close=regular_close,
                is_early_close=is_early_close,
            )

            next_name, next_at = self._next_transition(
                now_et=now_et,
                regular_close=regular_close,
                is_early_close=is_early_close,
            )

        minutes_to_transition = self._minutes_until(
            now_et,
            next_at,
        )

        return MarketContext(
            evaluated_at_et=now_et,
            market_date=market_date,
            weekday_name=now_et.strftime("%A"),
            market_status=status,
            market_phase=phase,
            readiness=readiness,
            next_transition_name=next_name,
            next_transition_at_et=next_at,
            minutes_to_next_transition=minutes_to_transition,
            regular_market_open_at_et=regular_open,
            regular_market_close_at_et=regular_close,
            is_regular_market_day=not is_weekend and not is_holiday,
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            is_early_close=is_early_close,
            explanation=explanation,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _normalize_timestamp(
        supplied: Optional[datetime],
    ) -> datetime:
        """Return a timezone-aware Eastern timestamp."""
        if supplied is None:
            return datetime.now(EASTERN_TIME)

        if supplied.tzinfo is None:
            raise ValueError(
                "Supplied market-clock timestamp must be timezone-aware."
            )

        return supplied.astimezone(EASTERN_TIME)

    @staticmethod
    def _at_time(
        day: date,
        clock_time: time,
    ) -> datetime:
        """Create one Eastern timezone-aware datetime."""
        return datetime.combine(
            day,
            clock_time,
            tzinfo=EASTERN_TIME,
        )

    def _classify_normal_day(
        self,
        now_et: datetime,
        regular_close: datetime,
        is_early_close: bool,
    ) -> tuple[
        MarketStatus,
        MarketPhase,
        ReadinessLevel,
        str,
    ]:
        """Classify a normal weekday into a market phase."""
        current = now_et.time()

        if current < time(4, 0):
            return (
                MarketStatus.CLOSED,
                MarketPhase.OVERNIGHT,
                ReadinessLevel.LOW,
                (
                    "US equities are in the overnight phase. Regular and "
                    "pre-market equity sessions have not yet begun. "
                    "Overnight futures, global markets, currencies and "
                    "crypto may still influence the coming US session."
                ),
            )

        if current < time(9, 0):
            return (
                MarketStatus.PRE_MARKET,
                MarketPhase.PRE_MARKET,
                ReadinessLevel.NORMAL,
                (
                    "US pre-market trading is active. PATCC should review "
                    "overnight changes, global-market direction, earnings, "
                    "economic releases and data freshness before treating "
                    "pre-market movements as confirmed."
                ),
            )

        if current < time(9, 30):
            return (
                MarketStatus.PRE_MARKET,
                MarketPhase.PRE_OPEN,
                ReadinessLevel.CAUTION,
                (
                    "The market is in the final pre-open phase. Opening "
                    "auction imbalances, overnight news and scheduled "
                    "economic events can materially affect the opening "
                    "price-discovery process."
                ),
            )

        if current < time(10, 0):
            return (
                MarketStatus.OPEN,
                MarketPhase.OPENING,
                ReadinessLevel.CAUTION,
                (
                    "The US regular session is in its opening phase. "
                    "Liquidity is generally high, but gaps, auction flows "
                    "and rapid price discovery can produce unstable early "
                    "signals. PATCC should emphasize confirmation and data "
                    "freshness rather than treating time alone as a rule."
                ),
            )

        if current < time(11, 30):
            return (
                MarketStatus.OPEN,
                MarketPhase.REGULAR,
                ReadinessLevel.HIGH,
                (
                    "The regular session is established after the opening "
                    "phase. Opening imbalances have had time to settle, so "
                    "cross-asset confirmation and trend persistence can be "
                    "evaluated with improved context."
                ),
            )

        if current < time(13, 30):
            return (
                MarketStatus.OPEN,
                MarketPhase.MIDDAY,
                ReadinessLevel.NORMAL,
                (
                    "The US market is in the midday phase. Trading volume "
                    "and directional conviction may be lower than during "
                    "the open and close, so signals should be checked for "
                    "adequate liquidity and follow-through."
                ),
            )

        if current < time(15, 0):
            return (
                MarketStatus.OPEN,
                MarketPhase.GLOBAL_TRANSITION,
                ReadinessLevel.NORMAL,
                (
                    "The market is in the US afternoon and global-transition "
                    "phase. Major non-US sessions are largely complete, and "
                    "US investors may reassess global closes, yields, "
                    "currencies, commodities and afternoon event risk."
                ),
            )

        closing_phase_start = regular_close - timedelta(minutes=30)
        power_hour_start = regular_close - timedelta(hours=1)

        if now_et < power_hour_start:
            return (
                MarketStatus.OPEN,
                MarketPhase.GLOBAL_TRANSITION,
                ReadinessLevel.NORMAL,
                (
                    "The US afternoon session remains active. PATCC should "
                    "compare afternoon leadership with the morning thesis "
                    "and identify meaningful changes before the final hour."
                ),
            )

        if now_et < closing_phase_start:
            return (
                MarketStatus.OPEN,
                MarketPhase.POWER_HOUR,
                ReadinessLevel.CAUTION,
                (
                    "The final trading hour has begun. Institutional flows, "
                    "position adjustments and closing preparation can "
                    "increase volume and volatility."
                ),
            )

        if now_et < regular_close:
            phase = (
                MarketPhase.EARLY_CLOSE
                if is_early_close
                else MarketPhase.CLOSING_PHASE
            )

            return (
                MarketStatus.OPEN,
                phase,
                ReadinessLevel.CAUTION,
                (
                    "The regular session is in its final 30 minutes. "
                    "Closing-auction preparation, index activity and "
                    "institutional rebalancing may materially affect price "
                    "and volume. This is context, not an automatic trading "
                    "restriction."
                ),
            )

        if current < time(20, 0):
            return (
                MarketStatus.AFTER_HOURS,
                MarketPhase.AFTER_HOURS,
                ReadinessLevel.LOW,
                (
                    "The regular US session is closed and after-hours "
                    "trading is active. Liquidity may be thinner and spreads "
                    "wider. PATCC should distinguish regular-session closes "
                    "from after-hours price movements."
                ),
            )

        return (
            MarketStatus.CLOSED,
            MarketPhase.POST_MARKET,
            ReadinessLevel.CLOSED,
            (
                "US equity after-hours trading has ended. PATCC may perform "
                "end-of-day review, archive results, evaluate outcomes and "
                "prepare the next market-day watchlist."
            ),
        )

    def _next_transition(
        self,
        now_et: datetime,
        regular_close: datetime,
        is_early_close: bool,
    ) -> tuple[str, datetime]:
        """Return the next market-time transition."""
        day = now_et.date()

        dynamic_boundaries: list[tuple[str, datetime]] = [
            (
                "US pre-market begins",
                self._at_time(day, time(4, 0)),
            ),
            (
                "Pre-open review phase begins",
                self._at_time(day, time(9, 0)),
            ),
            (
                "US regular market opens",
                self._at_time(day, time(9, 30)),
            ),
            (
                "Opening phase ends",
                self._at_time(day, time(10, 0)),
            ),
            (
                "Midday phase begins",
                self._at_time(day, time(11, 30)),
            ),
            (
                "Global transition phase begins",
                self._at_time(day, time(13, 30)),
            ),
            (
                "Final trading hour begins",
                regular_close - timedelta(hours=1),
            ),
            (
                "Closing phase begins",
                regular_close - timedelta(minutes=30),
            ),
            (
                (
                    "Early US regular market close"
                    if is_early_close
                    else "US regular market closes"
                ),
                regular_close,
            ),
            (
                "US after-hours trading ends",
                self._at_time(day, time(20, 0)),
            ),
        ]

        for name, transition_at in dynamic_boundaries:
            if transition_at > now_et:
                return name, transition_at

        next_pre_market = self._next_weekday_at(
            now_et,
            time(4, 0),
        )

        return (
            "Next weekday pre-market begins",
            next_pre_market,
        )

    def _next_weekday_at(
        self,
        now_et: datetime,
        clock_time: time,
    ) -> datetime:
        """Return the next Monday-through-Friday timestamp."""
        candidate_date = now_et.date() + timedelta(days=1)

        while candidate_date.weekday() >= 5:
            candidate_date += timedelta(days=1)

        return self._at_time(candidate_date, clock_time)

    def _next_weekday_open(
        self,
        now_et: datetime,
    ) -> datetime:
        """Return the next weekday 9:30 AM Eastern open."""
        return self._next_weekday_at(
            now_et,
            time(9, 30),
        )

    @staticmethod
    def _minutes_until(
        now_et: datetime,
        future_at: Optional[datetime],
    ) -> Optional[int]:
        """Return whole minutes until a future transition."""
        if future_at is None:
            return None

        seconds = (future_at - now_et).total_seconds()

        if seconds <= 0:
            return 0

        return int((seconds + 59) // 60)


def format_timestamp(value: Optional[datetime]) -> str:
    """Format an Eastern timestamp for readable output."""
    if value is None:
        return "Not available"

    return value.astimezone(EASTERN_TIME).strftime(
        "%Y-%m-%d %I:%M:%S %p ET"
    )


def print_context(context: MarketContext) -> None:
    """Print a readable PATCC Market Clock report."""
    print("=" * 78)
    print("PATCC MARKET CLOCK ENGINE v0.1")
    print("=" * 78)
    print(
        f"Evaluated at       : "
        f"{format_timestamp(context.evaluated_at_et)}"
    )
    print(f"Market date        : {context.market_date}")
    print(f"Weekday            : {context.weekday_name}")
    print(f"Market status      : {context.market_status.value}")
    print(f"Market phase       : {context.market_phase.value}")
    print(f"Readiness          : {context.readiness.value}")
    print(
        f"Regular open       : "
        f"{format_timestamp(context.regular_market_open_at_et)}"
    )
    print(
        f"Regular close      : "
        f"{format_timestamp(context.regular_market_close_at_et)}"
    )
    print(f"Next transition    : {context.next_transition_name}")
    print(
        f"Transition time    : "
        f"{format_timestamp(context.next_transition_at_et)}"
    )

    minutes = context.minutes_to_next_transition

    print(
        "Minutes remaining  : "
        f"{minutes if minutes is not None else 'Unknown'}"
    )
    print(f"Regular market day : {context.is_regular_market_day}")
    print(f"Weekend            : {context.is_weekend}")
    print(f"Holiday            : {context.is_holiday}")
    print(f"Early close        : {context.is_early_close}")
    print("-" * 78)
    print("EXPLANATION")
    print(context.explanation)

    if context.warnings:
        print("-" * 78)
        print("WARNINGS")

        for warning in context.warnings:
            print(f"- {warning}")

    print("=" * 78)


def build_test_timestamp(
    hour: int,
    minute: int = 0,
) -> datetime:
    """Build a deterministic weekday test timestamp."""
    test_day = date(2026, 7, 13)

    return datetime(
        test_day.year,
        test_day.month,
        test_day.day,
        hour,
        minute,
        tzinfo=EASTERN_TIME,
    )


def main() -> int:
    """Run a standalone Market Clock evaluation."""
    clock = MarketClock()
    context = clock.evaluate()
    print_context(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    