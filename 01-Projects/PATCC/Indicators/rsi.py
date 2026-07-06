"""
PATCC RSI Indicator
"""

from Indicators.base_indicator import BaseIndicator


class RSIIndicator(BaseIndicator):

    def __init__(self, period: int = 14):
        super().__init__(f"RSI({period})")
        self.period = period

    def calculate(self, market_data):
        data = market_data.data

        if "Close" not in data.columns:
            raise ValueError("DataFrame must contain a 'Close' column.")

        close = data["Close"]

        delta = close.diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()

        rs = avg_gain / avg_loss

        rsi = 100 - (100 / (1 + rs))

        return rsi
        