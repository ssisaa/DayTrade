from utils.helpers import calculate_atr, calculate_rsi
import pandas as pd


def add_indicators(df):
    df = df.copy()
    df['ema20'] = df['close'].ewm(span=20).mean()
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['rsi'] = calculate_rsi(df['close'])
    df['atr'] = calculate_atr(df)
    df['volume_ma'] = df['volume'].rolling(20).mean()
    return df
