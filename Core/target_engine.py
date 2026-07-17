"""
target_engine.py

PATCC target, stop-loss, risk/reward, and probability engine.
"""

from __future__ import annotations

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
    Calculates long-side reference targets using:

    - Recent structural support and resistance
    - Average True Range
    - Minimum stop distance
    - Directionally valid and ascending targets
    - Target-specific probability estimates

    These are reference levels. The recommendation engine determines
    whether a long trade is actionable, watch-only, or should be avoided.
    """

    ATR_PERIOD = 14
    LOOKBACK_PERIOD = 60

    MINIMUM_STOP_ATR = 1.50
    TARGET_1_ATR = 1.00
    TARGET_2_ATR = 2.00
    TARGET_3_ATR = 3.00
    MINIMUM_TARGET_SPACING_ATR = 0.75

    def calculate(
        self,
        df: pd.DataFrame,
        current_price: Optional[float] = None,
    ) -> TargetLevels:
        clean_df = self._validate_dataframe(df)

        if current_price is None:
            current_price = float(clean_df["Close"].iloc[-1])
        else:
            current_price = float(current_price)

        if current_price <= 0:
            raise ValueError("Current price must be greater than zero")

        recent = clean_df.tail(self.LOOKBACK_PERIOD).copy()
        atr = self._calculate_atr(recent)

        support = self._nearest_support(recent, current_price)
        resistance = self._nearest_resistance(recent, current_price)

        if support is None:
            support = float(recent["Low"].tail(20).min())

        if resistance is None:
            resistance = float(recent["High"].tail(20).max())

        # Ensure structural levels remain directionally valid.
        if support >= current_price:
            support = current_price - atr

        if resistance <= current_price:
            resistance = current_price + atr

        # Do not allow a very close support print to produce an
        # unrealistically tight stop-loss.
        structural_stop = support - (0.50 * atr)
        minimum_atr_stop = current_price - (self.MINIMUM_STOP_ATR * atr)

        stop_loss = min(structural_stop, minimum_atr_stop)

        if stop_loss <= 0:
            stop_loss = max(
                current_price * 0.90,
                current_price - (self.MINIMUM_STOP_ATR * atr),
            )

        risk = current_price - stop_loss

        if risk <= 0:
            raise ValueError("Calculated trade risk must be greater than zero")

        targets = self._build_long_targets(
            current_price=current_price,
            resistance=resistance,
            atr=atr,
        )

        target_1, target_2, target_3 = targets

        risk_reward_1 = self._risk_reward(
            current_price,
            target_1,
            stop_loss,
        )
        risk_reward_2 = self._risk_reward(
            current_price,
            target_2,
            stop_loss,
        )
        risk_reward_3 = self._risk_reward(
            current_price,
            target_3,
            stop_loss,
        )

        probabilities = self._calculate_probabilities(
            current_price=current_price,
            targets=targets,
            atr=atr,
            risk_rewards=[
                risk_reward_1,
                risk_reward_2,
                risk_reward_3,
            ],
        )

        probability_1, probability_2, probability_3 = probabilities

        return TargetLevels(
            current_price=round(current_price, 2),
            support=round(support, 2),
            resistance=round(resistance, 2),
            target_1=round(target_1, 2),
            target_2=round(target_2, 2),
            target_3=round(target_3, 2),
            stop_loss=round(stop_loss, 2),
            risk_reward_1=risk_reward_1,
            risk_reward_2=risk_reward_2,
            risk_reward_3=risk_reward_3,
            probability_1=probability_1,
            probability_2=probability_2,
            probability_3=probability_3,
        )

    def _validate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            raise ValueError("Price history dataframe is empty")

        required_columns = {"High", "Low", "Close"}
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        clean_df = df.dropna(
            subset=["High", "Low", "Close"]
        ).copy()

        if len(clean_df) < 20:
            raise ValueError(
                "Not enough price history to calculate reliable targets"
            )

        return clean_df

    def _build_long_targets(
        self,
        current_price: float,
        resistance: float,
        atr: float,
    ) -> tuple[float, float, float]:
        """
        Builds three strictly ascending long-side targets.

        Target 1 honors nearby resistance but must be at least one ATR
        above the current price. Targets 2 and 3 use progressively larger
        ATR extensions and minimum spacing.
        """

        target_1 = max(
            resistance,
            current_price + (self.TARGET_1_ATR * atr),
        )

        target_2 = max(
            current_price + (self.TARGET_2_ATR * atr),
            target_1 + (self.MINIMUM_TARGET_SPACING_ATR * atr),
        )

        target_3 = max(
            current_price + (self.TARGET_3_ATR * atr),
            target_2 + (self.MINIMUM_TARGET_SPACING_ATR * atr),
        )

        targets = sorted([target_1, target_2, target_3])

        minimum_increment = max(atr * 0.25, current_price * 0.001)

        for index in range(1, len(targets)):
            if targets[index] <= targets[index - 1]:
                targets[index] = targets[index - 1] + minimum_increment

        if any(target <= current_price for target in targets):
            raise ValueError(
                "Long-side targets must be greater than current price"
            )

        return targets[0], targets[1], targets[2]

    def _nearest_support(
        self,
        df: pd.DataFrame,
        current_price: float,
    ) -> Optional[float]:
        lows_below_price = df.loc[
            df["Low"] < current_price,
            "Low",
        ]

        if lows_below_price.empty:
            return None

        return float(lows_below_price.max())

    def _nearest_resistance(
        self,
        df: pd.DataFrame,
        current_price: float,
    ) -> Optional[float]:
        highs_above_price = df.loc[
            df["High"] > current_price,
            "High",
        ]

        if highs_above_price.empty:
            return None

        return float(highs_above_price.min())

    def _calculate_atr(
        self,
        df: pd.DataFrame,
        period: int = ATR_PERIOD,
    ) -> float:
        high_low = df["High"] - df["Low"]
        high_previous_close = (
            df["High"] - df["Close"].shift(1)
        ).abs()
        low_previous_close = (
            df["Low"] - df["Close"].shift(1)
        ).abs()

        true_range = pd.concat(
            [
                high_low,
                high_previous_close,
                low_previous_close,
            ],
            axis=1,
        ).max(axis=1)

        atr = true_range.rolling(
            window=period,
            min_periods=period,
        ).mean().iloc[-1]

        if pd.isna(atr) or atr <= 0:
            atr = float(
                high_low.tail(period).mean()
            )

        if pd.isna(atr) or atr <= 0:
            raise ValueError(
                "Unable to calculate a valid Average True Range"
            )

        return float(atr)

    def _risk_reward(
        self,
        current_price: float,
        target: float,
        stop_loss: float,
    ) -> float:
        risk = current_price - stop_loss
        reward = target - current_price

        if risk <= 0 or reward <= 0:
            return 0.0

        return round(reward / risk, 2)

    def _calculate_probabilities(
        self,
        current_price: float,
        targets: tuple[float, float, float],
        atr: float,
        risk_rewards: list[float],
    ) -> tuple[float, float, float]:
        """
        Assigns a separate probability to each target.

        Probability declines as ATR distance increases. Risk/reward
        provides a modest quality adjustment but cannot make a farther
        target more probable than a nearer target.
        """

        probabilities: list[float] = []

        for target, risk_reward in zip(targets, risk_rewards):
            distance_atr = (
                target - current_price
            ) / atr

            probability = 88.0 - (distance_atr * 13.0)

            if risk_reward >= 2.0:
                probability += 3.0
            elif risk_reward < 1.0:
                probability -= 5.0

            probability = max(
                20.0,
                min(85.0, probability),
            )

            probabilities.append(probability)

        # Enforce probability decay between progressively farther targets.
        probabilities[1] = min(
            probabilities[1],
            probabilities[0] - 7.0,
        )
        probabilities[2] = min(
            probabilities[2],
            probabilities[1] - 7.0,
        )

        probabilities = [
            round(max(20.0, probability), 0)
            for probability in probabilities
        ]

        return (
            probabilities[0],
            probabilities[1],
            probabilities[2],
        )
        