from dataclasses import dataclass
from typing import Optional


@dataclass
class TargetLevels:
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
    Calculates dynamic support, resistance, price targets,
    stop loss, reward/risk, and basic target probabilities.
    """

    def calculate(self, df, current_price: Optional[float] = None) -> TargetLevels:
        if df is None or df.empty:
            raise ValueError("Price history dataframe is empty")

        required_columns = {"High", "Low", "Close"}
        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        if current_price is None:
            current_price = float(df["Close"].iloc[-1])

        recent = df.tail(60)

        support = float(recent["Low"].min())
        resistance = float(recent["High"].max())

        price_range = resistance - support

        if price_range <= 0:
            price_range = current_price * 0.05

        target_1 = current_price + price_range * 0.382
        target_2 = current_price + price_range * 0.618
        target_3 = current_price + price_range * 1.000

        stop_loss = support * 0.98

        risk = current_price - stop_loss

        def rr(target: float) -> float:
            if risk <= 0:
                return 0.0
            return round((target - current_price) / risk, 2)

        probability_1 = 78.0
        probability_2 = 62.0
        probability_3 = 42.0

        return TargetLevels(
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
        