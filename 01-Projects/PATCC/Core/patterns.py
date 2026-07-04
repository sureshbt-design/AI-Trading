def is_ema_stack_bullish(row):
    return row["EMA20"] > row["EMA50"] > row["EMA200"]


def is_ema_stack_bearish(row):
    return row["EMA20"] < row["EMA50"] < row["EMA200"]


def is_price_above_key_emas(row):
    return (
        row["Close"] > row["EMA20"]
        and row["Close"] > row["EMA50"]
        and row["Close"] > row["EMA200"]
    )


def is_20_day_breakout(df):
    if len(df) < 21:
        return False

    latest_close = df["Close"].iloc[-1]
    prior_20_high = df["High"].iloc[-21:-1].max()

    return latest_close > prior_20_high


def is_50_day_breakout(df):
    if len(df) < 51:
        return False

    latest_close = df["Close"].iloc[-1]
    prior_50_high = df["High"].iloc[-51:-1].max()

    return latest_close > prior_50_high


def is_52_week_breakout(df):
    if len(df) < 200:
        return False

    latest_close = df["Close"].iloc[-1]
    prior_high = df["High"].iloc[:-1].max()

    return latest_close > prior_high


def is_volume_spike(row, threshold=1.5):
    return row["REL_VOL"] >= threshold


def is_high_relative_volume(row):
    return row["REL_VOL"] >= 2.0


def is_rsi_bullish(row):
    return 50 <= row["RSI"] <= 70


def is_rsi_overbought(row):
    return row["RSI"] > 70


def is_macd_bullish(row):
    return row["MACD"] > row["MACD_SIGNAL"]


def is_macd_bearish(row):
    return row["MACD"] < row["MACD_SIGNAL"]


def is_pullback_to_ema20(row, tolerance=0.02):
    lower = row["EMA20"] * (1 - tolerance)
    upper = row["EMA20"] * (1 + tolerance)

    return lower <= row["Close"] <= upper


def is_pullback_to_ema50(row, tolerance=0.025):
    lower = row["EMA50"] * (1 - tolerance)
    upper = row["EMA50"] * (1 + tolerance)

    return lower <= row["Close"] <= upper


def is_near_52_week_high(row, threshold=-5):
    return row["DIST_52W_HIGH"] >= threshold


def is_vcp_candidate(df):
    if len(df) < 60:
        return False

    recent = df.tail(60)
    first_range = (recent["High"].iloc[:20].max() - recent["Low"].iloc[:20].min())
    second_range = (recent["High"].iloc[20:40].max() - recent["Low"].iloc[20:40].min())
    third_range = (recent["High"].iloc[40:60].max() - recent["Low"].iloc[40:60].min())

    return first_range > second_range > third_range


def detect_patterns(df):
    latest = df.iloc[-1]

    patterns = []

    if is_ema_stack_bullish(latest):
        patterns.append("Bullish EMA Stack")

    if is_ema_stack_bearish(latest):
        patterns.append("Bearish EMA Stack")

    if is_price_above_key_emas(latest):
        patterns.append("Price Above Key EMAs")

    if is_20_day_breakout(df):
        patterns.append("20-Day Breakout")

    if is_50_day_breakout(df):
        patterns.append("50-Day Breakout")

    if is_52_week_breakout(df):
        patterns.append("52-Week Breakout")

    if is_volume_spike(latest):
        patterns.append("Volume Spike")

    if is_high_relative_volume(latest):
        patterns.append("High Relative Volume")

    if is_rsi_bullish(latest):
        patterns.append("Bullish RSI")

    if is_rsi_overbought(latest):
        patterns.append("Overbought RSI")

    if is_macd_bullish(latest):
        patterns.append("MACD Bullish")

    if is_macd_bearish(latest):
        patterns.append("MACD Bearish")

    if is_pullback_to_ema20(latest):
        patterns.append("EMA20 Pullback")

    if is_pullback_to_ema50(latest):
        patterns.append("EMA50 Pullback")

    if is_near_52_week_high(latest):
        patterns.append("Near 52-Week High")

    if is_vcp_candidate(df):
        patterns.append("VCP Candidate")

    return patterns
    