"""
alert_engine.py

Detects significant market events.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class AlertEvent:
    name: str
    direction: str
    priority: str
    message: str


class AlertEngine:

    def analyze(self, indicators) -> List[AlertEvent]:

        alerts = []

        # -----------------------------------
        # RSI
        # -----------------------------------

        if indicators.rsi14 > 70:
            alerts.append(
                AlertEvent(
                    "RSI_OVERBOUGHT",
                    "Bearish",
                    "Medium",
                    "RSI has entered overbought territory.",
                )
            )

        elif indicators.rsi14 < 30:
            alerts.append(
                AlertEvent(
                    "RSI_OVERSOLD",
                    "Bullish",
                    "Medium",
                    "RSI has entered oversold territory.",
                )
            )

        # -----------------------------------
        # Relative Volume
        # -----------------------------------

        if indicators.rvol >= 2:

            alerts.append(
                AlertEvent(
                    "HIGH_RELATIVE_VOLUME",
                    "Bullish",
                    "High",
                    "Relative volume exceeds 2x average.",
                )
            )

        # -----------------------------------
        # ATR
        # -----------------------------------

        if indicators.atr_percent > 8:

            alerts.append(
                AlertEvent(
                    "HIGH_VOLATILITY",
                    "Neutral",
                    "Medium",
                    "ATR indicates elevated volatility.",
                )
            )

        return alerts
        