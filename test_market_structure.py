import pandas as pd
from Core.market_structure_engine import MarketStructureEngine


data = {
    "High":  [10, 12, 11, 14, 13, 16, 15, 18, 17, 20],
    "Low":   [8,  9,  8.5, 10, 9.5, 12, 11.5, 14, 13.5, 16],
    "Close": [9, 11, 10, 13, 12, 15, 14, 17, 16, 21],
}

df = pd.DataFrame(data)

engine = MarketStructureEngine(lookback=1)
result = engine.analyze(df)

print("Trend:", result.trend)
print("Latest Structure:", result.latest_structure)
print("Latest Event:", result.latest_event)
print("Confidence:", result.confidence)
print("Swing Highs:", [(s.index, s.price) for s in result.swing_highs])
print("Swing Lows:", [(s.index, s.price) for s in result.swing_lows])
