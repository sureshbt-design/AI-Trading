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
    elif latest < ma20 < ma50:
        trend = "Bearish"
    else:
        trend = "Mixed"

    return {
        "Symbol": symbol,
        "Name": SYMBOLS.get(symbol, symbol),
        "Price": round(latest, 2),
        "1D %": round(change_pct, 2),
        "20MA": round(ma20, 2),
        "50MA": round(ma50, 2),
        "Trend": trend,
    }


def classify_market(results):
    score = 0

    def find(symbol):
        return next((r for r in results if r["Symbol"] == symbol), None)

    spy = find("SPY")
    qqq = find("QQQ")
    iwm = find("IWM")
    vix = find("^VIX")
    dxy = find("DX-Y.NYB")
    tnx = find("^TNX")

    for item in [spy, qqq, iwm]:
        if item and item["Trend"] == "Bullish":
            score += 2
        elif item and item["Trend"] == "Mixed":
            score += 1
        else:
            score -= 1

    if vix:
        if vix["1D %"] < 0:
            score += 1
        elif vix["1D %"] > 3:
            score -= 2

    if dxy and dxy["1D %"] > 0.3:
        score -= 1

    if tnx and tnx["1D %"] > 1:
        score -= 1

    if score >= 5:
        return "RISK-ON / Bullish conditions"
    elif score >= 2:
        return "NEUTRAL-BULLISH / Selective long setups"
    elif score >= 0:
        return "NEUTRAL / Wait for confirmation"
    else:
        return "RISK-OFF / Defensive conditions"


def main():
    print("\nProfessional AI Trading Command Center")
    print("Market Intelligence Agent")
    print("=" * 60)
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []

    for symbol in SYMBOLS:
        try:
            row = get_price_data(symbol)
            if row:
                results.append(row)
            else:
                print(f"Warning: No usable data for {symbol}")
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    df = pd.DataFrame(results)

    if df.empty:
        print("No market data available.")
        return

    table = tabulate(df, headers="keys", tablefmt="grid", showindex=False)
    regime = classify_market(results)

    print(table)
    print("\nMarket Regime:")
    print(regime)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("Professional AI Trading Command Center\n")
        f.write("Market Intelligence Agent\n")
        f.write("=" * 60 + "\n")
        f.write(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(table)
        f.write("\n\nMarket Regime:\n")
        f.write(regime)

    print(f"\nReport saved to:\n{REPORT_PATH}")


if __name__ == "__main__":
    main()
    