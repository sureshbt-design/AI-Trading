"""
economic_calendar.py

PATCC Economic Calendar Engine

Responsibilities
----------------
- Load economic and market-event definitions from JSON
- Validate schema and event records
- Calculate event status relative to an evaluation time
- Identify affected assets and transmission channels
- Produce structured, explainable event intelligence
- Support deterministic tests

This module does not:
- Download live calendar data
- Calculate asset-specific event risk scores
- Generate buy or sell recommendations

Version: 0.1.0
"""

from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CALENDAR_FILE = (
    PROJECT_ROOT / "Config" / "economic_events.json"
)

EASTERN_TIME = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


class EconomicCalendarError(Exception):
    """Raised when calendar configuration or event data is invalid."""


class ImpactLevel(str, Enum):
    """Configured event importance."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EXTREME = "EXTREME"


class EventStatus(str, Enum):
    """Current event lifecycle state."""

    UPCOMING = "UPCOMING"
    IMMINENT = "IMMINENT"
    REACTION = "REACTION"
    STABILIZATION = "STABILIZATION"
    COMPLETED = "COMPLETED"


class SensitivityLevel(str, Enum):
    """Asset sensitivity to an event."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True)
class EventSource:
    """Provenance metadata for one event."""

    provider: str
    source_type: str
    reliability: int


@dataclass(frozen=True)
class EventStatusPolicy:
    """Timing windows used to classify an event."""

    imminent_minutes: int
    reaction_minutes: int
    stabilization_minutes: int


@dataclass(frozen=True)
class AffectedAsset:
    """One asset affected by an event."""

    ticker: str
    sensitivity: SensitivityLevel
    directional_bias: str
    transmission_channel: str


@dataclass(frozen=True)
class EconomicEvent:
    """Validated economic or market event."""

    event_id: str
    name: str
    short_name: str
    category: str
    impact: ImpactLevel
    scheduled_at: datetime
    source: EventSource
    status_policy: EventStatusPolicy
    historical_importance: int
    current_importance: int
    affected_asset_classes: tuple[str, ...]
    affected_assets: tuple[AffectedAsset, ...]
    explanation: str
    patcc_guidance: str


@dataclass(frozen=True)
class EvaluatedEvent:
    """One event evaluated at a specific time."""

    event: EconomicEvent
    evaluated_at_et: datetime
    status: EventStatus
    minutes_until_event: Optional[int]
    minutes_since_event: Optional[int]
    status_explanation: str


@dataclass(frozen=True)
class CalendarEvaluation:
    """Complete evaluated economic-calendar result."""

    evaluated_at_et: datetime
    total_events: int
    upcoming_events: int
    imminent_events: int
    reaction_events: int
    stabilization_events: int
    completed_events: int
    next_event: Optional[EvaluatedEvent]
    events: tuple[EvaluatedEvent, ...]
    warnings: tuple[str, ...]


