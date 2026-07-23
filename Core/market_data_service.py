"""
market_data_service.py

Single gateway for retrieving, normalizing, validating, and documenting
market data.

Configured market-data providers are attempted in priority order.
A failure from one provider does not stop retrieval; PATCC proceeds
to the next configured provider.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
from time import perf_counter
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

from Config.patcc_settings import DEFAULT_TIMEZONE
from Core.market_data_provider import ProviderRequest
from Core.provider_factory import ProviderFactory
from Core.timeframe_manager import TimeframeManager


logger = logging.getLogger(__name__)


@dataclass
class MarketDataResponse:
    """
    Validated market data plus operational retrieval metadata.

    Existing fields remain unchanged so current PATCC callers continue
    to operate normally.
    """

    ticker: str
    source: str
    mode: str
    realtime: bool
    last_bar: datetime
    rows: int
    data: pd.DataFrame

    # Operational metadata
    requested_at: datetime
    received_at: datetime
    retrieval_seconds: float
    requested_period: str
    requested_interval: str
    provider_attempt: int
    fallback_used: bool


@dataclass
class MarketDataRequest:
    """
    Request object for market-data retrieval.

    Timeframe may be specified either directly (5m, 1h, 1d, etc.)
    or by providing explicit period/interval values.
    """

    ticker: str
    timeframe: str = "1d"
    period: str | None = None
    interval: str | None = None
    auto_adjust: bool = True


class MarketDataService:
    """
    Retrieve and validate OHLCV market data through a provider-neutral gateway.

    Providers are attempted in configured priority order. A provider failure
    is recorded and the next provider is attempted automatically.
    """

    REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

    def __init__(
        self,
        provider=None,
        providers=None,
    ) -> None:
        """
        Initialize the market-data service.

        Parameters
        ----------
        provider:
            Optional single provider instance. Retained for backward
            compatibility and focused testing.

        providers:
            Optional ordered collection of provider instances.

        When neither argument is supplied, providers are created from
        Config/patcc_settings.py through ProviderFactory.
        """

        if provider is not None and providers is not None:
            raise ValueError(
                "Specify either 'provider' or 'providers', not both."
            )

        if provider is not None:
            self.providers = [provider]
        elif providers is not None:
            self.providers = list(providers)
        else:
            self.providers = ProviderFactory.create()

        if not self.providers:
            raise ValueError(
                "No market-data providers are configured."
            )

        try:
            self.local_timezone = ZoneInfo(DEFAULT_TIMEZONE)
        except Exception as exc:
            raise ValueError(
                f"Invalid DEFAULT_TIMEZONE configuration: "
                f"{DEFAULT_TIMEZONE}"
            ) from exc

    def get_price_history(
        self,
        request: MarketDataRequest,
    ) -> MarketDataResponse:
        """
        Retrieve validated OHLCV history.

        Each configured provider is attempted until one returns valid data.
        Failed providers do not interrupt the provider chain.
        """

        ticker = request.ticker.upper().strip()

        if not ticker:
            raise ValueError("Ticker cannot be empty.")

        config = TimeframeManager.get_config(request.timeframe)

        period = request.period or config.period
        interval = request.interval or config.interval

        provider_request = ProviderRequest(
            ticker=ticker,
            period=period,
            interval=interval,
            auto_adjust=request.auto_adjust,
        )

        failures: list[str] = []

        for attempt_number, provider in enumerate(
            self.providers,
            start=1,
        ):
            provider_name = self._provider_name(provider)

            requested_at = datetime.now(self.local_timezone)
            retrieval_start = perf_counter()

            try:
                provider_response = provider.get_price_history(
                    provider_request
                )

                received_at = datetime.now(self.local_timezone)
                retrieval_seconds = perf_counter() - retrieval_start

                cleaned = self._validate(
                    ticker=ticker,
                    data=provider_response.data,
                )

                fallback_used = attempt_number > 1

                if fallback_used:
                    logger.warning(
                        "%s market data retrieved through fallback "
                        "provider %s after earlier provider failure.",
                        ticker,
                        provider_response.source,
                    )

                return MarketDataResponse(
                    ticker=ticker,
                    source=provider_response.source,
                    mode=provider_response.mode,
                    realtime=provider_response.realtime,
                    last_bar=cleaned.index[-1].to_pydatetime(),
                    rows=len(cleaned),
                    data=cleaned,
                    requested_at=requested_at,
                    received_at=received_at,
                    retrieval_seconds=round(
                        retrieval_seconds,
                        3,
                    ),
                    requested_period=period,
                    requested_interval=interval,
                    provider_attempt=attempt_number,
                    fallback_used=fallback_used,
                )

            except Exception as exc:
                retrieval_seconds = perf_counter() - retrieval_start

                failure_message = (
                    f"{provider_name}: "
                    f"{type(exc).__name__}: {exc}"
                )
                failures.append(failure_message)

                logger.warning(
                    "Market-data provider %s failed for %s after "
                    "%.3f seconds. PATCC will attempt the next "
                    "configured provider. Reason: %s",
                    provider_name,
                    ticker,
                    retrieval_seconds,
                    exc,
                )

        failure_summary = " | ".join(failures)

        raise RuntimeError(
            f"All configured market-data providers failed for "
            f"{ticker}. Attempts: {failure_summary}"
        )

    @staticmethod
    def _provider_name(provider) -> str:
        """
        Return a readable provider name for operational messages.
        """

        return provider.__class__.__name__

    def _validate(
        self,
        ticker: str,
        data: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Validate and normalize one provider's OHLCV response.
        """

        if data is None or data.empty:
            raise ValueError(
                f"No market data returned for ticker: {ticker}"
            )

        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = data.columns.get_level_values(0)

        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in data.columns
        ]

        if missing:
            raise ValueError(
                f"{ticker} missing required columns: {missing}"
            )

        cleaned = data[self.REQUIRED_COLUMNS].dropna().copy()

        if cleaned.empty:
            raise ValueError(
                f"{ticker} has no valid OHLCV rows after cleanup"
            )

        if not isinstance(cleaned.index, pd.DatetimeIndex):
            try:
                cleaned.index = pd.to_datetime(cleaned.index)
            except Exception as exc:
                raise ValueError(
                    f"{ticker} market-data index cannot be converted "
                    f"to datetime: {exc}"
                ) from exc

        cleaned = cleaned.sort_index()

        return cleaned


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    service = MarketDataService()

    request = MarketDataRequest(
        ticker="TQQQ",
        period="3mo",
        interval="1d",
    )

    response = service.get_price_history(request)

    print("=" * 72)
    print("PATCC MARKET DATA RESPONSE")
    print("=" * 72)
    print(f"Ticker              : {response.ticker}")
    print(f"Source              : {response.source}")
    print(f"Mode                : {response.mode}")
    print(f"Real-Time           : {response.realtime}")
    print(f"Requested Period    : {response.requested_period}")
    print(f"Requested Interval  : {response.requested_interval}")
    print(f"Requested At        : {response.requested_at:%Y-%m-%d %I:%M:%S %p %Z}")
    print(f"Received At         : {response.received_at:%Y-%m-%d %I:%M:%S %p %Z}")
    print(f"Retrieval Time      : {response.retrieval_seconds:.3f} seconds")
    print(f"Provider Attempt    : {response.provider_attempt}")
    print(f"Fallback Used       : {response.fallback_used}")
    print(f"Last Available Bar  : {response.last_bar}")
    print(f"Rows                : {response.rows}")
    print("=" * 72)

    print(response.data.tail())
    