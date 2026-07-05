"""
PATCC EMA Indicator
"""

import pandas as pd

from Indicators.base_indicator import BaseIndicator


class EMAIndicator(BaseIndicator):

    def __init__(self, period: int = 20):
        super().__init__(f"EMA({period})")
        self.period = period

    def calculate(self, data: pd.DataFrame):

        if "Close" not in data.columns:
            raise ValueError("DataFrame must contain a 'Close' column.")

        return data["Close"].ewm(
            span=self.period,
            adjust=False
        ).mean()
        