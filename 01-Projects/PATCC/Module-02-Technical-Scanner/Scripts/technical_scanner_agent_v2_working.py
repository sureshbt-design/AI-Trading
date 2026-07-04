import os
import sys
from datetime import datetime

import pandas as pd
import yfinance as yf
from tabulate import tabulate

sys.path.append(r"C:\AI-Trading\01-Projects\PATCC")

from Core.indicators import (
    ema,
    rsi,
    macd,
    atr,
    obv,
    roc,
    relative_volume,
    distance_from_high,
)
from Core.patterns import detect_patterns


SYMBOLS = [
    "SPY", "QQQ", "DIA", "IWM",
    "AAPL", "MSFT", "NVDA", "AMD", "AVGO",
    "META", "AMZN", "TSLA", "PLTR", "MSTR", "COIN",
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLU"
]

BASE_DIR = r"C:\AI-Trading\01-Projects\PATCC\Module-02-Technical-Scanner"
REPORT_DIR = os.path.join(BASE_DIR, "Reports")
REPORT_FILE = os.path.join(REPORT_DIR, "technical_scanner_report.txt")

def get_trend(price, ema20, ema50, ema200):
    if price > ema20 > ema50 > ema200:
        return "Strong Bullish"
    if price > ema50 and price > ema200:
        return "Bullish"
    if price < ema20 and ema20 < ema50:
        return "Bearish"
    return "Mixed"


def analyze_symbol(symbol):
    df = yf.download(
        symbol,
        period="1y",
        interval="1d",
        progress=False,
        auto_adjust=True
    )

   


    if df.empty or len(df) < 220:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df["EMA20"] = ema(df["Close"], 20)
    df["EMA50"] = ema(df["Close"], 50)
    df["EMA200"] = ema(df["Close"], 200)

    df["RSI"] = rsi(df["Close"])
    df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = macd(df["Close"])
    df["ATR"] = atr(df)
    df["OBV"] = obv(df)
    df["ROC20"] = roc(df["Close"], 20)
    df["REL_VOL"] = relative_volume(df["Volume"], 20)
    df["DIST_52W_HIGH"] = distance_from_high(df)

    patterns = detect_patterns(df)
    from Core.patterns import detect_patterns
    from Core.scoring import calculate_component_scores


    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = latest["Close"]
    daily_change_pct = ((latest["Close"] - previous["Close"]) / previous["Close"]) * 100
    rel_vol = latest["REL_VOL"]
    atr_pct = (latest["ATR"] / latest["Close"]) * 100 if latest["Close"] > 0 else 0

    trend_score = 0
    momentum_score = 0
    volume_score = 0
    volatility_score = 0
    strength_score = 0

    if price > latest["EMA20"]:
        trend_score += 20
    if price > latest["EMA50"]:
        trend_score += 25
    if price > latest["EMA200"]:
        trend_score += 30
    if latest["EMA20"] > latest["EMA50"]:
        trend_score += 15
    if latest["EMA50"] > latest["EMA200"]:
        trend_score += 10

    if 50 <= latest["RSI"] <= 70:
        momentum_score += 35
    elif 45 <= latest["RSI"] < 50:
        momentum_score += 20
    elif latest["RSI"] > 70:
        momentum_score += 20

    if latest["MACD"] > latest["MACD_SIGNAL"]:
        momentum_score += 35

    if latest["ROC20"] > 0:
        momentum_score += 30

    if rel_vol >= 2:
        volume_score = 100
    elif rel_vol >= 1.5:
        volume_score = 80
    elif rel_vol >= 1:
        volume_score = 60
    else:
        volume_score = 30

    if 1 <= atr_pct <= 4:
        volatility_score = 100
    elif 4 < atr_pct <= 7:
        volatility_score = 70
    elif atr_pct < 1:
        volatility_score = 50
    else:
        volatility_score = 35

    if latest["DIST_52W_HIGH"] >= -5:
        strength_score = 100
    elif latest["DIST_52W_HIGH"] >= -10:
        strength_score = 80
    elif latest["DIST_52W_HIGH"] >= -20:
        strength_score = 60
    else:
        strength_score = 30

    score = round(
        trend_score * 0.35
        + momentum_score * 0.25
        + volume_score * 0.15
        + volatility_score * 0.10
        + strength_score * 0.15
    )

    trend = get_trend(
        price,
        latest["EMA20"],
        latest["EMA50"],
        latest["EMA200"]
    )

    return {
        "Symbol": symbol,
        "Price": round(price, 2),
        "Daily %": round(daily_change_pct, 2),
        "RSI": round(latest["RSI"], 2),
        "Rel Vol": round(rel_vol, 2),
        "ATR %": round(atr_pct, 2),
        "ROC20": round(latest["ROC20"], 2),
        "52W Dist %": round(latest["DIST_52W_HIGH"], 2),
        "Trend": trend,
        "Trend Score": round(trend_score, 1),
        "Momentum Score": round(momentum_score, 1),
        "Volume Score": round(volume_score, 1),
        "Patterns": ", ".join(patterns[:3]),
        "Score": score,
        "Grade": grade_score(score),
    }


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)

    results = []

    for symbol in SYMBOLS:
        try:
            result = analyze_symbol(symbol)
            if result:
                results.append(result)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")

    results = sorted(results, key=lambda x: x["Score"], reverse=True)

    table = tabulate(results, headers="keys", tablefmt="grid")

    report = f"""
PATCC MODULE 2 - TECHNICAL SCANNER AGENT V2.1
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{table}
"""

    print(report)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"\nReport saved to:\n{REPORT_FILE}")


if __name__ == "__main__":
    main()
    