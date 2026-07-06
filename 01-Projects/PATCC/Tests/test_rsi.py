"""
PATCC RSI Indicator Test
"""

from pathlib import Path
import sys

PATCC_ROOT = Path(__file__).resolve().parents[1]

if str(PATCC_ROOT) not in sys.path:
    sys.path.insert(0, str(PATCC_ROOT))

from Services.data_service import DataService
from Indicators.rsi import RSIIndicator


def main():
    print("=" * 60)
    print("PATCC RSI TEST")
    print("=" * 60)

    data_service = DataService()
    market_data = data_service.get_history("SPY", "6mo", "1d")

    rsi14 = RSIIndicator(period=14)
    rsi = rsi14.calculate(market_data)

    latest_rsi = float(rsi.iloc[-1].iloc[0])

    print(f"\nSymbol     : {market_data.symbol}")
    print(f"Provider   : {market_data.provider}")
    print(f"RSI Period : 14")
    print(f"Latest RSI : {latest_rsi:.2f}")

    if latest_rsi >= 70:
        signal = "Overbought"
    elif latest_rsi <= 30:
        signal = "Oversold"
    else:
        signal = "Neutral"

    print(f"Signal     : {signal}")

    print("\nLast 5 RSI Values")
    print("-----------------")
    print(rsi.tail())


if __name__ == "__main__":
    main()
    