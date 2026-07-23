"""
provider_factory.py

Creates market data providers based on PATCC configuration.
"""

from Config.patcc_settings import MARKET_DATA_PROVIDERS

from Core.providers.yahoo_provider import YahooMarketDataProvider


class ProviderFactory:
    """
    Creates provider instances in configured priority order.
    """

    @staticmethod
    def create():
        providers = []

        for provider_name in MARKET_DATA_PROVIDERS:

            name = provider_name.upper()

            if name == "YAHOO":
                providers.append(YahooMarketDataProvider())

            else:
                raise ValueError(
                    f"Unsupported market data provider: {provider_name}"
                )

        return providers
        