"""
PATCC ATR Indicator Test
"""

from pathlib import Path
import sys

PATCC_ROOT = Path(__file__).resolve().parents[1]

if str(PATCC_ROOT) not in sys.path:
    sys.path.insert(0, str(PATCC_ROOT))

from Services.data_service import DataService
from Indicators.atr import ATRIndicator


def main():
    print("=" * 60)
    print("PATCC ATR TEST")
    print("=" * 60)

    data_service = DataService()
    market_data = data_service.get_history("SPY", "6mo", "1d")

    atr14 = ATRIndicator(period=14)
    atr = atr14.calculate(market_data)

    latest_atr = float(atr.iloc[-1])

    print(f"\nSymbol     : {market_data.symbol}")
    print(f"Provider   : {market_data.provider}")
    print(f"ATR Period : 14")
    print(f"Latest ATR : {latest_atr:.2f}")

    print("\nLast 5 ATR Values")
    print("-----------------")
    print(atr.tail())


if __name__ == "__main__":
    main()
