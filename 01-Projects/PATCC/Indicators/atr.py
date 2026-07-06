"""
PATCC ATR Indicator
"""

import pandas as pd

from Indicators.base_indicator import BaseIndicator


class ATRIndicator(BaseIndicator):

    def __init__(self, period: int = 14):
        super().__init__(f"ATR({period})")
        self.period = period

    def calculate(self, market_data):
        data = market_data.data

        required_columns = ["High", "Low", "Close"]

        for column in required_columns:
            if column not in data.columns:
                raise ValueError(f"DataFrame must contain '{column}' column.")

        high = data["High"]
        low = data["Low"]
        close = data["Close"]

        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = true_range.rolling(window=self.period).mean()

        return atr
        