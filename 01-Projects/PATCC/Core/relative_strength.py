import pandas as pd


def calculate_relative_strength(symbol_df, benchmark_df, period=20):
    if len(symbol_df) < period + 1 or len(benchmark_df) < period + 1:
        return None

    symbol_return = (
        symbol_df["Close"].iloc[-1] / symbol_df["Close"].iloc[-period] - 1
    ) * 100

    benchmark_return = (
        benchmark_df["Close"].iloc[-1] / benchmark_df["Close"].iloc[-period] - 1
    ) * 100

    relative_strength = symbol_return - benchmark_return

    return round(relative_strength, 2)


def calculate_relative_strength_score(relative_strength):
    if relative_strength is None:
        return 0

    if relative_strength >= 10:
        return 100
    if relative_strength >= 5:
        return 90
    if relative_strength >= 2:
        return 80
    if relative_strength >= 0:
        return 70
    if relative_strength >= -2:
        return 50
    if relative_strength >= -5:
        return 30

    return 10


def calculate_rs_rank(results, rs_key="RS vs SPY"):
    sorted_results = sorted(
        results,
        key=lambda x: x.get(rs_key, -999),
        reverse=True
    )

    for rank, item in enumerate(sorted_results, start=1):
        item["RS Rank"] = rank

    return sorted_results


def relative_strength_label(score):
    if score >= 90:
        return "Elite"
    if score >= 80:
        return "Strong"
    if score >= 70:
        return "Positive"
    if score >= 50:
        return "Neutral"
    if score >= 30:
        return "Weak"

    return "Very Weak"
    