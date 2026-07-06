"""
indicator_engine.py

Calculates core technical indicators from OHLCV price data.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class IndicatorResult:
    close: float
    ema20: float
    ema50: float
    ema200: float | None
    atr14: float
    atr_percent: float
    rsi14: float
    avg_volume20: float
    rvol: float


class IndicatorEngine:
    """Calculate technical indicators from OHLCV data."""

    def calculate(self, df: pd.DataFrame) -> IndicatorResult:
        if df is None or df.empty:
            raise ValueError("Price data is empty")

        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required - set(df.columns)

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        data = df.copy()

        close = data["Close"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]

        data["EMA20"] = close.ewm(span=20, adjust=False).mean()
        data["EMA50"] = close.ewm(span=50, adjust=False).mean()
        data["EMA200"] = close.ewm(span=200, adjust=False).mean()

        data["ATR14"] = self._atr(data, period=14)
        data["RSI14"] = self._rsi(close, period=14)

        data["AVG_VOLUME20"] = volume.rolling(window=20).mean()
        data["RVOL"] = volume / data["AVG_VOLUME20"]

        latest = data.iloc[-1]

        close_value = float(latest["Close"])
        atr_value = float(latest["ATR14"])

        ema200_value = (
            float(latest["EMA200"])
            if len(data) >= 200
            else None
        )

        return IndicatorResult(
            close=close_value,
            ema20=float(latest["EMA20"]),
            ema50=float(latest["EMA50"]),
            ema200=ema200_value,
            atr14=atr_value,
            atr_percent=(atr_value / close_value) * 100,
            rsi14=float(latest["RSI14"]),
            avg_volume20=float(latest["AVG_VOLUME20"]),
            rvol=float(latest["RVOL"]),
        )

    def _atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
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

        return true_range.rolling(window=period).mean()

    def _rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()

        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi


if __name__ == "__main__":
    from market_data_service import MarketDataRequest, MarketDataService

    service = MarketDataService()
    engine = IndicatorEngine()

    request = MarketDataRequest(
        ticker="TQQQ",
        period="1y",
        interval="1d",
    )

    df = service.get_price_history(request)
    indicators = engine.calculate(df)

    print(indicators)
    