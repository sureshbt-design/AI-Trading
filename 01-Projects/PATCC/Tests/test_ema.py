"""
PATCC EMA Indicator Test
"""
from pathlib import Path
import sys

PATCC_ROOT = Path(__file__).resolve().parents[1]

if str(PATCC_ROOT) not in sys.path:
    sys.path.insert(0, str(PATCC_ROOT))

from Services.data_service import DataService
from Indicators.ema import EMAIndicator


def main():

    print("=" * 60)
    print("PATCC EMA TEST")
    print("=" * 60)

    data_service = DataService()

    df = data_service.get_history(
        symbol="SPY",
        period="6mo",
        interval="1d"
    )

    ema20 = EMAIndicator(period=20)

    ema = ema20.calculate(df)

    latest_close = float(df["Close"].iloc[-1].iloc[0])
    latest_ema = float(ema.iloc[-1].iloc[0])

    print(f"\nLatest Close : {latest_close:.2f}")
    print(f"Latest EMA20 : {latest_ema:.2f}")


    print("\nLast 5 EMA Values")
    print("-----------------")
    print(ema.tail())


if __name__ == "__main__":
    main()
