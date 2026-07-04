from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PATCC_ROOT = PROJECT_ROOT / "01-Projects" / "PATCC"

MARKET_INDEXES = ["SPY", "QQQ", "DIA", "IWM"]
RISK_INDEXES = ["VIX", "DXY", "TNX", "BTC-USD"]

DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMD", "AVGO",
    "META", "AMZN", "TSLA", "PLTR", "MSTR",
    "COIN", "NFLX", "GOOGL", "MU",
    "SPY", "QQQ", "SMH", "SOXL", "TQQQ",
    "IBIT", "XLK", "XLF", "XLE"
]

LOOKBACK_DAYS = 180
MIN_AVG_VOLUME = 1_000_000

EMA_SHORT = 20
EMA_MEDIUM = 50
EMA_LONG = 200

RSI_PERIOD = 14
ATR_PERIOD = 14
VOLUME_LOOKBACK = 20

MIN_SCORE_TO_REPORT = 60
TOP_RESULTS_LIMIT = 20

DATA_DIR = PATCC_ROOT / "Data"
REPORTS_DIR = PATCC_ROOT / "Reports"
LOGS_DIR = PATCC_ROOT / "Logs"

WATCHLIST_DIR = DATA_DIR / "watchlists"
CACHE_DIR = DATA_DIR / "cache"
HISTORICAL_DIR = DATA_DIR / "historical"

DAILY_REPORT_DIR = REPORTS_DIR / "Daily"
WEEKLY_REPORT_DIR = REPORTS_DIR / "Weekly"
ARCHIVE_REPORT_DIR = REPORTS_DIR / "Archive"


def create_required_directories():
    for directory in [
        DATA_DIR,
        REPORTS_DIR,
        LOGS_DIR,
        WATCHLIST_DIR,
        CACHE_DIR,
        HISTORICAL_DIR,
        DAILY_REPORT_DIR,
        WEEKLY_REPORT_DIR,
        ARCHIVE_REPORT_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    create_required_directories()
    print("PATCC settings loaded successfully.")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"PATCC root: {PATCC_ROOT}")
