"""
scoring_engine.py

Profile-based scoring engine for trading candidates.
"""

import argparse
from dataclasses import dataclass
from Core.asset_classifier import AssetClassifier
from Core.target_engine import TargetEngine
from Core.indicator_engine import IndicatorEngine
from Core.market_data_service import MarketDataRequest, MarketDataService
from Core.market_state_analyzer import MarketStateAnalyzer
from Core.analysis_result import AnalysisResult
from Core.report_builder import ReportBuilder


MODE_CONFIG = {
    "swing": {"period": "1y", "interval": "1d"},
    "intraday": {"period": "5d", "interval": "15m"},
    "entry": {"period": "1d", "interval": "5m"},
}


@dataclass
class ScoreResult:
    overall_score: int
    grade: str
    action: str
    trend_score: int
    momentum_score: int
    volume_score: int
    volatility_score: int
    risk_score: int


class ScoringEngine:
    """Convert market state and indicators into a 0-100 score."""

    def score(self, indicators, state, profile: str = "stock") -> ScoreResult:
        profile = profile.lower().strip()

        trend_score = self._score_trend(state)
        momentum_score = self._score_momentum(indicators)
        volume_score = self._score_volume(state)
        volatility_score = self._score_volatility(indicators, profile)
        risk_score = self._score_risk(state)

        overall = (
            trend_score
            + momentum_score
            + volume_score
            + volatility_score
            + risk_score
        )

        return ScoreResult(
            overall_score=overall,
            grade=self._grade(overall),
            action=self._action(overall),
            trend_score=trend_score,
            momentum_score=momentum_score,
            volume_score=volume_score,
            volatility_score=volatility_score,
            risk_score=risk_score,
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

    def _score_volatility(self, indicators, profile: str) -> int:
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="PATCC scoring engine"
    )

    parser.add_argument(
        "--ticker",
        default="TQQQ",
        help="Ticker symbol to analyze. Default: TQQQ",
    )

    parser.add_argument(
        "--mode",
        choices=["swing", "intraday", "entry"],
        default="swing",
        help="Analysis mode. swing=1y/1d, intraday=5d/15m, entry=1d/5m",
    )

    parser.add_argument(
        "--period",
        default=None,
        help="Optional custom Yahoo Finance period, for example 6mo, 1y, 5d",
    )

    parser.add_argument(
        "--interval",
        default=None,
        help="Optional custom Yahoo Finance interval, for example 1d, 15m, 5m",
    )

    parser.add_argument(
    "--tf",
    "--timeframe",
    dest="timeframe",
    default=None,
    help="Analysis timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo).",
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
        help="Optional profile override. By default PATCC classifies the ticker automatically.", 
    )

    return parser.parse_args()


def resolve_timeframe(mode: str, period: str | None, interval: str | None):
    config = MODE_CONFIG[mode]

    resolved_period = period if period else config["period"]
    resolved_interval = interval if interval else config["interval"]

    return resolved_period, resolved_interval


def run_analysis(
    ticker: str,
    mode: str,
    period: str | None,
    interval: str | None,
    timeframe: str | None,
    profile: str,
):

    service = MarketDataService()
    indicator_engine = IndicatorEngine()
    state_analyzer = MarketStateAnalyzer()
    scoring_engine = ScoringEngine()
    target_engine = TargetEngine()

    market_data = service.get_price_history(
        MarketDataRequest(
            ticker=ticker,
            timeframe=timeframe or "1d",
            period=period,
            interval=interval,
        )
    )
    df = market_data.data

    indicators = indicator_engine.calculate(df)
    state = state_analyzer.analyze(indicators)

    score = scoring_engine.score(
        indicators=indicators,
        state=state,
        profile=profile,
    )

    targets = target_engine.calculate(df)

    analysis = AnalysisResult(
        ticker=ticker,
        profile=profile,
        market_data=market_data,
        indicators=indicators,
        market_state=state,
        score=score,
        targets=targets,
    )

    builder = ReportBuilder()
    print(builder.build_console_report(analysis))


if __name__ == "__main__":
    args = parse_args()

    ticker = args.ticker.upper().strip()
    period, interval = resolve_timeframe(
        mode=args.mode,
        period=args.period,
        interval=args.interval,
    )

    asset_info = AssetClassifier.classify(args.ticker)

    profile = args.profile or asset_info.profile

    run_analysis(
        ticker=args.ticker,
        mode=args.mode,
        period=args.period,
        interval=args.interval,
        timeframe=args.timeframe,
        profile=profile,
)
    