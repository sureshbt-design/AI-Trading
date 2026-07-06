"""
market_data_service.py

Single gateway for downloading and validating market data.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf


@dataclass
class MarketDataRequest:
    ticker: str
    period: str = "6mo"
    interval: str = "1d"


class MarketDataService:
    """Download and validate OHLCV market data."""

    REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

    def get_price_history(self, request: MarketDataRequest) -> pd.DataFrame:
        ticker = request.ticker.upper().strip()

        data = yf.download(
            ticker,
            period=request.period,
            interval=request.interval,
            progress=False,
            auto_adjust=False,
        )

        return self._validate(ticker, data)

    def _validate(self, ticker: str, data: Optional[pd.DataFrame]) -> pd.DataFrame:
        if data is None or data.empty:
            raise ValueError(f"No market data returned for ticker: {ticker}")

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        missing = [col for col in self.REQUIRED_COLUMNS if col not in data.columns]
        if missing:
            raise ValueError(f"{ticker} missing required columns: {missing}")

        cleaned = data[self.REQUIRED_COLUMNS].dropna()

        if cleaned.empty:
            raise ValueError(f"{ticker} has no valid OHLCV rows after cleanup")

        return cleaned


if __name__ == "__main__":
    service = MarketDataService()

    request = MarketDataRequest(
        ticker="TQQQ",
        period="3mo",
        interval="1d",
    )

    df = service.get_price_history(request)

    print(df.tail())
    print(f"\nRows returned: {len(df)}")
    