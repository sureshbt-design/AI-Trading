"""
data_quality_engine.py

PATCC Data Quality and Freshness Engine

Responsibilities
----------------
- Record data provider and timestamps
- Calculate observation age
- Evaluate freshness relative to timeframe and market session
- Validate required fields
- Separate warnings from errors
- Produce a data-quality score
- Return PASS, WARN, or FAIL

This module does not download market data and does not generate
investment recommendations.

Version: 0.1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo


EASTERN_TIME = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


class QualityStatus(str, Enum):
    """Overall data-quality result."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class FreshnessStatus(str, Enum):
    """Freshness classification relative to intended use."""

    FRESH = "FRESH"
    CURRENT = "CURRENT"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FreshnessPolicy:
    """Maximum expected data ages for one timeframe."""

    timeframe: str
    fresh_age: timedelta
    current_age: timedelta
    aging_age: timedelta


@dataclass
class DataQualityRecord:
    """Metadata describing one market-data observation."""

    symbol: str
    provider: str
    timeframe: str
    observation_time: datetime
    fetched_at: datetime
    market_session: str
    data_mode: str
    price: Optional[float] = None
    volume: Optional[float] = None
    expected_real_time: bool = False
    provider_reliability: int = 90
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DataQualityResult:
    """Validated data-quality result."""

    symbol: str
    status: QualityStatus
    freshness: FreshnessStatus
    quality_score: int
    age: timedelta
    age_description: str
    provider: str
    timeframe: str
    market_session: str
    data_mode: str
    observation_time: datetime
    fetched_at: datetime
    warnings: tuple[str, ...]
    errors: tuple[str, ...]


FRESHNESS_POLICIES: dict[str, FreshnessPolicy] = {
    "1m": FreshnessPolicy(
        timeframe="1m",
        fresh_age=timedelta(minutes=2),
        current_age=timedelta(minutes=5),
        aging_age=timedelta(minutes=15),
    ),
    "5m": FreshnessPolicy(
        timeframe="5m",
        fresh_age=timedelta(minutes=7),
        current_age=timedelta(minutes=15),
        aging_age=timedelta(minutes=30),
    ),
    "15m": FreshnessPolicy(
        timeframe="15m",
        fresh_age=timedelta(minutes=20),
        current_age=timedelta(minutes=45),
        aging_age=timedelta(hours=2),
    ),
    "1h": FreshnessPolicy(
        timeframe="1h",
        fresh_age=timedelta(hours=1, minutes=15),
        current_age=timedelta(hours=3),
        aging_age=timedelta(hours=8),
    ),
    "4h": FreshnessPolicy(
        timeframe="4h",
        fresh_age=timedelta(hours=5),
        current_age=timedelta(hours=12),
        aging_age=timedelta(days=1),
    ),
    "1d": FreshnessPolicy(
        timeframe="1d",
        fresh_age=timedelta(days=1),
        current_age=timedelta(days=4),
        aging_age=timedelta(days=7),
    ),
    "1wk": FreshnessPolicy(
        timeframe="1wk",
        fresh_age=timedelta(days=8),
        current_age=timedelta(days=15),
        aging_age=timedelta(days=30),
    ),
}


