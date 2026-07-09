from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class TargetLevels:
    current_price: float
    support: float
    resistance: float
    target_1: float
    target_2: float
    target_3: float
    stop_loss: float
    risk_reward_1: float
    risk_reward_2: float
    risk_reward_3: float
    probability_1: float
    probability_2: float
    probability_3: float


class TargetEngine:
    """
    Calculates support, resistance, targets, stop loss, reward/risk,
    and basic target probabilities using recent validated price data.
    """

    def calculate(self, df: pd.DataFrame, current_price: Optional[float] = None) -> TargetLevels:
        if df is None or df.empty:
            raise ValueError("Price history dataframe is empty")

        required_columns = {"High", "Low", "Close"}
        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df = df.dropna(subset=["High", "Low", "Close"])

        if len(df) < 20:
            raise ValueError("Not enough price history to calculate reliable targets")

        if current_price is None:
            current_price = float(df["Close"].iloc[-1])

        recent = df.tail(60)

        support = self._nearest_support(recent, current_price)
        resistance = self._nearest_resistance(recent, current_price)

        atr = self._calculate_atr(recent)

        if support is None:
            support = float(recent["Low"].tail(20).min())

        if resistance is None:
            resistance = float(recent["High"].tail(20).max())

        if resistance <= current_price:
            resistance = current_price + atr * 2

        if support >= current_price:
            support = current_price - atr * 2

        stop_loss = support - atr * 0.5

        risk = current_price - stop_loss

        target_1 = resistance
        target_2 = current_price + (current_price - support) * 1.5
        target_3 = current_price + (current_price - support) * 2.5

        def rr(target: float) -> float:
            if risk <= 0:
                return 0.0
            return round((target - current_price) / risk, 2)

        probability_1 = self._target_probability(rr(target_1))
        probability_2 = self._target_probability(rr(target_2))
        probability_3 = self._target_probability(rr(target_3))

        return TargetLevels(
            current_price=round(current_price, 2),
            support=round(support, 2),
            resistance=round(resistance, 2),
            target_1=round(target_1, 2),
            target_2=round(target_2, 2),
            target_3=round(target_3, 2),
            stop_loss=round(stop_loss, 2),
            risk_reward_1=rr(target_1),
            risk_reward_2=rr(target_2),
            risk_reward_3=rr(target_3),
            probability_1=probability_1,
            probability_2=probability_2,
            probability_3=probability_3,
        )

    def _nearest_support(self, df: pd.DataFrame, current_price: float) -> Optional[float]:
        lows_below_price = df[df["Low"] < current_price]["Low"]

        if lows_below_price.empty:
            return None

        return float(lows_below_price.max())

    def _nearest_resistance(self, df: pd.DataFrame, current_price: float) -> Optional[float]:
        highs_above_price = df[df["High"] > current_price]["High"]

        if highs_above_price.empty:
            return None

        return float(highs_above_price.min())

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high_low = df["High"] - df["Low"]
        high_close = (df["High"] - df["Close"].shift()).abs()
        low_close = (df["Low"] - df["Close"].shift()).abs()

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean().iloc[-1]

        if pd.isna(atr) or atr <= 0:
            atr = float((df["High"] - df["Low"]).tail(period).mean())

        return float(atr)

    def _target_probability(self, risk_reward: float) -> float:
        if risk_reward <= 0:
            return 0.0

        if risk_reward < 1:
            return 75.0

        if risk_reward < 2:
            return 62.0

        if risk_reward < 3:
            return 48.0

        return 35.0
        