"""
patcc_settings.py

Global runtime configuration for PATCC.

This module centralizes system-wide runtime behavior so that
market data providers, reporting engines, and future execution
components all use one consistent configuration source.
"""

# ============================================================
# Market Data Provider Configuration
# ============================================================

# Providers are attempted in order.
# The first successful provider is used.
#
# Future example:
#
# MARKET_DATA_PROVIDERS = (
#     "SCHWAB",
#     "IBKR",
#     "YAHOO",
#     "CACHE",
# )
#

MARKET_DATA_PROVIDERS = (
    "YAHOO",
)

ALLOW_PROVIDER_FALLBACK = True

FAIL_IF_ALL_PROVIDERS_FAIL = False


# ============================================================
# Market Session
# ============================================================

ENABLE_PREMARKET = True

ENABLE_AFTER_HOURS = True


# ============================================================
# Reporting
# ============================================================

DEFAULT_TIMEZONE = "US/Eastern"

MORNING_REPORT_TIME = "07:30"

EVENING_REPORT_TIME = "20:00"
