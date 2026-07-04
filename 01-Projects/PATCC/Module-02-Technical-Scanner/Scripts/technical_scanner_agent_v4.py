import os
import sys
from datetime import datetime

import pandas as pd
import yfinance as yf
from tabulate import tabulate

sys.path.append(r"C:\AI-Trading\01-Projects\PATCC")

from Core.ranking import top_candidates
from Core.universe import get_default_universe
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
from Core.scoring import calculate_component_scores
from Core.relative_strength import (
    calculate_relative_strength,
    calculate_relative_strength_score,
    calculate_rs_rank,
    relative_strength_label,
)


SYMBOLS = get_default_universe()


BASE_DIR = r"C:\AI-Trading\01-Projects\PATCC\Module-02-Technical-Scanner"
REPORT_DIR = os.path.join(BASE_DIR, "Reports")
REPORT_FILE = os.path.join(REPORT_DIR, "technical_scanner_report_v4.txt")


def get_trend(price, ema20, ema50, ema200):
    if price > ema20 > ema50 > ema200:
        return "Strong Bullish"
    if price > ema50 and price > ema200:
        return "Bullish"
    if price < ema20 and ema20 < ema50:
        return "Bearish"
    return "Mixed"


def analyze_symbol(symbol, benchmark_df):
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

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = latest["Close"]
    daily_change_pct = ((latest["Close"] - previous["Close"]) / previous["Close"]) * 100
    rel_vol = latest["REL_VOL"]
    atr_pct = (latest["ATR"] / latest["Close"]) * 100 if latest["Close"] > 0 else 0

    scores = calculate_component_scores(latest)
     
    rs_vs_spy = calculate_relative_strength(df, benchmark_df, period=20)
    rs_score = calculate_relative_strength_score(rs_vs_spy)
    rs_label = relative_strength_label(rs_score)



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
        "Trend Score": round(scores["trend_score"], 1),
        "Momentum Score": round(scores["momentum_score"], 1),
        "Volume Score": round(scores["volume_score"], 1),
        "Strength Score": round(scores["strength_score"], 1),
        "Patterns": ", ".join(patterns[:3]),
        "RS vs SPY": rs_vs_spy,
        "RS Score": rs_score,
        "RS Label": rs_label,
        "Score": scores["total_score"],
        "Grade": scores["grade"],
    }


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    # Download benchmark once
    benchmark_df = yf.download(
    "SPY",
    period="1y",
    interval="1d",
    progress=False,
    auto_adjust=True,
)

    if isinstance(benchmark_df.columns, pd.MultiIndex):
       benchmark_df.columns = benchmark_df.columns.get_level_values(0)
  
    results = []

    for symbol in SYMBOLS:
        try:
            result = analyze_symbol(symbol, benchmark_df)
            if result:
                results.append(result)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")

    
    ranked_df = top_candidates(results, top_n=len(results))
    results = ranked_df.to_dict("records")


    table = tabulate(results, headers="keys", tablefmt="grid")

    report = f"""
PATCC MODULE 2 - TECHNICAL SCANNER AGENT V3
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{table}
"""

    print(report)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"\nReport saved to:\n{REPORT_FILE}")


if __name__ == "__main__":
    main()
    