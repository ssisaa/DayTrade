
def classify_regime(df_daily, df_4h=None):
    """
    Returns one of: STRONG_BULL, BULL, RANGE, BEAR, STRONG_BEAR, CHAOS
    """
    if df_daily is None or len(df_daily) < 55:
        return "UNKNOWN"

    price = df_daily['close'].iloc[-1]
    ema20 = df_daily['ema20'].iloc[-1]
    ema50 = df_daily['ema50'].iloc[-1]
    atr = df_daily['atr'].iloc[-1]
    atr_ma = df_daily['atr'].rolling(40).mean().iloc[-1]

    # Chaos filter (too much volatility)
    if atr > atr_ma * 1.9:
        return "CHAOS"

    # Trend strength
    if price > ema20 > ema50:
        # Check if it's a strong trend
        if (price - ema50) / ema50 > 0.04:
            return "STRONG_BULL"
        return "BULL"

    elif price < ema20 < ema50:
        if (ema50 - price) / ema50 > 0.04:
            return "STRONG_BEAR"
        return "BEAR"

    else:
        return "RANGE"