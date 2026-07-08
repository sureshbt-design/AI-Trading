"""
scoring_engine.py

Profile-based scoring engine for trading candidates.
"""

from target_engine import TargetEngine
from dataclasses import dataclass

from indicator_engine import IndicatorEngine
from market_data_service import MarketDataRequest, MarketDataService
from market_state_analyzer import MarketStateAnalyzer


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


if __name__ == "__main__":
    ticker = "TQQQ"

    service = MarketDataService()
    indicator_engine = IndicatorEngine()
    state_analyzer = MarketStateAnalyzer()
    scoring_engine = ScoringEngine()
    target_engine = TargetEngine()

    market_data = service.get_price_history(
        MarketDataRequest(
            ticker=ticker,
            period="1y",
            interval="1d",
        )
    )

    df = market_data.data

    indicators = indicator_engine.calculate(df)
    state = state_analyzer.analyze(indicators)
    score = scoring_engine.score(
        indicators=indicators,
        state=state,
        profile="leveraged_etf",
    )
    targets = target_engine.calculate(df)
    print(state)
    print(score)
    print(targets)