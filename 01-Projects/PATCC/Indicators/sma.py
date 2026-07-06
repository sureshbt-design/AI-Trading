"""
PATCC SMA Indicator
"""

from Indicators.base_indicator import BaseIndicator


class SMAIndicator(BaseIndicator):

    def __init__(self, period: int = 20):
        super().__init__(f"SMA({period})")
        self.period = period

    def calculate(self, market_data):
        data = market_data.data

        if "Close" not in data.columns:
            raise ValueError("DataFrame must contain a 'Close' column.")

        return data["Close"].rolling(
            window=self.period
        ).mean()
        