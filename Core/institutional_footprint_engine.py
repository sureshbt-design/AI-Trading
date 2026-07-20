"""
institutional_footprint_engine.py

Infers institutional accumulation or distribution from observable
price, volume, money-flow, trend, and relative-strength evidence.

This module does not claim to identify actual institutional orders.
It identifies an institutional-style market footprint.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass(frozen=True)
class InstitutionalFootprintResult:
    score: int
    classification: str
    confidence: str

    rvol: float
    rvol_status: str

    obv_trend: str
    cmf20: float
    cmf_status: str

    mfi14: float
    mfi_status: str

    accumulation_distribution_trend: str

    price_vs_dema8: str
    dema8_slope: str

    price_vs_vwap20: str

    relative_strength_20d: float | None
    relative_strength_status: str

    score_volume: int
    score_obv: int
    score_cmf: int
    score_mfi: int
    score_ad: int
    score_dema: int
    score_vwap: int
    score_relative_strength: int


class InstitutionalFootprintEngine:
    """
    Calculate an evidence-based institutional-footprint score.

    Maximum score: 100

    Components
    ----------
    Relative volume            15
    OBV trend                  15
    Chaikin Money Flow         15
    Money Flow Index           10
    A/D trend                  10
    DEMA-8 structure           15
    VWAP-20 structure          10
    Relative strength vs SPY   10
    """

    def calculate(
        self,
        indicators,
        security_df: pd.DataFrame,
        benchmark_df: pd.DataFrame | None = None,
    ) -> InstitutionalFootprintResult:

        volume_score = self._score_rvol(indicators.rvol)
        obv_score = self._score_obv(indicators.obv_trend)
        cmf_score = self._score_cmf(indicators.cmf20)
        mfi_score = self._score_mfi(indicators.mfi14)

        ad_score = self._score_ad(
            indicators.accumulation_distribution_trend
        )

        dema_score = self._score_dema(
            price_above=indicators.price_above_dema8,
            slope=indicators.dema8_slope,
        )

        vwap_score = self._score_vwap(
            indicators.price_above_vwap20
        )

        relative_strength = self._relative_strength_20d(
            security_df=security_df,
            benchmark_df=benchmark_df,
        )

        relative_strength_score = self._score_relative_strength(
            relative_strength
        )

        total_score = (
            volume_score
            + obv_score
            + cmf_score
            + mfi_score
            + ad_score
            + dema_score
            + vwap_score
            + relative_strength_score
        )

        total_score = max(0, min(100, int(round(total_score))))

        return InstitutionalFootprintResult(
            score=total_score,
            classification=self._classification(total_score),
            confidence=self._confidence(
                benchmark_available=relative_strength is not None,
                score=total_score,
            ),

            rvol=indicators.rvol,
            rvol_status=self._rvol_status(indicators.rvol),

            obv_trend=indicators.obv_trend,

            cmf20=indicators.cmf20,
            cmf_status=self._cmf_status(indicators.cmf20),

            mfi14=indicators.mfi14,
            mfi_status=self._mfi_status(indicators.mfi14),

            accumulation_distribution_trend=(
                indicators.accumulation_distribution_trend
            ),

            price_vs_dema8=(
                "Above"
                if indicators.price_above_dema8
                else "Below"
            ),

            dema8_slope=(
                "Rising"
                if indicators.dema8_slope > 0
                else "Falling"
                if indicators.dema8_slope < 0
                else "Flat"
            ),

            price_vs_vwap20=(
                "Above"
                if indicators.price_above_vwap20
                else "Below"
            ),

            relative_strength_20d=relative_strength,
            relative_strength_status=(
                self._relative_strength_status(relative_strength)
            ),

            score_volume=volume_score,
            score_obv=obv_score,
            score_cmf=cmf_score,
            score_mfi=mfi_score,
            score_ad=ad_score,
            score_dema=dema_score,
            score_vwap=vwap_score,
            score_relative_strength=relative_strength_score,
        )

    def _score_rvol(self, rvol: float) -> int:
        if rvol >= 2.0:
            return 15
        if rvol >= 1.5:
            return 13
        if rvol >= 1.2:
            return 10
        if rvol >= 1.0:
            return 8
        if rvol >= 0.8:
            return 5
        return 2

    def _score_obv(self, trend: str) -> int:
        if trend == "Rising":
            return 15
        if trend == "Flat":
            return 7
        return 0

    def _score_cmf(self, cmf: float) -> int:
        if cmf >= 0.20:
            return 15
        if cmf >= 0.10:
            return 13
        if cmf >= 0.05:
            return 10
        if cmf > 0:
            return 8
        if cmf > -0.05:
            return 5
        if cmf > -0.10:
            return 2
        return 0

    def _score_mfi(self, mfi: float) -> int:
        if 55 <= mfi <= 75:
            return 10
        if 50 <= mfi < 55:
            return 8
        if 75 < mfi <= 85:
            return 7
        if 40 <= mfi < 50:
            return 5
        if mfi > 85:
            return 3
        if 30 <= mfi < 40:
            return 3
        return 1

    def _score_ad(self, trend: str) -> int:
        if trend == "Rising":
            return 10
        if trend == "Flat":
            return 5
        return 0

    def _score_dema(
        self,
        price_above: bool,
        slope: float,
    ) -> int:
        if price_above and slope > 0:
            return 15
        if price_above and slope <= 0:
            return 10
        if not price_above and slope > 0:
            return 7
        return 0

    def _score_vwap(self, price_above: bool) -> int:
        return 10 if price_above else 0

    def _score_relative_strength(
        self,
        relative_strength: float | None,
    ) -> int:
        if relative_strength is None:
            return 5

        if relative_strength >= 5.0:
            return 10
        if relative_strength >= 2.0:
            return 9
        if relative_strength > 0:
            return 7
        if relative_strength > -2.0:
            return 4
        if relative_strength > -5.0:
            return 2
        return 0

    def _relative_strength_20d(
        self,
        security_df: pd.DataFrame,
        benchmark_df: pd.DataFrame | None,
    ) -> float | None:
        if benchmark_df is None:
            return None

        if security_df is None or security_df.empty:
            return None

        if benchmark_df.empty:
            return None

        if "Close" not in security_df.columns:
            return None

        if "Close" not in benchmark_df.columns:
            return None

        security_close = pd.to_numeric(
            security_df["Close"],
            errors="coerce",
        ).dropna()

        benchmark_close = pd.to_numeric(
            benchmark_df["Close"],
            errors="coerce",
        ).dropna()

        aligned = pd.concat(
            [
                security_close.rename("security"),
                benchmark_close.rename("benchmark"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(aligned) < 21:
            return None

        security_start = float(aligned["security"].iloc[-21])
        security_end = float(aligned["security"].iloc[-1])

        benchmark_start = float(aligned["benchmark"].iloc[-21])
        benchmark_end = float(aligned["benchmark"].iloc[-1])

        if security_start == 0 or benchmark_start == 0:
            return None

        security_return = (
            (security_end / security_start) - 1.0
        ) * 100.0

        benchmark_return = (
            (benchmark_end / benchmark_start) - 1.0
        ) * 100.0

        relative_strength = security_return - benchmark_return

        if not math.isfinite(relative_strength):
            return None

        return float(relative_strength)

    def _classification(self, score: int) -> str:
        if score >= 80:
            return "Strong Accumulation"
        if score >= 65:
            return "Accumulation"
        if score >= 45:
            return "Neutral / Unconfirmed"
        if score >= 30:
            return "Weak / Distribution Risk"
        return "Distribution"

    def _confidence(
        self,
        benchmark_available: bool,
        score: int,
    ) -> str:
        if benchmark_available and (score >= 75 or score <= 30):
            return "High"

        if benchmark_available:
            return "Moderate"

        return "Limited — benchmark unavailable"

    def _rvol_status(self, rvol: float) -> str:
        if rvol >= 1.5:
            return "High Participation"
        if rvol >= 1.0:
            return "Above Average"
        if rvol >= 0.8:
            return "Near Average"
        return "Low Participation"

    def _cmf_status(self, cmf: float) -> str:
        if cmf >= 0.10:
            return "Positive Inflow"
        if cmf > 0:
            return "Mild Inflow"
        if cmf > -0.10:
            return "Mild Outflow"
        return "Negative Outflow"

    def _mfi_status(self, mfi: float) -> str:
        if mfi >= 80:
            return "Overbought"
        if mfi >= 55:
            return "Positive"
        if mfi >= 45:
            return "Neutral"
        if mfi >= 20:
            return "Weak"
        return "Oversold"

    def _relative_strength_status(
        self,
        relative_strength: float | None,
    ) -> str:
        if relative_strength is None:
            return "Unavailable"

        if relative_strength >= 2.0:
            return "Outperforming SPY"

        if relative_strength > -2.0:
            return "In Line With SPY"

        return "Underperforming SPY"
        