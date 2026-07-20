"""
single_timeframe_analyzer.py

Reusable PATCC analysis pipeline for one timeframe.

This module downloads market data, validates the latest bar,
calculates indicators, market state, institutional footprint,
score, and optional target levels.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from Core.indicator_engine import IndicatorEngine
from Core.institutional_footprint_engine import (
    InstitutionalFootprintEngine,
)
from Core.market_data_service import (
    MarketDataRequest,
    MarketDataResponse,
    MarketDataService,
)
from Core.market_state_analyzer import MarketStateAnalyzer
from Core.scoring_engine import ScoringEngine
from Core.target_engine import TargetEngine


EASTERN_TIME = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class BarValidationResult:
    """
    Information about the bar selected for analysis.
    """

    status: str
    latest_downloaded_bar: datetime
    analysis_bar: datetime
    provisional: bool
    rows_downloaded: int
    rows_used: int
    note: str


@dataclass(frozen=True)
class TimeframeAnalysis:
    """
    Complete PATCC result for one timeframe.
    """

    key: str
    label: str
    role: str

    timeframe: str
    period: str
    interval: str

    market_data: MarketDataResponse
    analysis_data: pd.DataFrame
    bar_validation: BarValidationResult

    indicators: Any
    market_state: Any
    institutional_footprint: Any
    score: Any
    targets: Any | None

    error: str | None = None


class SingleTimeframeAnalyzer:
    """
    Run the PATCC analysis pipeline for one timeframe.
    """

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
    ) -> None:
        self.market_data_service = (
            market_data_service or MarketDataService()
        )

        self.indicator_engine = IndicatorEngine()
        self.market_state_analyzer = MarketStateAnalyzer()
        self.scoring_engine = ScoringEngine()
        self.target_engine = TargetEngine()
        self.footprint_engine = InstitutionalFootprintEngine()

    def analyze(
        self,
        *,
        ticker: str,
        profile: str,
        key: str,
        label: str,
        role: str,
        timeframe: str,
        period: str,
        interval: str,
        benchmark_ticker: str = "SPY",
        use_completed_bar: bool = True,
        allow_live_bar: bool = False,
        calculate_targets: bool = False,
    ) -> TimeframeAnalysis:
        """
        Analyze one security on one timeframe.
        """

        market_data = self.market_data_service.get_price_history(
            MarketDataRequest(
                ticker=ticker,
                timeframe=timeframe,
                period=period,
                interval=interval,
            )
        )

        analysis_df, validation = self._prepare_analysis_data(
            df=market_data.data,
            timeframe=timeframe,
            interval=interval,
            use_completed_bar=use_completed_bar,
            allow_live_bar=allow_live_bar,
        )

        indicators = self.indicator_engine.calculate(
            analysis_df
        )

        market_state = self.market_state_analyzer.analyze(
            indicators
        )

        benchmark_df = self._load_benchmark(
            ticker=ticker,
            benchmark_ticker=benchmark_ticker,
            timeframe=timeframe,
            period=period,
            interval=interval,
            use_completed_bar=use_completed_bar,
            allow_live_bar=allow_live_bar,
            security_df=analysis_df,
        )

        institutional_footprint = (
            self.footprint_engine.calculate(
                indicators=indicators,
                security_df=analysis_df,
                benchmark_df=benchmark_df,
            )
        )

        score = self.scoring_engine.score(
            indicators=indicators,
            state=market_state,
            profile=profile,
            institutional_footprint=(
                institutional_footprint
            ),
        )

        targets = None

        if calculate_targets:
            targets = self.target_engine.calculate(
                analysis_df
            )

        return TimeframeAnalysis(
            key=key,
            label=label,
            role=role,
            timeframe=timeframe,
            period=period,
            interval=interval,
            market_data=market_data,
            analysis_data=analysis_df,
            bar_validation=validation,
            indicators=indicators,
            market_state=market_state,
            institutional_footprint=(
                institutional_footprint
            ),
            score=score,
            targets=targets,
        )

    def _load_benchmark(
        self,
        *,
        ticker: str,
        benchmark_ticker: str,
        timeframe: str,
        period: str,
        interval: str,
        use_completed_bar: bool,
        allow_live_bar: bool,
        security_df: pd.DataFrame,
    ) -> pd.DataFrame | None:
        """
        Load SPY or another benchmark for relative strength.
        """

        if (
            ticker.upper().strip()
            == benchmark_ticker.upper().strip()
        ):
            return security_df.copy()

        try:
            response = (
                self.market_data_service.get_price_history(
                    MarketDataRequest(
                        ticker=benchmark_ticker,
                        timeframe=timeframe,
                        period=period,
                        interval=interval,
                    )
                )
            )

            benchmark_df, _ = self._prepare_analysis_data(
                df=response.data,
                timeframe=timeframe,
                interval=interval,
                use_completed_bar=use_completed_bar,
                allow_live_bar=allow_live_bar,
            )

            return benchmark_df

        except Exception as exc:
            print(
                f"WARNING: Benchmark {benchmark_ticker} "
                f"could not be loaded for {timeframe}: {exc}"
            )

            return None

    def _prepare_analysis_data(
        self,
        *,
        df: pd.DataFrame,
        timeframe: str,
        interval: str,
        use_completed_bar: bool,
        allow_live_bar: bool,
    ) -> tuple[pd.DataFrame, BarValidationResult]:
        """
        Select completed bars unless a provisional live bar is allowed.
        """

        if df is None or df.empty:
            raise ValueError(
                "Downloaded price history is empty."
            )

        working = df.copy()

        latest_downloaded = self._index_to_datetime(
            working.index[-1]
        )

        incomplete = self._is_incomplete_bar(
            bar_timestamp=latest_downloaded,
            timeframe=timeframe,
            interval=interval,
        )

        provisional = False

        note = (
            "Latest downloaded bar is considered complete."
        )

        remove_latest = (
            incomplete
            and use_completed_bar
            and not allow_live_bar
        )

        if remove_latest:
            if len(working) <= 30:
                raise ValueError(
                    "Not enough rows remain after excluding "
                    "the incomplete current bar."
                )

            working = working.iloc[:-1].copy()

            note = (
                "Incomplete current bar excluded; analysis "
                "uses the most recent completed bar."
            )

        elif incomplete and allow_live_bar:
            provisional = True

            note = (
                "Current live bar included. Execution result "
                "is provisional until the bar closes."
            )

        elif incomplete:
            provisional = True

            note = (
                "Potentially incomplete bar included because "
                "completed-bar filtering was disabled."
            )

        if working.empty:
            raise ValueError(
                "No usable price rows remain for analysis."
            )

        analysis_bar = self._index_to_datetime(
            working.index[-1]
        )

        validation = BarValidationResult(
            status=(
                "LIVE / PROVISIONAL"
                if provisional
                else "COMPLETED"
            ),
            latest_downloaded_bar=latest_downloaded,
            analysis_bar=analysis_bar,
            provisional=provisional,
            rows_downloaded=len(df),
            rows_used=len(working),
            note=note,
        )

        return working, validation

    def _is_incomplete_bar(
        self,
        *,
        bar_timestamp: datetime,
        timeframe: str,
        interval: str,
    ) -> bool:
        """
        Determine whether the newest bar may still be forming.
        """

        now_et = datetime.now(EASTERN_TIME)
        bar_et = self._to_eastern(bar_timestamp)

        normalized_timeframe = (
            timeframe.lower().strip()
        )

        normalized_interval = (
            interval.lower().strip()
        )

        if normalized_timeframe in {
            "1d",
            "d",
            "daily",
        }:
            return self._daily_bar_is_incomplete(
                bar_et=bar_et,
                now_et=now_et,
            )

        if normalized_timeframe in {
            "1wk",
            "1w",
            "weekly",
        }:
            return self._weekly_bar_is_incomplete(
                bar_et=bar_et,
                now_et=now_et,
            )

        duration = self._interval_duration(
            normalized_interval
        )

        if duration is None:
            return False

        expected_close = bar_et + duration

        return now_et < expected_close

    def _daily_bar_is_incomplete(
        self,
        *,
        bar_et: datetime,
        now_et: datetime,
    ) -> bool:
        """
        A US daily bar is incomplete before 4:00 PM Eastern.
        """

        if bar_et.date() != now_et.date():
            return False

        regular_close = datetime.combine(
            now_et.date(),
            time(hour=16, minute=0),
            tzinfo=EASTERN_TIME,
        )

        return now_et < regular_close

    def _weekly_bar_is_incomplete(
        self,
        *,
        bar_et: datetime,
        now_et: datetime,
    ) -> bool:
        """
        The current weekly bar is incomplete until Friday close.
        """

        bar_year, bar_week, _ = (
            bar_et.isocalendar()
        )

        now_year, now_week, _ = (
            now_et.isocalendar()
        )

        if (
            bar_year,
            bar_week,
        ) != (
            now_year,
            now_week,
        ):
            return False

        days_until_friday = 4 - now_et.weekday()

        friday_date = (
            now_et.date()
            + timedelta(days=days_until_friday)
        )

        friday_close = datetime.combine(
            friday_date,
            time(hour=16, minute=0),
            tzinfo=EASTERN_TIME,
        )

        return now_et < friday_close

    def _interval_duration(
        self,
        interval: str,
    ) -> timedelta | None:
        """
        Return the expected duration of an intraday bar.
        """

        mapping = {
            "1m": timedelta(minutes=1),
            "2m": timedelta(minutes=2),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "30m": timedelta(minutes=30),
            "60m": timedelta(minutes=60),
            "90m": timedelta(minutes=90),
            "1h": timedelta(hours=1),
        }

        return mapping.get(interval)

    def _index_to_datetime(
        self,
        value: object,
    ) -> datetime:
        """
        Convert a pandas index value into a datetime.
        """

        timestamp = pd.Timestamp(value)

        return timestamp.to_pydatetime()

    def _to_eastern(
        self,
        value: datetime,
    ) -> datetime:
        """
        Normalize a datetime to America/New_York.
        """

        if value.tzinfo is None:
            return value.replace(
                tzinfo=EASTERN_TIME
            )

        return value.astimezone(EASTERN_TIME)
        