import yfinance as yf
import pandas as pd
from datetime import datetime
from tabulate import tabulate

SYMBOLS = {
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
    "DIA": "Dow Jones ETF",
    "IWM": "Russell 2000 ETF",
    "^VIX": "Volatility Index",
    "^TNX": "10Y Treasury Yield",
    "DX-Y.NYB": "US Dollar Index",
    "BTC-USD": "Bitcoin",
    "GLD": "Gold ETF",
    "SLV": "Silver ETF",
    "USO": "Oil ETF",
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
}

SECTORS = ["XLK", "XLF", "XLV", "XLE", "XLY", "XLP", "XLU"]

REPORT_PATH = r"C:\AI-Trading\01-Projects\PATCC\Reports\market_intelligence_report.txt"


def get_close_series(data):
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna()


def get_price_data(symbol):
    data = yf.download(
        symbol,
        period="3mo",
        interval="1d",
        progress=False,
        auto_adjust=True,
        threads=False,
    )

    if data.empty:
        return None

    close = get_close_series(data)

    if len(close) < 50:
        return None

    latest = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    change_pct = ((latest - prev) / prev) * 100
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1])

    if latest > ma20 > ma50:
        trend = "Bullish"
        trend_score = 2
    elif latest < ma20 < ma50:
        trend = "Bearish"
        trend_score = -2
    else:
        trend = "Mixed"
        trend_score = 0

    strength = ((latest - ma50) / ma50) * 100

    return {
        "Symbol": symbol,
        "Name": SYMBOLS.get(symbol, symbol),
        "Price": round(latest, 2),
        "1D %": round(change_pct, 2),
        "20MA": round(ma20, 2),
        "50MA": round(ma50, 2),
        "Trend": trend,
        "Strength %": round(strength, 2),
        "Trend Score": trend_score,
    }


def get_item(results, symbol):
    return next((r for r in results if r["Symbol"] == symbol), None)


def classify_market(results):
    score = 50

    for symbol in ["SPY", "QQQ", "IWM"]:
        item = get_item(results, symbol)
        if not item:
            continue

        if item["Trend"] == "Bullish":
            score += 12
        elif item["Trend"] == "Mixed":
            score += 4
        else:
            score -= 10

    vix = get_item(results, "^VIX")
    dxy = get_item(results, "DX-Y.NYB")
    tnx = get_item(results, "^TNX")

    if vix:
        if vix["1D %"] < 0:
            score += 5
        elif vix["1D %"] > 3:
            score -= 10

    if dxy and dxy["1D %"] > 0.3:
        score -= 5

    if tnx and tnx["1D %"] > 1:
        score -= 5

    score = max(0, min(100, score))

    if score >= 75:
        regime = "RISK-ON / Bullish conditions"
    elif score >= 60:
        regime = "NEUTRAL-BULLISH / Selective long setups"
    elif score >= 45:
        regime = "NEUTRAL / Wait for confirmation"
    else:
        regime = "RISK-OFF / Defensive conditions"

    return score, regime


def rank_sectors(results):
    sector_rows = [r for r in results if r["Symbol"] in SECTORS]
    return sorted(sector_rows, key=lambda x: x["Strength %"], reverse=True)


def build_brief(results, score, regime):
    sector_rankings = rank_sectors(results)
    leaders = sector_rankings[:3]
    laggards = sector_rankings[-3:]

    lines = []
    lines.append("Professional AI Trading Command Center")
    lines.append("Morning Market Intelligence Brief")
    lines.append("=" * 60)
    lines.append(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"Market Score: {score}/100")
    lines.append(f"Market Regime: {regime}")
    lines.append("")

    lines.append("Major Index Trend")
    for symbol in ["SPY", "QQQ", "DIA", "IWM"]:
        item = get_item(results, symbol)
        if item:
            lines.append(f"{symbol}: {item['Trend']} | 1D: {item['1D %']}% | Strength: {item['Strength %']}%")

    lines.append("")
    lines.append("Macro Conditions")
    for symbol in ["^VIX", "^TNX", "DX-Y.NYB", "BTC-USD", "GLD", "USO"]:
        item = get_item(results, symbol)
        if item:
            lines.append(f"{symbol}: {item['Trend']} | 1D: {item['1D %']}%")

    lines.append("")
    lines.append("Sector Leaders")
    for item in leaders:
        lines.append(f"{item['Symbol']} - {item['Name']} | Strength: {item['Strength %']}% | Trend: {item['Trend']}")

    lines.append("")
    lines.append("Sector Laggards")
    for item in laggards:
        lines.append(f"{item['Symbol']} - {item['Name']} | Strength: {item['Strength %']}% | Trend: {item['Trend']}")

    lines.append("")
    lines.append("Trading Desk Interpretation")
    if score >= 75:
        lines.append("Risk appetite is strong. Prefer long setups in leading sectors, but avoid chasing extended names.")
    elif score >= 60:
        lines.append("Conditions are constructive but selective. Focus on clean pullbacks and relative strength.")
    elif score >= 45:
        lines.append("Market is mixed. Reduce position size and wait for confirmation.")
    else:
        lines.append("Defensive environment. Prioritize capital preservation and avoid weak breakouts.")

    return "\n".join(lines)


def main():
    results = []

    print("\nFetching market data...")

    for symbol in SYMBOLS:
        try:
            row = get_price_data(symbol)
            if row:
                results.append(row)
            else:
                print(f"Warning: No usable data for {symbol}")
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    if not results:
        print("No market data available.")
        return

    df = pd.DataFrame(results)
    score, regime = classify_market(results)
    brief = build_brief(results, score, regime)

    print("\n" + brief)
    print("\nDetailed Market Table")
    print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(brief)
        f.write("\n\nDetailed Market Table\n")
        f.write(tabulate(df, headers="keys", tablefmt="grid", showindex=False))

    print(f"\nReport saved to:\n{REPORT_PATH}")


if __name__ == "__main__":
    main()
    