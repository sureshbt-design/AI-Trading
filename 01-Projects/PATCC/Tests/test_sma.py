"""
PATCC SMA Indicator Test
"""

from pathlib import Path
import sys

PATCC_ROOT = Path(__file__).resolve().parents[1]

if str(PATCC_ROOT) not in sys.path:
    sys.path.insert(0, str(PATCC_ROOT))

from Services.data_service import DataService
from Indicators.sma import SMAIndicator


def main():
    print("=" * 60)
    print("PATCC SMA TEST")
    print("=" * 60)

    data_service = DataService()

    market_data = data_service.get_history(
        symbol="SPY",
        period="6mo",
        interval="1d"
    )

    df = market_data.data

    sma20 = SMAIndicator(period=20)
    sma50 = SMAIndicator(period=50)

    sma20_values = sma20.calculate(market_data)
    sma50_values = sma50.calculate(market_data)

    latest_close = float(df["Close"].iloc[-1].iloc[0])
    latest_sma20 = float(sma20_values.iloc[-1].iloc[0])
    latest_sma50 = float(sma50_values.iloc[-1].iloc[0])

    print(f"\nSymbol       : {market_data.symbol}")
    print(f"Provider     : {market_data.provider}")
    print(f"Latest Close : {latest_close:.2f}")
    print(f"Latest SMA20 : {latest_sma20:.2f}")
    print(f"Latest SMA50 : {latest_sma50:.2f}")

    print("\nLast 5 SMA20 Values")
    print("-------------------")
    print(sma20_values.tail())


if __name__ == "__main__":
    main()
    