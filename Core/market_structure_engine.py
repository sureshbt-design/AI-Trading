from dataclasses import dataclass
from typing import List, Optional
import pandas as pd


@dataclass
class SwingPoint:
    index: int
    price: float
    kind: str  # "HIGH" or "LOW"


@dataclass
class MarketStructureResult:
    trend: str
    latest_structure: str
    latest_event: str
    swing_highs: List[SwingPoint]
    swing_lows: List[SwingPoint]
    confidence: int


class MarketStructureEngine:
    """
    Detects basic market structure:
    - Swing highs
    - Swing lows
    - Higher highs / lower highs
    - Higher lows / lower lows
    - Break of Structure
    - Change of Character
    """

    def __init__(self, lookback: int = 2):
        self.lookback = lookback

    def analyze(self, df: pd.DataFrame) -> MarketStructureResult:
        if df is None or df.empty:
            return self._empty_result("No data")

        required = {"High", "Low", "Close"}
        missing = required - set(df.columns)

        if missing:
            return self._empty_result(f"Missing columns: {missing}")

        swing_highs = self._find_swing_highs(df)
        swing_lows = self._find_swing_lows(df)

        trend = self._detect_trend(swing_highs, swing_lows)
        latest_structure = self._latest_structure(swing_highs, swing_lows)
        latest_event = self._detect_event(df, swing_highs, swing_lows, trend)
        confidence = self._confidence_score(trend, latest_event, swing_highs, swing_lows)

        return MarketStructureResult(
            trend=trend,
            latest_structure=latest_structure,
            latest_event=latest_event,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            confidence=confidence,
        )

    def _find_swing_highs(self, df: pd.DataFrame) -> List[SwingPoint]:
        swings = []

        for i in range(self.lookback, len(df) - self.lookback):
            current_high = df["High"].iloc[i]
            left_highs = df["High"].iloc[i - self.lookback:i]
            right_highs = df["High"].iloc[i + 1:i + 1 + self.lookback]

            if current_high > left_highs.max() and current_high > right_highs.max():
                swings.append(SwingPoint(index=i, price=float(current_high), kind="HIGH"))

        return swings

    def _find_swing_lows(self, df: pd.DataFrame) -> List[SwingPoint]:
        swings = []

        for i in range(self.lookback, len(df) - self.lookback):
            current_low = df["Low"].iloc[i]
            left_lows = df["Low"].iloc[i - self.lookback:i]
            right_lows = df["Low"].iloc[i + 1:i + 1 + self.lookback]

            if current_low < left_lows.min() and current_low < right_lows.min():
                swings.append(SwingPoint(index=i, price=float(current_low), kind="LOW"))

        return swings

    def _detect_trend(
        self,
        highs: List[SwingPoint],
        lows: List[SwingPoint],
    ) -> str:
        if len(highs) < 2 or len(lows) < 2:
            return "Unknown"

        last_high = highs[-1].price
        prev_high = highs[-2].price

        last_low = lows[-1].price
        prev_low = lows[-2].price

        if last_high > prev_high and last_low > prev_low:
            return "Bullish"

        if last_high < prev_high and last_low < prev_low:
            return "Bearish"

        return "Sideways"

    def _latest_structure(
        self,
        highs: List[SwingPoint],
        lows: List[SwingPoint],
    ) -> str:
        labels = []

        if len(highs) >= 2:
            if highs[-1].price > highs[-2].price:
                labels.append("HH")
            else:
                labels.append("LH")

        if len(lows) >= 2:
            if lows[-1].price > lows[-2].price:
                labels.append("HL")
            else:
                labels.append("LL")

        if not labels:
            return "Insufficient structure"

        return " / ".join(labels)

    def _detect_event(
        self,
        df: pd.DataFrame,
        highs: List[SwingPoint],
        lows: List[SwingPoint],
        trend: str,
    ) -> str:
        if len(highs) < 2 or len(lows) < 2:
            return "No clear event"

        latest_close = float(df["Close"].iloc[-1])
        previous_swing_high = highs[-1].price
        previous_swing_low = lows[-1].price

        if latest_close > previous_swing_high:
            if trend == "Bullish":
                return "Bullish BOS"
            if trend == "Bearish":
                return "Bullish CHOCH"
            return "Bullish breakout"

        if latest_close < previous_swing_low:
            if trend == "Bearish":
                return "Bearish BOS"
            if trend == "Bullish":
                return "Bearish CHOCH"
            return "Bearish breakdown"

        return "Inside structure"

    def _confidence_score(
        self,
        trend: str,
        latest_event: str,
        highs: List[SwingPoint],
        lows: List[SwingPoint],
    ) -> int:
        score = 0

        if trend in ["Bullish", "Bearish"]:
            score += 40
        elif trend == "Sideways":
            score += 20

        if "BOS" in latest_event:
            score += 35
        elif "CHOCH" in latest_event:
            score += 30
        elif "breakout" in latest_event or "breakdown" in latest_event:
            score += 20
        elif latest_event == "Inside structure":
            score += 10

        if len(highs) >= 3 and len(lows) >= 3:
            score += 20
        elif len(highs) >= 2 and len(lows) >= 2:
            score += 10

        return min(score, 100)

    def _empty_result(self, reason: str) -> MarketStructureResult:
        return MarketStructureResult(
            trend="Unknown",
            latest_structure="Unavailable",
            latest_event=reason,
            swing_highs=[],
            swing_lows=[],
            confidence=0,
        )
        