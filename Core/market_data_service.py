"""
market_data_service.py

Single gateway for downloading and validating market data.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import yfinance as yf

from dataclasses import dataclass
from datetime import datetime
from Core.timeframe_manager import TimeframeManager

@dataclass
class MarketDataResponse:
    ticker: str
    source: str
    mode: str
    realtime: bool
    last_bar: datetime
    rows: int
    data: pd.DataFrame

@dataclass
class MarketDataRequest:
    """
    Request object for market data retrieval.

    Timeframe may be specified either directly (5m, 1h, 1d, etc.)
    or by providing explicit period/interval values.
    """

    ticker: str

    timeframe: str = "1d"

    period: str | None = None
    interval: str | None = None

    auto_adjust: bool = True


class MarketDataService:
    """Download and validate OHLCV market data."""

    REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

    def get_price_history(self, request: MarketDataRequest) -> MarketDataResponse:
        ticker = request.ticker.upper().strip()
        # Resolve timeframe defaults
        config = TimeframeManager.get_config(request.timeframe)

        period = request.period or config.period
        interval = request.interval or config.interval

        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=request.auto_adjust,
            progress=False,
        )

        cleaned = self._validate(ticker, df)

        return MarketDataResponse(
           ticker=ticker,
           source="Yahoo Finance",
           mode="Research / Watchlist",
           realtime=False,
           last_bar=cleaned.index[-1].to_pydatetime(),
           rows=len(cleaned),
           data=cleaned,
        )

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

    response = service.get_price_history(request)

    print("=" * 60)
    print(f"Ticker      : {response.ticker}")
    print(f"Source      : {response.source}")
    print(f"Mode        : {response.mode}")
    print(f"Real-Time   : {response.realtime}")
    print(f"Last Bar    : {response.last_bar}")
    print(f"Rows        : {response.rows}")
    print("=" * 60)

    print(response.data.tail())
    