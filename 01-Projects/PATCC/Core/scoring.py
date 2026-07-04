def grade_score(score):
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "Avoid"


def calculate_component_scores(row):
    trend_score = 0
    momentum_score = 0
    volume_score = 0
    volatility_score = 0
    strength_score = 0

    price = row["Close"]
    atr_pct = (row["ATR"] / row["Close"]) * 100 if row["Close"] > 0 else 0
    rel_vol = row["REL_VOL"]

    if price > row["EMA20"]:
        trend_score += 20
    if price > row["EMA50"]:
        trend_score += 25
    if price > row["EMA200"]:
        trend_score += 30
    if row["EMA20"] > row["EMA50"]:
        trend_score += 15
    if row["EMA50"] > row["EMA200"]:
        trend_score += 10

    if 50 <= row["RSI"] <= 70:
        momentum_score += 35
    elif 45 <= row["RSI"] < 50:
        momentum_score += 20
    elif row["RSI"] > 70:
        momentum_score += 20

    if row["MACD"] > row["MACD_SIGNAL"]:
        momentum_score += 35

    if row["ROC20"] > 0:
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

    if row["DIST_52W_HIGH"] >= -5:
        strength_score = 100
    elif row["DIST_52W_HIGH"] >= -10:
        strength_score = 80
    elif row["DIST_52W_HIGH"] >= -20:
        strength_score = 60
    else:
        strength_score = 30

    total_score = round(
        trend_score * 0.35
        + momentum_score * 0.25
        + volume_score * 0.15
        + volatility_score * 0.10
        + strength_score * 0.15
    )

    return {
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "volume_score": volume_score,
        "volatility_score": volatility_score,
        "strength_score": strength_score,
        "total_score": total_score,
        "grade": grade_score(total_score),
    }
    