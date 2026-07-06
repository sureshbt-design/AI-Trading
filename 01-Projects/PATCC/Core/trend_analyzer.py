"""
PATCC Trend Analyzer
"""

from Models.trend_models import TrendSignal


class TrendAnalyzer:

    def analyze(
        self,
        price: float,
        ema20: float,
        sma20: float,
        sma50: float,
    ) -> TrendSignal:

        score = 0
        reasons = []

        if price > ema20:
            score += 30
            reasons.append("Price above EMA20")
        else:
            reasons.append("Price below EMA20")

        if price > sma20:
            score += 25
            reasons.append("Price above SMA20")
        else:
            reasons.append("Price below SMA20")

        if sma20 > sma50:
            score += 30
            reasons.append("SMA20 above SMA50")
        else:
            reasons.append("SMA20 below SMA50")

        if price > sma50:
            score += 15
            reasons.append("Price above SMA50")
        else:
            reasons.append("Price below SMA50")

        if score >= 80:
            direction = "Bullish"
            strength = "Strong"
        elif score >= 60:
            direction = "Bullish"
            strength = "Moderate"
        elif score >= 40:
            direction = "Neutral"
            strength = "Mixed"
        else:
            direction = "Bearish"
            strength = "Weak"

        return TrendSignal(
            direction=direction,
            strength=strength,
            score=score,
            reasons=reasons,
        )
        