class DataQualityEngine:
    """Validate data provenance, completeness, and freshness."""

    def evaluate(
        self,
        record: DataQualityRecord,
    ) -> DataQualityResult:
        """Evaluate one data-quality record."""
        warnings: list[str] = []
        errors: list[str] = []

        self._validate_record(record, warnings, errors)

        age = self._calculate_age(record, errors)
        freshness = self._classify_freshness(
            record=record,
            age=age,
            warnings=warnings,
        )

        quality_score = self._calculate_quality_score(
            record=record,
            freshness=freshness,
            warnings=warnings,
            errors=errors,
        )

        if errors:
            status = QualityStatus.FAIL
        elif warnings:
            status = QualityStatus.WARN
        else:
            status = QualityStatus.PASS

        return DataQualityResult(
            symbol=record.symbol.strip().upper(),
            status=status,
            freshness=freshness,
            quality_score=quality_score,
            age=age,
            age_description=self._format_age(age),
            provider=record.provider.strip(),
            timeframe=record.timeframe.strip().lower(),
            market_session=record.market_session.strip(),
            data_mode=record.data_mode.strip(),
            observation_time=record.observation_time,
            fetched_at=record.fetched_at,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    @staticmethod
    def _validate_record(
        record: DataQualityRecord,
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Validate required fields and data completeness."""
        if not record.symbol.strip():
            errors.append("Symbol is missing.")

        if not record.provider.strip():
            errors.append("Provider is missing.")

        if not record.timeframe.strip():
            errors.append("Timeframe is missing.")

        if not record.market_session.strip():
            warnings.append("Market session is not specified.")

        if not record.data_mode.strip():
            warnings.append("Data mode is not specified.")

        if record.observation_time.tzinfo is None:
            errors.append(
                "Observation timestamp must be timezone-aware."
            )

        if record.fetched_at.tzinfo is None:
            errors.append(
                "Fetch timestamp must be timezone-aware."
            )

        if record.price is not None and record.price <= 0:
            errors.append("Price must be greater than zero.")

        if record.volume is not None and record.volume < 0:
            errors.append("Volume cannot be negative.")

        if not 0 <= record.provider_reliability <= 100:
            errors.append(
                "Provider reliability must be between 0 and 100."
            )

        if record.price is None:
            warnings.append("Price was not supplied.")

        if record.volume is None:
            warnings.append("Volume was not supplied.")

    @staticmethod
    def _calculate_age(
        record: DataQualityRecord,
        errors: list[str],
    ) -> timedelta:
        """Calculate age between observation and fetch time."""
        if (
            record.observation_time.tzinfo is None
            or record.fetched_at.tzinfo is None
        ):
            return timedelta.max

        observation_utc = record.observation_time.astimezone(UTC)
        fetched_utc = record.fetched_at.astimezone(UTC)
        age = fetched_utc - observation_utc

        if age < timedelta(0):
            errors.append(
                "Observation timestamp is later than fetch timestamp."
            )
            return timedelta(0)

        return age

    def _classify_freshness(
        self,
        record: DataQualityRecord,
        age: timedelta,
        warnings: list[str],
    ) -> FreshnessStatus:
        """Classify freshness relative to timeframe."""
        timeframe = record.timeframe.strip().lower()
        policy = FRESHNESS_POLICIES.get(timeframe)

        if policy is None:
            warnings.append(
                f"No freshness policy exists for timeframe "
                f"{record.timeframe!r}."
            )
            return FreshnessStatus.UNKNOWN

        if age <= policy.fresh_age:
            freshness = FreshnessStatus.FRESH
        elif age <= policy.current_age:
            freshness = FreshnessStatus.CURRENT
        elif age <= policy.aging_age:
            freshness = FreshnessStatus.AGING
            warnings.append(
                "Data is aging for the selected timeframe."
            )
        else:
            freshness = FreshnessStatus.STALE
            warnings.append(
                "Data is stale for the selected timeframe."
            )

        if (
            record.expected_real_time
            and freshness != FreshnessStatus.FRESH
        ):
            warnings.append(
                "Real-time data was expected but was not fresh."
            )

        return freshness

    @staticmethod
    def _calculate_quality_score(
        record: DataQualityRecord,
        freshness: FreshnessStatus,
        warnings: list[str],
        errors: list[str],
    ) -> int:
        """Calculate an explainable score from zero to one hundred."""
        if errors:
            return 0

        score = record.provider_reliability

        freshness_adjustments = {
            FreshnessStatus.FRESH: 0,
            FreshnessStatus.CURRENT: -5,
            FreshnessStatus.AGING: -20,
            FreshnessStatus.STALE: -45,
            FreshnessStatus.UNKNOWN: -25,
        }

        score += freshness_adjustments[freshness]

        if record.price is None:
            score -= 10

        if record.volume is None:
            score -= 5

        score -= min(len(warnings) * 2, 10)

        return max(0, min(100, round(score)))

    @staticmethod
    def _format_age(age: timedelta) -> str:
        """Return a human-readable age description."""
        if age == timedelta.max:
            return "Unknown"

        total_seconds = int(age.total_seconds())

        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts: list[str] = []

        if days:
            parts.append(f"{days}d")

        if hours:
            parts.append(f"{hours}h")

        if minutes:
            parts.append(f"{minutes}m")

        if seconds or not parts:
            parts.append(f"{seconds}s")

        return " ".join(parts)


def print_result(result: DataQualityResult) -> None:
    """Print one readable data-quality report."""
    print("=" * 72)
    print("PATCC DATA QUALITY ENGINE v0.1")
    print("=" * 72)
    print(f"Symbol            : {result.symbol}")
    print(f"Provider          : {result.provider}")
    print(f"Timeframe         : {result.timeframe}")
    print(f"Market session    : {result.market_session}")
    print(f"Data mode         : {result.data_mode}")
    print(
        "Observation time  : "
        f"{result.observation_time.astimezone(EASTERN_TIME)}"
    )
    print(
        "Fetched at        : "
        f"{result.fetched_at.astimezone(EASTERN_TIME)}"
    )
    print(f"Data age          : {result.age_description}")
    print(f"Freshness         : {result.freshness.value}")
    print(f"Quality score     : {result.quality_score}/100")
    print(f"Status            : {result.status.value}")

    if result.warnings:
        print("-" * 72)
        print("WARNINGS")

        for warning in result.warnings:
            print(f"- {warning}")

    if result.errors:
        print("-" * 72)
        print("ERRORS")

        for error in result.errors:
            print(f"- {error}")

    print("=" * 72)


def build_sample_record() -> DataQualityRecord:
    """Build a sample daily-data record for independent testing."""
    fetched_at = datetime.now(EASTERN_TIME)

    observation_time = fetched_at.replace(
        hour=16,
        minute=0,
        second=0,
        microsecond=0,
    ) - timedelta(days=1)

    return DataQualityRecord(
        symbol="SPY",
        provider="Yahoo Finance",
        timeframe="1d",
        observation_time=observation_time,
        fetched_at=fetched_at,
        market_session="PRE_MARKET",
        data_mode="Last completed daily bar",
        price=755.20,
        volume=72_500_000,
        expected_real_time=False,
        provider_reliability=90,
        notes=[
            "Sample record for PATCC validation.",
        ],
    )


def main() -> int:
    """Run the standalone sample validation."""
    engine = DataQualityEngine()
    record = build_sample_record()
    result = engine.evaluate(record)

    print_result(result)

    return 1 if result.status == QualityStatus.FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
    