import numpy as np
import pandas as pd


def sma(series, period):
    return series.rolling(period).mean()


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(close, fast=12, slow=26, signal=9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)

    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def atr(df, period=14):
    high_low = df["High"] - df["Low"]
    high_close = np.abs(df["High"] - df["Close"].shift())
    low_close = np.abs(df["Low"] - df["Close"].shift())

    true_range = pd.concat(
        [high_low, high_close, low_close],
        axis=1
    ).max(axis=1)

    return true_range.rolling(period).mean()


def obv(df):
    values = [0]

    for i in range(1, len(df)):
        if df["Close"].iloc[i] > df["Close"].iloc[i - 1]:
            values.append(values[-1] + df["Volume"].iloc[i])
        elif df["Close"].iloc[i] < df["Close"].iloc[i - 1]:
            values.append(values[-1] - df["Volume"].iloc[i])
        else:
            values.append(values[-1])

    return pd.Series(values, index=df.index)


def roc(close, period=20):
    return ((close - close.shift(period)) / close.shift(period)) * 100


def relative_volume(volume, period=20):
    avg_volume = volume.rolling(period).mean()
    return volume / avg_volume


def distance_from_high(df):
    highest_high = df["High"].max()
    return ((df["Close"] - highest_high) / highest_high) * 100


def bollinger_bands(close, period=20, std_dev=2):
    middle = sma(close, period)
    std = close.rolling(period).std()

    upper = middle + std_dev * std
    lower = middle - std_dev * std
    width = ((upper - lower) / middle) * 100

    return upper, middle, lower, width


def vwap(df):
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cumulative_price_volume = (typical_price * df["Volume"]).cumsum()
    cumulative_volume = df["Volume"].cumsum()

    return cumulative_price_volume / cumulative_volume
    