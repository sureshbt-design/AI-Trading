MARKET_ETFS = [
    "SPY", "QQQ", "DIA", "IWM"
]

SECTOR_ETFS = [
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLU"
]

MEGA_CAPS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"
]

SEMICONDUCTORS = [
    "NVDA", "AMD", "AVGO", "MU", "SMH", "SOXL"
]

CRYPTO_RELATED = [
    "MSTR", "COIN", "IBIT", "MARA", "RIOT"
]

AI_GROWTH = [
    "NVDA", "MSFT", "GOOGL", "META", "PLTR", "AMD", "AVGO"
]

DEFAULT_UNIVERSE = (
    MARKET_ETFS
    + SECTOR_ETFS
    + MEGA_CAPS
    + SEMICONDUCTORS
    + CRYPTO_RELATED
    + AI_GROWTH
)


def get_unique_symbols(symbols):
    return list(dict.fromkeys(symbols))


def get_default_universe():
    return get_unique_symbols(DEFAULT_UNIVERSE)


def get_universe_by_name(name):
    name = name.lower()

    universes = {
        "market": MARKET_ETFS,
        "sectors": SECTOR_ETFS,
        "mega_caps": MEGA_CAPS,
        "semiconductors": SEMICONDUCTORS,
        "crypto": CRYPTO_RELATED,
        "ai": AI_GROWTH,
        "default": get_default_universe(),
    }

    return get_unique_symbols(universes.get(name, get_default_universe()))
    