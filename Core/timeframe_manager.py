"""
timeframe_manager.py

Centralized timeframe configuration for PATCC.

This module defines:

- Supported timeframe aliases
- Market-data intervals
- Historical lookback periods
- Indicator defaults
- Strategy horizon classifications

All downstream modules should obtain timeframe settings from this module
instead of maintaining separate timeframe logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TimeframeConfig:
    """
    Configuration for one analysis timeframe.
    """

    name: str
    interval: str
    period: str
    horizon: str

    fast_ema: int
    slow_ema: int
    trend_ema: int

    rsi_period: int
    atr_period: int

    minimum_bars: int


class TimeframeManager:
    """
    Provides normalized and validated timeframe configurations.
    """

    _CONFIGS: Dict[str, TimeframeConfig] = {
        "1m": TimeframeConfig(
            name="1 Minute",
            interval="1m",
            period="5d",
            horizon="scalping",
            fast_ema=9,
            slow_ema=20,
            trend_ema=50,
            rsi_period=14,
            atr_period=14,
            minimum_bars=100,
        ),
        "5m": TimeframeConfig(
            name="5 Minute",
            interval="5m",
            period="60d",
            horizon="intraday",
            fast_ema=10,
            slow_ema=20,
            trend_ema=50,
            rsi_period=14,
            atr_period=14,
            minimum_bars=150,
        ),
        "15m": TimeframeConfig(
            name="15 Minute",
            interval="15m",
            period="60d",
            horizon="intraday",
            fast_ema=10,
            slow_ema=20,
            trend_ema=50,
            rsi_period=14,
            atr_period=14,
            minimum_bars=150,
        ),
        "30m": TimeframeConfig(
            name="30 Minute",
            interval="30m",
            period="60d",
            horizon="short_swing",
            fast_ema=10,
            slow_ema=20,
            trend_ema=50,
            rsi_period=14,
            atr_period=14,
            minimum_bars=150,
        ),
        "1h": TimeframeConfig(
            name="1 Hour",
            interval="60m",
            period="2y",
            horizon="swing",
            fast_ema=10,
            slow_ema=20,
            trend_ema=50,
            rsi_period=14,
            atr_period=14,
            minimum_bars=200,
        ),
        "1d": TimeframeConfig(
            name="Daily",
            interval="1d",
            period="5y",
            horizon="position",
            fast_ema=10,
            slow_ema=20,
            trend_ema=50,
            rsi_period=14,
            atr_period=14,
            minimum_bars=250,
        ),
        "1wk": TimeframeConfig(
            name="Weekly",
            interval="1wk",
            period="10y",
            horizon="long_term",
            fast_ema=10,
            slow_ema=20,
            trend_ema=40,
            rsi_period=14,
            atr_period=14,
            minimum_bars=100,
        ),
        "1mo": TimeframeConfig(
            name="Monthly",
            interval="1mo",
            period="max",
            horizon="strategic",
            fast_ema=6,
            slow_ema=12,
            trend_ema=24,
            rsi_period=14,
            atr_period=14,
            minimum_bars=60,
        ),
    }

    _ALIASES: Dict[str, str] = {
        "1min": "1m",
        "minute": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "60m": "1h",
        "60min": "1h",
        "hour": "1h",
        "hourly": "1h",
        "day": "1d",
        "daily": "1d",
        "d": "1d",
        "week": "1wk",
        "weekly": "1wk",
        "1w": "1wk",
        "w": "1wk",
        "month": "1mo",
        "monthly": "1mo",
        "1month": "1mo",
    }

    DEFAULT_TIMEFRAME = "1d"

    @classmethod
    def normalize(cls, timeframe: str | None) -> str:
        """
        Normalize a timeframe or alias to its canonical value.

        Example:
            daily -> 1d
            60m   -> 1h
        """

        if timeframe is None:
            return cls.DEFAULT_TIMEFRAME

        normalized = timeframe.strip().lower()

        if not normalized:
            return cls.DEFAULT_TIMEFRAME

        normalized = cls._ALIASES.get(normalized, normalized)

        if normalized not in cls._CONFIGS:
            supported = ", ".join(cls.supported_timeframes())
            raise ValueError(
                f"Unsupported timeframe '{timeframe}'. "
                f"Supported timeframes: {supported}"
            )

        return normalized

    @classmethod
    def get_config(cls, timeframe: str | None = None) -> TimeframeConfig:
        """
        Return the configuration for a timeframe.
        """

        normalized = cls.normalize(timeframe)
        return cls._CONFIGS[normalized]

    @classmethod
    def supported_timeframes(cls) -> List[str]:
        """
        Return all canonical supported timeframes.
        """

        return list(cls._CONFIGS.keys())

    @classmethod
    def describe(cls, timeframe: str | None = None) -> str:
        """
        Return a readable description of a timeframe configuration.
        """

        config = cls.get_config(timeframe)

        return (
            f"Timeframe: {config.name}\n"
            f"Interval: {config.interval}\n"
            f"History period: {config.period}\n"
            f"Strategy horizon: {config.horizon}\n"
            f"EMA settings: "
            f"{config.fast_ema}/{config.slow_ema}/{config.trend_ema}\n"
            f"RSI period: {config.rsi_period}\n"
            f"ATR period: {config.atr_period}\n"
            f"Minimum bars: {config.minimum_bars}"
        )


def main() -> None:
    """
    Command-line smoke test.
    """

    import argparse

    parser = argparse.ArgumentParser(
        description="Display PATCC timeframe configuration."
    )

    parser.add_argument(
        "timeframe",
        nargs="?",
        default=TimeframeManager.DEFAULT_TIMEFRAME,
        help="Timeframe such as 5m, 1h, 1d, 1wk, or 1mo.",
    )

    args = parser.parse_args()

    try:
        print(TimeframeManager.describe(args.timeframe))
    except ValueError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
    