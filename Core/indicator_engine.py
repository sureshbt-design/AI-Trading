"""
indicator_engine.py

Calculates technical, volume, and money-flow indicators from OHLCV data.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass(frozen=True)
class IndicatorResult:
    close: float

    ema20: float
    ema50: float
    ema200: float | None

    dema8: float
    dema8_previous: float
    dema8_slope: float
    price_above_dema8: bool

    vwap20: float
    price_above_vwap20: bool

    atr14: float
    atr_percent: float
    rsi14: float

    current_volume: float
    avg_volume20: float
    rvol: float

    obv: float
    obv_slope20: float
    obv_trend: str

    cmf20: float
    mfi14: float

    accumulation_distribution: float
    accumulation_distribution_slope20: float
    accumulation_distribution_trend: str


class IndicatorEngine:
    """Calculate technical and institutional-footprint indicators."""

    def calculate(self, df: pd.DataFrame) -> IndicatorResult:
        if df is None or df.empty:
            raise ValueError("Price data is empty")

        required = {"Open", "High", "Low", "Close", "Volume"}
        missing = required - set(df.columns)

        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        data = df.copy()

        for column in required:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

        data = data.dropna(
            subset=["Open", "High", "Low", "Close", "Volume"]
        )

        if len(data) < 30:
            raise ValueError(
                "At least 30 valid OHLCV rows are required "
                "for indicator calculation"
            )

        close = data["Close"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]

        # ---------------------------------------------------------
        # Moving averages
        # ---------------------------------------------------------

        data["EMA20"] = close.ewm(span=20, adjust=False).mean()
        data["EMA50"] = close.ewm(span=50, adjust=False).mean()
        data["EMA200"] = close.ewm(span=200, adjust=False).mean()

        ema8_first = close.ewm(span=8, adjust=False).mean()
        ema8_second = ema8_first.ewm(span=8, adjust=False).mean()

        data["DEMA8"] = (2.0 * ema8_first) - ema8_second

        # ---------------------------------------------------------
        # Volatility and momentum
        # ---------------------------------------------------------

        data["ATR14"] = self._atr(data, period=14)
        data["RSI14"] = self._rsi(close, period=14)

        # ---------------------------------------------------------
        # Volume
        # ---------------------------------------------------------

        data["AVG_VOLUME20"] = volume.rolling(
            window=20,
            min_periods=20,
        ).mean()

        data["RVOL"] = self._safe_divide(
            volume,
            data["AVG_VOLUME20"],
        )

        # ---------------------------------------------------------
        # Rolling VWAP
        #
        # This is a 20-bar rolling volume-weighted average price.
        # For daily data it is VWAP-20; for intraday data it is a
        # rolling 20-bar VWAP.
        # ---------------------------------------------------------

        typical_price = (high + low + close) / 3.0

        rolling_price_volume = (
            typical_price * volume
        ).rolling(
            window=20,
            min_periods=20,
        ).sum()

        rolling_volume = volume.rolling(
            window=20,
            min_periods=20,
        ).sum()

        data["VWAP20"] = self._safe_divide(
            rolling_price_volume,
            rolling_volume,
        )

        # ---------------------------------------------------------
        # On-Balance Volume
        # ---------------------------------------------------------

        close_change = close.diff()

        volume_direction = pd.Series(
            0.0,
            index=data.index,
            dtype="float64",
        )

        volume_direction.loc[close_change > 0] = 1.0
        volume_direction.loc[close_change < 0] = -1.0

        data["OBV"] = (
            volume_direction * volume
        ).fillna(0.0).cumsum()

        data["OBV_SLOPE20"] = self._rolling_slope(
            data["OBV"],
            period=20,
        )

        # ---------------------------------------------------------
        # Chaikin Money Flow
        # ---------------------------------------------------------

        high_low_range = high - low

        money_flow_multiplier = self._safe_divide(
            ((close - low) - (high - close)),
            high_low_range,
        ).fillna(0.0)

        money_flow_volume = money_flow_multiplier * volume

        data["CMF20"] = self._safe_divide(
            money_flow_volume.rolling(
                window=20,
                min_periods=20,
            ).sum(),
            volume.rolling(
                window=20,
                min_periods=20,
            ).sum(),
        )

        # ---------------------------------------------------------
        # Money Flow Index
        # ---------------------------------------------------------

        data["MFI14"] = self._mfi(
            high=high,
            low=low,
            close=close,
            volume=volume,
            period=14,
        )

        # ---------------------------------------------------------
        # Accumulation / Distribution Line
        # ---------------------------------------------------------

        data["AD_LINE"] = money_flow_volume.fillna(0.0).cumsum()

        data["AD_SLOPE20"] = self._rolling_slope(
            data["AD_LINE"],
            period=20,
        )

        latest = data.iloc[-1]
        previous = data.iloc[-2]

        close_value = self._finite_float(
            latest["Close"],
            "Close",
        )

        atr_value = self._finite_float(
            latest["ATR14"],
            "ATR14",
        )

        ema200_value: float | None = None

        if len(data) >= 200 and self._is_finite(latest["EMA200"]):
            ema200_value = float(latest["EMA200"])

        dema8_value = self._finite_float(
            latest["DEMA8"],
            "DEMA8",
        )

        previous_dema8 = self._finite_float(
            previous["DEMA8"],
            "Previous DEMA8",
        )

        dema8_slope = dema8_value - previous_dema8

        vwap20_value = self._finite_float(
            latest["VWAP20"],
            "VWAP20",
        )

        obv_slope = self._finite_float(
            latest["OBV_SLOPE20"],
            "OBV slope",
        )

        ad_slope = self._finite_float(
            latest["AD_SLOPE20"],
            "A/D slope",
        )

        return IndicatorResult(
            close=close_value,

            ema20=self._finite_float(latest["EMA20"], "EMA20"),
            ema50=self._finite_float(latest["EMA50"], "EMA50"),
            ema200=ema200_value,

            dema8=dema8_value,
            dema8_previous=previous_dema8,
            dema8_slope=dema8_slope,
            price_above_dema8=close_value > dema8_value,

            vwap20=vwap20_value,
            price_above_vwap20=close_value > vwap20_value,

            atr14=atr_value,
            atr_percent=(atr_value / close_value) * 100.0,
            rsi14=self._finite_float(latest["RSI14"], "RSI14"),

            current_volume=self._finite_float(
                latest["Volume"],
                "Current volume",
            ),
            avg_volume20=self._finite_float(
                latest["AVG_VOLUME20"],
                "Average volume 20",
            ),
            rvol=self._finite_float(latest["RVOL"], "RVOL"),

            obv=self._finite_float(latest["OBV"], "OBV"),
            obv_slope20=obv_slope,
            obv_trend=self._trend_label(obv_slope),

            cmf20=self._finite_float(latest["CMF20"], "CMF20"),
            mfi14=self._finite_float(latest["MFI14"], "MFI14"),

            accumulation_distribution=self._finite_float(
                latest["AD_LINE"],
                "Accumulation/Distribution Line",
            ),
            accumulation_distribution_slope20=ad_slope,
            accumulation_distribution_trend=self._trend_label(
                ad_slope
            ),
        )

    def _atr(
        self,
        data: pd.DataFrame,
        period: int = 14,
    ) -> pd.Series:
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

        return true_range.rolling(
            window=period,
            min_periods=period,
        ).mean()

    def _rsi(
        self,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        delta = close.diff()

        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)

        avg_gain = gain.ewm(
            alpha=1.0 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        avg_loss = loss.ewm(
            alpha=1.0 / period,
            adjust=False,
            min_periods=period,
        ).mean()

        rs = self._safe_divide(avg_gain, avg_loss)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        no_losses = avg_loss == 0
        no_gains = avg_gain == 0

        rsi = rsi.mask(no_losses & ~no_gains, 100.0)
        rsi = rsi.mask(no_gains & ~no_losses, 0.0)
        rsi = rsi.mask(no_gains & no_losses, 50.0)

        return rsi

    def _mfi(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        typical_price = (high + low + close) / 3.0
        raw_money_flow = typical_price * volume

        direction = typical_price.diff()

        positive_flow = raw_money_flow.where(
            direction > 0,
            0.0,
        )

        negative_flow = raw_money_flow.where(
            direction < 0,
            0.0,
        )

        positive_sum = positive_flow.rolling(
            window=period,
            min_periods=period,
        ).sum()

        negative_sum = negative_flow.rolling(
            window=period,
            min_periods=period,
        ).sum()

        money_ratio = self._safe_divide(
            positive_sum,
            negative_sum,
        )

        mfi = 100.0 - (100.0 / (1.0 + money_ratio))

        mfi = mfi.mask(
            (negative_sum == 0) & (positive_sum > 0),
            100.0,
        )

        mfi = mfi.mask(
            (positive_sum == 0) & (negative_sum > 0),
            0.0,
        )

        mfi = mfi.mask(
            (positive_sum == 0) & (negative_sum == 0),
            50.0,
        )

        return mfi

    def _rolling_slope(
        self,
        series: pd.Series,
        period: int,
    ) -> pd.Series:
        return series.diff(period) / float(period)

    def _safe_divide(
        self,
        numerator: pd.Series,
        denominator: pd.Series,
    ) -> pd.Series:
        """
        Divide two numeric series safely.

        Non-numeric values are converted to NaN, and zero denominators
        are masked before division. This prevents pandas NAType values
        from reaching downstream float conversions.
        """

        numeric_numerator = pd.to_numeric(
            numerator,
            errors="coerce",
        ).astype("float64")

        numeric_denominator = pd.to_numeric(
            denominator,
            errors="coerce",
        ).astype("float64")

        numeric_denominator = numeric_denominator.mask(
            numeric_denominator == 0.0
        )

        return numeric_numerator.div(
            numeric_denominator
        )

    def _trend_label(self, slope: float) -> str:
        if slope > 0:
            return "Rising"

        if slope < 0:
            return "Falling"

        return "Flat"

    def _is_finite(self, value: object) -> bool:
        try:
            return math.isfinite(float(value))
        except (TypeError, ValueError):
            return False

    def _finite_float(
        self,
        value: object,
        field_name: str,
    ) -> float:
        if not self._is_finite(value):
            raise ValueError(
                f"{field_name} could not be calculated from the "
                "available price history"
            )

        return float(value)


if __name__ == "__main__":
    from Core.market_data_service import (
        MarketDataRequest,
        MarketDataService,
    )

    service = MarketDataService()
    engine = IndicatorEngine()

    response = service.get_price_history(
        MarketDataRequest(
            ticker="TQQQ",
            period="1y",
            interval="1d",
        )
    )

    indicators = engine.calculate(response.data)
    print(indicators)
    