class EconomicCalendarEngine:
    """
    Load, evaluate, explain and report PATCC market events.
    """

    def __init__(
        self,
        calendar_file: Path = DEFAULT_CALENDAR_FILE,
    ) -> None:
        self.calendar_file = calendar_file
        self._events: list[EconomicEvent] = []
        self._warnings: list[str] = []

    def load(
        self,
        calendar_file: Optional[Path] = None,
    ) -> list[EconomicEvent]:
        """Load and validate economic events from JSON."""
        path = calendar_file or self.calendar_file
        payload = self._load_json(path)

        if payload.get("schema_version") != "1.0.0":
            raise EconomicCalendarError(
                "Unsupported economic-calendar schema version: "
                f"{payload.get('schema_version')!r}"
            )

        raw_events = payload.get("events")

        if not isinstance(raw_events, list):
            raise EconomicCalendarError(
                "Calendar configuration must contain an 'events' list."
            )

        events = [
            self._parse_event(raw_event, position)
            for position, raw_event in enumerate(raw_events, start=1)
        ]

        self._validate_unique_event_ids(events)
        self._events = sorted(
            events,
            key=lambda event: event.scheduled_at,
        )

        return list(self._events)

    def evaluate(
        self,
        evaluated_at: Optional[datetime] = None,
        *,
        include_completed: bool = True,
    ) -> CalendarEvaluation:
        """Evaluate all loaded events at a supplied or current time."""
        if not self._events:
            self.load()

        now_et = self._normalize_timestamp(evaluated_at)

        evaluated_events = [
            self._evaluate_event(event, now_et)
            for event in self._events
        ]

        if not include_completed:
            evaluated_events = [
                item
                for item in evaluated_events
                if item.status != EventStatus.COMPLETED
            ]

        next_event = next(
            (
                item
                for item in evaluated_events
                if item.status in {
                    EventStatus.UPCOMING,
                    EventStatus.IMMINENT,
                }
            ),
            None,
        )

        counts = {
            status: sum(
                1
                for item in evaluated_events
                if item.status == status
            )
            for status in EventStatus
        }

        return CalendarEvaluation(
            evaluated_at_et=now_et,
            total_events=len(evaluated_events),
            upcoming_events=counts[EventStatus.UPCOMING],
            imminent_events=counts[EventStatus.IMMINENT],
            reaction_events=counts[EventStatus.REACTION],
            stabilization_events=counts[
                EventStatus.STABILIZATION
            ],
            completed_events=counts[EventStatus.COMPLETED],
            next_event=next_event,
            events=tuple(evaluated_events),
            warnings=tuple(self._warnings),
        )

    def explain(
        self,
        item: EvaluatedEvent,
    ) -> str:
        """Return a full explanation for one evaluated event."""
        affected = ", ".join(
            asset.ticker
            for asset in item.event.affected_assets
        )

        return (
            f"{item.event.short_name} is classified as "
            f"{item.event.impact.value} impact and is currently in the "
            f"{item.status.value} state. "
            f"{item.status_explanation} "
            f"Affected PATCC assets include: {affected}. "
            f"Why it matters: {item.event.explanation} "
            f"PATCC guidance: {item.event.patcc_guidance}"
        )

    def report(
        self,
        evaluation: CalendarEvaluation,
    ) -> str:
        """Return a readable calendar report as text."""
        lines: list[str] = []

        lines.append("=" * 88)
        lines.append("PATCC ECONOMIC CALENDAR ENGINE v0.1")
        lines.append("=" * 88)
        lines.append(
            "Evaluated at      : "
            f"{self._format_timestamp(evaluation.evaluated_at_et)}"
        )
        lines.append(
            f"Total events     : {evaluation.total_events}"
        )
        lines.append(
            f"Upcoming         : {evaluation.upcoming_events}"
        )
        lines.append(
            f"Imminent         : {evaluation.imminent_events}"
        )
        lines.append(
            f"Reaction         : {evaluation.reaction_events}"
        )
        lines.append(
            "Stabilization    : "
            f"{evaluation.stabilization_events}"
        )
        lines.append(
            f"Completed        : {evaluation.completed_events}"
        )

        if evaluation.next_event is not None:
            lines.append("-" * 88)
            lines.append(
                "Next event       : "
                f"{evaluation.next_event.event.short_name}"
            )
            lines.append(
                "Scheduled at     : "
                f"{self._format_timestamp(
                    evaluation.next_event.event.scheduled_at
                )}"
            )
            lines.append(
                "Minutes remaining: "
                f"{evaluation.next_event.minutes_until_event}"
            )

        lines.append("=" * 88)

        for item in evaluation.events:
            event = item.event

            lines.append("")
            lines.append(
                f"{event.short_name} — {event.name}"
            )
            lines.append("-" * 88)
            lines.append(
                f"Event ID         : {event.event_id}"
            )
            lines.append(
                f"Category         : {event.category}"
            )
            lines.append(
                f"Impact           : {event.impact.value}"
            )
            lines.append(
                f"Status           : {item.status.value}"
            )
            lines.append(
                "Scheduled at      : "
                f"{self._format_timestamp(event.scheduled_at)}"
            )

            if item.minutes_until_event is not None:
                lines.append(
                    "Minutes until    : "
                    f"{item.minutes_until_event}"
                )

            if item.minutes_since_event is not None:
                lines.append(
                    "Minutes since    : "
                    f"{item.minutes_since_event}"
                )

            lines.append(
                "Source            : "
                f"{event.source.provider} "
                f"({event.source.source_type}, "
                f"{event.source.reliability}/100)"
            )
            lines.append(
                "Historical rating : "
                f"{event.historical_importance}/5"
            )
            lines.append(
                "Current rating    : "
                f"{event.current_importance}/5"
            )
            lines.append(
                "Status explanation: "
                f"{item.status_explanation}"
            )
            lines.append(
                f"Why it matters    : {event.explanation}"
            )
            lines.append(
                f"PATCC guidance    : {event.patcc_guidance}"
            )
            lines.append("Affected assets:")

            for asset in event.affected_assets:
                lines.append(
                    f"  {asset.ticker:<10}"
                    f"{asset.sensitivity.value:<12}"
                    f"{asset.directional_bias:<18}"
                    f"{asset.transmission_channel}"
                )

        if evaluation.warnings:
            lines.append("")
            lines.append("=" * 88)
            lines.append("WARNINGS")
            lines.append("-" * 88)

            for warning in evaluation.warnings:
                lines.append(f"- {warning}")

        lines.append("=" * 88)

        return "\n".join(lines)

    def find_events_for_ticker(
        self,
        ticker: str,
    ) -> list[EconomicEvent]:
        """Return all configured events affecting one ticker."""
        if not self._events:
            self.load()

        normalized = ticker.strip().upper()

        return [
            event
            for event in self._events
            if any(
                asset.ticker == normalized
                for asset in event.affected_assets
            )
        ]

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        """Load one JSON configuration file."""
        if not path.exists():
            raise EconomicCalendarError(
                f"Economic calendar file not found: {path}"
            )

        if not path.is_file():
            raise EconomicCalendarError(
                f"Economic calendar path is not a file: {path}"
            )

        try:
            payload = json.loads(
                path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise EconomicCalendarError(
                f"Invalid JSON in {path}: line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}"
            ) from exc
        except OSError as exc:
            raise EconomicCalendarError(
                f"Unable to read {path}: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise EconomicCalendarError(
                "Top-level economic-calendar JSON must be an object."
            )

        return payload

    def _parse_event(
        self,
        raw: Any,
        position: int,
    ) -> EconomicEvent:
        """Validate and normalize one configured event."""
        if not isinstance(raw, dict):
            raise EconomicCalendarError(
                f"Event #{position} must be a JSON object."
            )

        required = {
            "event_id",
            "name",
            "short_name",
            "category",
            "impact",
            "scheduled_at",
            "source",
            "status_policy",
            "historical_importance",
            "current_importance",
            "affected_asset_classes",
            "affected_assets",
            "explanation",
            "patcc_guidance",
        }

        missing = required - raw.keys()

        if missing:
            raise EconomicCalendarError(
                f"Event #{position} is missing fields: "
                f"{', '.join(sorted(missing))}"
            )

        event_id = str(raw["event_id"]).strip().upper()

        if not event_id:
            raise EconomicCalendarError(
                f"Event #{position} has an empty event_id."
            )

        try:
            impact = ImpactLevel(
                str(raw["impact"]).strip().upper()
            )
        except ValueError as exc:
            raise EconomicCalendarError(
                f"{event_id}: invalid impact level."
            ) from exc

        scheduled_at = self._parse_datetime(
            raw["scheduled_at"],
            event_id,
        )

        source = self._parse_source(
            raw["source"],
            event_id,
        )

        policy = self._parse_status_policy(
            raw["status_policy"],
            event_id,
        )

        affected_assets = self._parse_affected_assets(
            raw["affected_assets"],
            event_id,
        )

        historical_importance = self._parse_rating(
            raw["historical_importance"],
            event_id,
            "historical_importance",
        )

        current_importance = self._parse_rating(
            raw["current_importance"],
            event_id,
            "current_importance",
        )

        classes = raw["affected_asset_classes"]

        if not isinstance(classes, list):
            raise EconomicCalendarError(
                f"{event_id}: affected_asset_classes must be a list."
            )

        return EconomicEvent(
            event_id=event_id,
            name=str(raw["name"]).strip(),
            short_name=str(raw["short_name"]).strip(),
            category=str(raw["category"]).strip(),
            impact=impact,
            scheduled_at=scheduled_at,
            source=source,
            status_policy=policy,
            historical_importance=historical_importance,
            current_importance=current_importance,
            affected_asset_classes=tuple(
                str(value).strip()
                for value in classes
                if str(value).strip()
            ),
            affected_assets=tuple(affected_assets),
            explanation=str(raw["explanation"]).strip(),
            patcc_guidance=str(
                raw["patcc_guidance"]
            ).strip(),
        )

    @staticmethod
    def _parse_datetime(
        raw_value: Any,
        event_id: str,
    ) -> datetime:
        """Parse one timezone-aware ISO timestamp."""
        try:
            value = datetime.fromisoformat(str(raw_value))
        except ValueError as exc:
            raise EconomicCalendarError(
                f"{event_id}: scheduled_at is not valid ISO-8601."
            ) from exc

        if value.tzinfo is None:
            raise EconomicCalendarError(
                f"{event_id}: scheduled_at must be timezone-aware."
            )

        return value.astimezone(EASTERN_TIME)

    @staticmethod
    def _parse_source(
        raw_source: Any,
        event_id: str,
    ) -> EventSource:
        """Validate event source metadata."""
        if not isinstance(raw_source, dict):
            raise EconomicCalendarError(
                f"{event_id}: source must be an object."
            )

        reliability = int(raw_source.get("reliability", -1))

        if not 0 <= reliability <= 100:
            raise EconomicCalendarError(
                f"{event_id}: source reliability must be 0–100."
            )

        return EventSource(
            provider=str(
                raw_source.get("provider", "")
            ).strip(),
            source_type=str(
                raw_source.get("source_type", "")
            ).strip(),
            reliability=reliability,
        )

    @staticmethod
    def _parse_status_policy(
        raw_policy: Any,
        event_id: str,
    ) -> EventStatusPolicy:
        """Validate event timing policy."""
        if not isinstance(raw_policy, dict):
            raise EconomicCalendarError(
                f"{event_id}: status_policy must be an object."
            )

        imminent = int(
            raw_policy.get("imminent_minutes", -1)
        )
        reaction = int(
            raw_policy.get("reaction_minutes", -1)
        )
        stabilization = int(
            raw_policy.get("stabilization_minutes", -1)
        )

        if min(imminent, reaction, stabilization) < 0:
            raise EconomicCalendarError(
                f"{event_id}: status-policy values cannot be negative."
            )

        if stabilization < reaction:
            raise EconomicCalendarError(
                f"{event_id}: stabilization_minutes must be "
                "greater than or equal to reaction_minutes."
            )

        return EventStatusPolicy(
            imminent_minutes=imminent,
            reaction_minutes=reaction,
            stabilization_minutes=stabilization,
        )

    def _parse_affected_assets(
        self,
        raw_assets: Any,
        event_id: str,
    ) -> list[AffectedAsset]:
        """Validate affected assets and reject duplicates."""
        if not isinstance(raw_assets, list):
            raise EconomicCalendarError(
                f"{event_id}: affected_assets must be a list."
            )

        assets: list[AffectedAsset] = []
        seen: set[str] = set()

        for position, raw_asset in enumerate(
            raw_assets,
            start=1,
        ):
            if not isinstance(raw_asset, dict):
                raise EconomicCalendarError(
                    f"{event_id}: affected asset #{position} "
                    "must be an object."
                )

            ticker = str(
                raw_asset.get("ticker", "")
            ).strip().upper()

            if not ticker:
                raise EconomicCalendarError(
                    f"{event_id}: affected asset #{position} "
                    "has an empty ticker."
                )

            if ticker in seen:
                raise EconomicCalendarError(
                    f"{event_id}: duplicate affected ticker {ticker}."
                )

            seen.add(ticker)

            try:
                sensitivity = SensitivityLevel(
                    str(
                        raw_asset.get("sensitivity", "")
                    ).strip().upper()
                )
            except ValueError as exc:
                raise EconomicCalendarError(
                    f"{event_id}/{ticker}: invalid sensitivity."
                ) from exc

            assets.append(
                AffectedAsset(
                    ticker=ticker,
                    sensitivity=sensitivity,
                    directional_bias=str(
                        raw_asset.get(
                            "directional_bias",
                            "CONDITIONAL",
                        )
                    ).strip().upper(),
                    transmission_channel=str(
                        raw_asset.get(
                            "transmission_channel",
                            "",
                        )
                    ).strip(),
                )
            )

        return assets

    @staticmethod
    def _parse_rating(
        value: Any,
        event_id: str,
        field_name: str,
    ) -> int:
        """Validate a one-to-five importance rating."""
        rating = int(value)

        if not 1 <= rating <= 5:
            raise EconomicCalendarError(
                f"{event_id}: {field_name} must be between 1 and 5."
            )

        return rating

    @staticmethod
    def _validate_unique_event_ids(
        events: Iterable[EconomicEvent],
    ) -> None:
        """Reject duplicate event IDs."""
        seen: set[str] = set()

        for event in events:
            if event.event_id in seen:
                raise EconomicCalendarError(
                    f"Duplicate event_id detected: {event.event_id}"
                )

            seen.add(event.event_id)

    def _evaluate_event(
        self,
        event: EconomicEvent,
        now_et: datetime,
    ) -> EvaluatedEvent:
        """Evaluate one event lifecycle state."""
        scheduled = event.scheduled_at
        delta = scheduled - now_et
        minutes_difference = int(
            abs(delta.total_seconds()) // 60
        )

        if now_et < scheduled:
            minutes_until = max(
                0,
                int(
                    (delta.total_seconds() + 59) // 60
                ),
            )

            if (
                minutes_until
                <= event.status_policy.imminent_minutes
            ):
                status = EventStatus.IMMINENT
                explanation = (
                    f"The event is scheduled in approximately "
                    f"{minutes_until} minutes and is inside its "
                    "configured imminent-event window."
                )
            else:
                status = EventStatus.UPCOMING
                explanation = (
                    f"The event is scheduled in approximately "
                    f"{minutes_until} minutes and is not yet inside "
                    "its configured imminent-event window."
                )

            return EvaluatedEvent(
                event=event,
                evaluated_at_et=now_et,
                status=status,
                minutes_until_event=minutes_until,
                minutes_since_event=None,
                status_explanation=explanation,
            )

        minutes_since = minutes_difference

        if minutes_since <= event.status_policy.reaction_minutes:
            status = EventStatus.REACTION
            explanation = (
                f"The event occurred approximately {minutes_since} "
                "minutes ago and remains inside its configured "
                "primary reaction window."
            )

        elif (
            minutes_since
            <= event.status_policy.stabilization_minutes
        ):
            status = EventStatus.STABILIZATION
            explanation = (
                f"The event occurred approximately {minutes_since} "
                "minutes ago. The primary reaction window has passed, "
                "but post-event stabilization may still be underway."
            )

        else:
            status = EventStatus.COMPLETED
            explanation = (
                f"The event occurred approximately {minutes_since} "
                "minutes ago and is beyond its configured reaction "
                "and stabilization windows."
            )

        return EvaluatedEvent(
            event=event,
            evaluated_at_et=now_et,
            status=status,
            minutes_until_event=None,
            minutes_since_event=minutes_since,
            status_explanation=explanation,
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
                "Economic-calendar evaluation time must be "
                "timezone-aware."
            )

        return supplied.astimezone(EASTERN_TIME)

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        """Format one Eastern timestamp."""
        return value.astimezone(EASTERN_TIME).strftime(
            "%Y-%m-%d %I:%M:%S %p ET"
        )


def build_test_timestamp(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    """Build a deterministic Eastern test timestamp."""
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        tzinfo=EASTERN_TIME,
    )


def main() -> int:
    """Run the standalone economic-calendar report."""
    engine = EconomicCalendarEngine()

    try:
        engine.load()
        evaluation = engine.evaluate()
    except EconomicCalendarError as exc:
        print("=" * 88)
        print("PATCC ECONOMIC CALENDAR ENGINE — FAILED")
        print("=" * 88)
        print(exc)
        return 1

    print(engine.report(evaluation))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    