"""
market_state_analyzer.py

Analyzes the current market state using calculated indicators.
"""

from dataclasses import dataclass

from Core.indicator_engine import IndicatorEngine
from Core.market_data_service import MarketDataRequest, MarketDataService


@dataclass
class MarketState:
    trend: str
    momentum: str
    volatility: str
    volume: str
    market_bias: str
    risk_level: str
    score: int


class MarketStateAnalyzer:
    """Determine overall market condition."""

    def analyze(self, indicators) -> MarketState:

        score = 0

        # -------------------------
        # Trend
        # -------------------------

        if indicators.close > indicators.ema20:
            score += 1

        if indicators.ema20 > indicators.ema50:
            score += 2

        if indicators.ema200 is not None:
            if indicators.ema50 > indicators.ema200:
                score += 3

        # -------------------------
        # RSI
        # -------------------------

        if 50 <= indicators.rsi14 <= 70:
            score += 2
            momentum = "Bullish"

        elif indicators.rsi14 > 70:
            score += 1
            momentum = "Overbought"

        elif indicators.rsi14 < 30:
            momentum = "Oversold"

        else:
            momentum = "Neutral"

        # -------------------------
        # Volatility
        # -------------------------

        if indicators.atr_percent > 6:
            volatility = "High"

        elif indicators.atr_percent > 3:
            volatility = "Medium"

        else:
            volatility = "Low"

        # -------------------------
        # Volume
        # -------------------------

        if indicators.rvol > 1.5:
            volume = "Very High"

        elif indicators.rvol > 1.0:
            volume = "Above Average"

        else:
            volume = "Below Average"

        # -------------------------
        # Trend
        # -------------------------

        if score >= 7:
            trend = "Strong Bullish"

        elif score >= 5:
            trend = "Bullish"

        elif score >= 3:
            trend = "Neutral"

        else:
            trend = "Bearish"

        # -------------------------
        # Risk
        # -------------------------

        if volatility == "High":
            risk = "Aggressive"

        elif volatility == "Medium":
            risk = "Moderate"

        else:
            risk = "Conservative"

        # -------------------------
        # Market Bias
        # -------------------------

        if trend.startswith("Strong"):
            bias = "Buy"

        elif trend == "Bullish":
            bias = "Watch for Pullback"

        elif trend == "Neutral":
            bias = "Wait"

        else:
            bias = "Avoid"

        return MarketState(
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            volume=volume,
            market_bias=bias,
            risk_level=risk,
            score=score,
        )


if __name__ == "__main__":

    service = MarketDataService()

    engine = IndicatorEngine()

    analyzer = MarketStateAnalyzer()

    request = MarketDataRequest(
        ticker="TQQQ",
        period="1y",
        interval="1d",
    )

    df = service.get_price_history(request)

    indicators = engine.calculate(df)

    state = analyzer.analyze(indicators)

    print(state)
    