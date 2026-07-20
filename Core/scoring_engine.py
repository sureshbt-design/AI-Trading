"""
scoring_engine.py

PATCC profile-based scoring engine.

Operational modes
-----------------
Default:
    Compact one-screen table.

--detail:
    Full diagnostic report for drill-down.

--json:
    Machine-readable output for downstream engines.

The scoring methodology is unchanged. This revision only separates
analysis from presentation and adds multi-ticker output support.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from typing import Any, Iterable

from Core.analysis_result import AnalysisResult
from Core.asset_classifier import AssetClassifier
from Core.indicator_engine import IndicatorEngine
from Core.institutional_footprint_engine import (
    InstitutionalFootprintEngine,
)
from Core.market_data_service import (
    MarketDataRequest,
    MarketDataService,
)
from Core.market_state_analyzer import MarketStateAnalyzer
from Core.report_builder import ReportBuilder
from Core.target_engine import TargetEngine


MODE_CONFIG = {
    "swing": {
        "period": "1y",
        "interval": "1d",
    },
    "intraday": {
        "period": "5d",
        "interval": "15m",
    },
    "entry": {
        "period": "1d",
        "interval": "5m",
    },
}


PROFILE_OVERRIDES = {
    "HYG": "etf",
    "URA": "etf",
    "URNM": "etf",
    "UNG": "etf",
}


@dataclass(frozen=True)
class ScoreResult:
    overall_score: int
    grade: str
    action: str

    trend_score: int
    momentum_score: int
    volume_score: int
    volatility_score: int
    risk_score: int
    institutional_footprint_score: int


class ScoringEngine:
    """
    Convert market state, indicators, and institutional footprint
    into a 0-100 candidate score.

    Existing technical model maximum: 90 points
    Institutional-footprint contribution: 10 points
    Total maximum: 100 points
    """

    def score(
        self,
        indicators,
        state,
        profile: str = "stock",
        institutional_footprint=None,
    ) -> ScoreResult:
        profile = profile.lower().strip()

        trend_score = self._score_trend(state)
        momentum_score = self._score_momentum(indicators)
        volume_score = self._score_volume(state)
        volatility_score = self._score_volatility(
            indicators,
            profile,
        )
        risk_score = self._score_risk(state)

        footprint_score = self._score_institutional_footprint(
            institutional_footprint
        )

        overall = (
            trend_score
            + momentum_score
            + volume_score
            + volatility_score
            + risk_score
            + footprint_score
        )

        overall = max(0, min(100, overall))

        return ScoreResult(
            overall_score=overall,
            grade=self._grade(overall),
            action=self._action(overall),

            trend_score=trend_score,
            momentum_score=momentum_score,
            volume_score=volume_score,
            volatility_score=volatility_score,
            risk_score=risk_score,
            institutional_footprint_score=footprint_score,
        )

    def _score_trend(self, state) -> int:
        if state.trend == "Strong Bullish":
            return 30

        if state.trend == "Bullish":
            return 24

        if state.trend == "Neutral":
            return 12

        return 0

    def _score_momentum(self, indicators) -> int:
        if 55 <= indicators.rsi14 <= 68:
            return 20

        if 50 <= indicators.rsi14 < 55:
            return 15

        if 68 < indicators.rsi14 <= 75:
            return 10

        if 40 <= indicators.rsi14 < 50:
            return 8

        return 3

    def _score_volume(self, state) -> int:
        if state.volume == "Very High":
            return 15

        if state.volume == "Above Average":
            return 11

        return 5

    def _score_volatility(
        self,
        indicators,
        profile: str,
    ) -> int:
        atr = indicators.atr_percent

        if profile == "leveraged_etf":
            if 4 <= atr <= 9:
                return 15

            if 9 < atr <= 13:
                return 10

            if atr < 4:
                return 8

            return 4

        if 1 <= atr <= 4:
            return 15

        if 4 < atr <= 7:
            return 10

        if atr < 1:
            return 8

        return 4

    def _score_risk(self, state) -> int:
        if state.risk_level == "Conservative":
            return 10

        if state.risk_level == "Moderate":
            return 7

        return 4

    def _score_institutional_footprint(
        self,
        footprint,
    ) -> int:
        if footprint is None:
            return 0

        return max(
            0,
            min(
                10,
                int(round(footprint.score / 10.0)),
            ),
        )

    def _grade(self, score: int) -> str:
        if score >= 85:
            return "A"

        if score >= 70:
            return "B"

        if score >= 55:
            return "C"

        if score >= 40:
            return "D"

        return "F"

    def _action(self, score: int) -> str:
        if score >= 85:
            return "Strong Candidate"

        if score >= 70:
            return "Good Candidate"

        if score >= 55:
            return "Watchlist"

        if score >= 40:
            return "Weak Setup"

        return "Avoid"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PATCC scoring engine"
    )

    ticker_group = parser.add_mutually_exclusive_group()

    ticker_group.add_argument(
        "--ticker",
        default=None,
        help="Single ticker symbol to analyze.",
    )

    ticker_group.add_argument(
        "--tickers",
        default=None,
        help=(
            "Comma-separated ticker symbols, for example "
            "XLV,XLF,HYG."
        ),
    )

    parser.add_argument(
        "--mode",
        choices=[
            "swing",
            "intraday",
            "entry",
        ],
        default="swing",
        help=(
            "Analysis mode. "
            "swing=1y/1d, intraday=5d/15m, entry=1d/5m"
        ),
    )

    parser.add_argument(
        "--period",
        default=None,
        help=(
            "Optional Yahoo Finance period, "
            "for example 6mo, 1y, or 5d"
        ),
    )

    parser.add_argument(
        "--interval",
        default=None,
        help=(
            "Optional Yahoo Finance interval, "
            "for example 1d, 15m, or 5m"
        ),
    )

    parser.add_argument(
        "--tf",
        "--timeframe",
        dest="timeframe",
        default=None,
        help=(
            "Analysis timeframe "
            "(1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)"
        ),
    )

    parser.add_argument(
        "--profile",
        choices=[
            "stock",
            "etf",
            "leveraged_etf",
            "crypto",
            "index",
            "future",
            "currency",
        ],
        default=None,
        help=(
            "Optional profile override. PATCC classifies "
            "the ticker automatically by default."
        ),
    )

    parser.add_argument(
        "--detail",
        action="store_true",
        help="Print the full diagnostic report.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )

    return parser.parse_args()


def resolve_timeframe(
    mode: str,
    period: str | None,
    interval: str | None,
) -> tuple[str, str]:
    config = MODE_CONFIG[mode]

    resolved_period = period if period else config["period"]
    resolved_interval = interval if interval else config["interval"]

    return resolved_period, resolved_interval


def resolve_profile(
    ticker: str,
    explicit_profile: str | None = None,
) -> str:
    if explicit_profile:
        return explicit_profile

    normalized = ticker.upper().strip()

    if normalized in PROFILE_OVERRIDES:
        return PROFILE_OVERRIDES[normalized]

    return AssetClassifier.classify(normalized).profile


def parse_tickers(args: argparse.Namespace) -> list[str]:
    raw = args.tickers or args.ticker or "TQQQ"

    tickers: list[str] = []

    for item in raw.split(","):
        normalized = item.upper().strip()

        if normalized and normalized not in tickers:
            tickers.append(normalized)

    if not tickers:
        raise SystemExit("At least one ticker is required.")

    return tickers


def load_benchmark_data(
    service: MarketDataService,
    ticker: str,
    timeframe: str,
    period: str | None,
    interval: str | None,
):
    """Load benchmark history for relative-strength comparison."""

    response = service.get_price_history(
        MarketDataRequest(
            ticker=ticker,
            timeframe=timeframe,
            period=period,
            interval=interval,
        )
    )

    return response.data


def build_footprint_report(footprint) -> str:
    """Build the full institutional-footprint console section."""

    relative_strength = (
        f"{footprint.relative_strength_20d:+.2f}%"
        if footprint.relative_strength_20d is not None
        else "Unavailable"
    )

    lines = [
        "",
        "INSTITUTIONAL FOOTPRINT",
        "-" * 65,
        (
            f"Relative Volume      : "
            f"{footprint.rvol:.2f} "
            f"({footprint.rvol_status})"
        ),
        f"OBV Trend            : {footprint.obv_trend}",
        (
            f"CMF-20               : "
            f"{footprint.cmf20:+.3f} "
            f"({footprint.cmf_status})"
        ),
        (
            f"MFI-14               : "
            f"{footprint.mfi14:.1f} "
            f"({footprint.mfi_status})"
        ),
        (
            f"A/D Trend            : "
            f"{footprint.accumulation_distribution_trend}"
        ),
        f"Price vs DEMA-8      : {footprint.price_vs_dema8}",
        f"DEMA-8 Slope         : {footprint.dema8_slope}",
        f"Price vs VWAP-20     : {footprint.price_vs_vwap20}",
        (
            f"RS vs SPY, 20 bars   : "
            f"{relative_strength} "
            f"({footprint.relative_strength_status})"
        ),
        "",
        f"Footprint Score      : {footprint.score}/100",
        f"Classification       : {footprint.classification}",
        f"Confidence           : {footprint.confidence}",
        (
            "Interpretation       : "
            "Evidence-based footprint; not direct proof "
            "of institutional orders."
        ),
    ]

    return "\n".join(lines)


def analyze_ticker(
    *,
    ticker: str,
    mode: str = "swing",
    period: str | None = None,
    interval: str | None = None,
    timeframe: str | None = None,
    profile: str | None = None,
) -> AnalysisResult:
    """Run one complete PATCC scoring analysis and return its result."""

    normalized_ticker = ticker.upper().strip()

    if not normalized_ticker:
        raise ValueError("Ticker cannot be empty.")

    resolved_period, resolved_interval = resolve_timeframe(
        mode=mode,
        period=period,
        interval=interval,
    )

    resolved_profile = resolve_profile(
        normalized_ticker,
        profile,
    )

    service = MarketDataService()
    indicator_engine = IndicatorEngine()
    state_analyzer = MarketStateAnalyzer()
    scoring_engine = ScoringEngine()
    target_engine = TargetEngine()
    footprint_engine = InstitutionalFootprintEngine()

    resolved_timeframe = (
        timeframe
        or resolved_interval
        or "1d"
    )

    market_data = service.get_price_history(
        MarketDataRequest(
            ticker=normalized_ticker,
            timeframe=resolved_timeframe,
            period=resolved_period,
            interval=resolved_interval,
        )
    )

    df = market_data.data

    indicators = indicator_engine.calculate(df)
    state = state_analyzer.analyze(indicators)

    benchmark_df = None

    try:
        if normalized_ticker == "SPY":
            benchmark_df = df
        else:
            benchmark_df = load_benchmark_data(
                service=service,
                ticker="SPY",
                timeframe=resolved_timeframe,
                period=resolved_period,
                interval=resolved_interval,
            )
    except Exception:
        benchmark_df = None

    footprint = footprint_engine.calculate(
        indicators=indicators,
        security_df=df,
        benchmark_df=benchmark_df,
    )

    score = scoring_engine.score(
        indicators=indicators,
        state=state,
        profile=resolved_profile,
        institutional_footprint=footprint,
    )

    targets = target_engine.calculate(df)

    return AnalysisResult(
        ticker=normalized_ticker,
        profile=resolved_profile,
        market_data=market_data,
        indicators=indicators,
        market_state=state,
        score=score,
        targets=targets,
        institutional_footprint=footprint,
    )


def _safe_attr(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def compact_status(analysis: AnalysisResult) -> str:
    """Translate detailed evidence into an operational status."""

    footprint = analysis.institutional_footprint
    score = analysis.score

    classification = str(
        _safe_attr(footprint, "classification", "")
    )
    dema_position = str(
        _safe_attr(footprint, "price_vs_dema8", "")
    )
    dema_slope = str(
        _safe_attr(footprint, "dema8_slope", "")
    )
    vwap_position = str(
        _safe_attr(footprint, "price_vs_vwap20", "")
    )

    if score.overall_score < 40:
        return "AVOID"

    if "Distribution" in classification:
        return "AVOID"

    if (
        dema_position == "Above"
        and dema_slope == "Rising"
        and vwap_position == "Above"
    ):
        return "QUALIFIED"

    if score.overall_score >= 70:
        return "WAIT"

    return "WATCH"


def compact_row(analysis: AnalysisResult) -> dict[str, Any]:
    footprint = analysis.institutional_footprint
    state = analysis.market_state
    score = analysis.score

    rs = _safe_attr(
        footprint,
        "relative_strength_20d",
        None,
    )

    return {
        "ticker": analysis.ticker,
        "profile": analysis.profile,
        "score": score.overall_score,
        "grade": score.grade,
        "trend": state.trend,
        "volume": state.volume,
        "dema8": (
            f"{_safe_attr(footprint, 'price_vs_dema8', 'N/A')}/"
            f"{_safe_attr(footprint, 'dema8_slope', 'N/A')}"
        ),
        "vwap20": _safe_attr(
            footprint,
            "price_vs_vwap20",
            "N/A",
        ),
        "footprint_score": _safe_attr(
            footprint,
            "score",
            0,
        ),
        "footprint": _safe_attr(
            footprint,
            "classification",
            "Unavailable",
        ),
        "rs_spy": rs,
        "status": compact_status(analysis),
    }


def build_compact_table(
    analyses: Iterable[AnalysisResult],
) -> str:
    rows = [compact_row(item) for item in analyses]

    headers = [
        ("Ticker", 7),
        ("Score", 5),
        ("Gr", 2),
        ("Trend", 15),
        ("Volume", 13),
        ("DEMA-8", 15),
        ("VWAP", 5),
        ("FP", 3),
        ("Footprint", 20),
        ("RS", 8),
        ("Status", 9),
    ]

    line = " ".join(
        f"{label:<{width}}"
        for label, width in headers
    )

    divider = "-" * len(line)

    output = [
        "PATCC DAILY CANDIDATE TABLE",
        divider,
        line,
        divider,
    ]

    for row in rows:
        rs_text = (
            f"{row['rs_spy']:+.2f}%"
            if row["rs_spy"] is not None
            else "N/A"
        )

        output.append(
            f"{row['ticker']:<7} "
            f"{row['score']:>5} "
            f"{row['grade']:<2} "
            f"{row['trend']:<15.15} "
            f"{row['volume']:<13.13} "
            f"{row['dema8']:<15.15} "
            f"{row['vwap20']:<5.5} "
            f"{row['footprint_score']:>3} "
            f"{row['footprint']:<20.20} "
            f"{rs_text:>8} "
            f"{row['status']:<9}"
        )

    output.append(divider)
    output.append(
        "QUALIFIED = evidence aligned; WAIT = strong structure but "
        "entry confirmation incomplete."
    )

    return "\n".join(output)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if is_dataclass(value):
        return {
            key: _json_safe(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]

    if hasattr(value, "__dict__"):
        return {
            key: _json_safe(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


def analysis_to_dict(
    analysis: AnalysisResult,
) -> dict[str, Any]:
    return {
        "summary": compact_row(analysis),
        "analysis": _json_safe(analysis),
    }


def print_detail(analysis: AnalysisResult) -> None:
    builder = ReportBuilder()
    print(builder.build_console_report(analysis))
    print(
        build_footprint_report(
            analysis.institutional_footprint
        )
    )


def main() -> None:
    args = parse_args()
    tickers = parse_tickers(args)

    analyses: list[AnalysisResult] = []
    failures: list[dict[str, str]] = []

    for ticker in tickers:
        try:
            analyses.append(
                analyze_ticker(
                    ticker=ticker,
                    mode=args.mode,
                    period=args.period,
                    interval=args.interval,
                    timeframe=args.timeframe,
                    profile=args.profile,
                )
            )
        except KeyboardInterrupt:
            raise SystemExit(
                "\nAnalysis cancelled by user."
            )
        except Exception as exc:
            failures.append(
                {
                    "ticker": ticker,
                    "error": str(exc),
                }
            )

    if args.json:
        payload = {
            "results": [
                analysis_to_dict(item)
                for item in analyses
            ],
            "failures": failures,
        }
        print(
            json.dumps(
                payload,
                indent=2,
                default=str,
            )
        )
        return

    if args.detail:
        for index, analysis in enumerate(analyses):
            if index:
                print("\n" + "=" * 79 + "\n")
            print_detail(analysis)
    else:
        if analyses:
            print(build_compact_table(analyses))

    if failures:
        print("")
        print("FAILED TICKERS")
        print("-" * 65)
        for failure in failures:
            print(
                f"{failure['ticker']}: "
                f"{failure['error']}"
            )

    if not analyses:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
