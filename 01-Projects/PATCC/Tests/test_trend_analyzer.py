"""
PATCC Trend Analyzer Test
"""

from pathlib import Path
import sys

PATCC_ROOT = Path(__file__).resolve().parents[1]

if str(PATCC_ROOT) not in sys.path:
    sys.path.insert(0, str(PATCC_ROOT))

from Services.data_service import DataService
from Indicators.ema import EMAIndicator
from Indicators.sma import SMAIndicator
from Core.trend_analyzer import TrendAnalyzer


def main():
    print("=" * 60)
    print("PATCC TREND ANALYZER TEST")
    print("=" * 60)

    data_service = DataService()
    market_data = data_service.get_history("SPY", "6mo", "1d")

    df = market_data.data

    ema20 = EMAIndicator(20).calculate(market_data)
    sma20 = SMAIndicator(20).calculate(market_data)
    sma50 = SMAIndicator(50).calculate(market_data)

    price = float(df["Close"].iloc[-1].iloc[0])
    ema20_value = float(ema20.iloc[-1].iloc[0])
    sma20_value = float(sma20.iloc[-1].iloc[0])
    sma50_value = float(sma50.iloc[-1].iloc[0])

    analyzer = TrendAnalyzer()
    signal = analyzer.analyze(
        price=price,
        ema20=ema20_value,
        sma20=sma20_value,
        sma50=sma50_value,
    )

    print(f"\nSymbol    : {market_data.symbol}")
    print(f"Price     : {price:.2f}")
    print(f"EMA20     : {ema20_value:.2f}")
    print(f"SMA20     : {sma20_value:.2f}")
    print(f"SMA50     : {sma50_value:.2f}")
    print(f"Direction : {signal.direction}")
    print(f"Strength  : {signal.strength}")
    print(f"Score     : {signal.score}")

    print("\nReasons")
    print("-------")
    for reason in signal.reasons:
        print(f"- {reason}")


if __name__ == "__main__":
    main()
    