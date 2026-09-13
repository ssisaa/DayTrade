def classify_regime(df_daily, df_4h=None):
    """
    Returns one of: STRONG_BULL, BULL, RANGE, BEAR, STRONG_BEAR, CHAOS
    More balanced for both LONG and SHORT.
    """
    if df_daily is None or len(df_daily) < 55:
        return "UNKNOWN"

    price = df_daily['close'].iloc[-1]
    ema20 = df_daily['ema20'].iloc[-1]
    ema50 = df_daily['ema50'].iloc[-1]
    atr = df_daily['atr'].iloc[-1]
    atr_ma = df_daily['atr'].rolling(40).mean().iloc[-1]

    # Volatility ratio
    vol_ratio = atr / atr_ma if atr_ma > 0 else 1.0

    # True chaos only when volatility is extremely high AND no clear trend
    if vol_ratio > 2.3:
        return "CHAOS"

    # Strong bullish structure
    if price > ema20 > ema50:
        if (price - ema50) / ema50 > 0.045:
            return "STRONG_BULL"
        return "BULL"

    # Strong bearish structure (important for SHORT)
    elif price < ema20 < ema50:
        if (ema50 - price) / ema50 > 0.045:
            return "STRONG_BEAR"
        return "BEAR"

    # Mild bullish / mild bearish / range
    elif price > ema20 and price > ema50:
        return "BULL"
    elif price < ema20 and price < ema50:
        return "BEAR"
    else:
        # Elevated volatility but still directional → prefer BEAR/BULL over CHAOS
        if vol_ratio > 1.8:
            if price < ema50:
                return "BEAR"
            elif price > ema50:
                return "BULL"
        return "RANGE"


def evaluate_setup(pair, df, regime, trading_mode="PERP", min_distance=0.65):
    """
    Improved quality filter for LONG and SHORT setups.

    Returns:
        dict or None
        {
            "direction": "LONG" or "SHORT",
            "score": float,
            "reason": str,
            "entry": float,
            "sl": float,
            "tp": float
        }
    """

    if df is None or len(df) < 50:
        return None

    price = df['close'].iloc[-1]
    rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
    atr = df['atr'].iloc[-1] if 'atr' in df.columns else price * 0.01

    # Key levels (simple but effective)
    recent_high = df['high'].iloc[-20:].max()
    recent_low = df['low'].iloc[-20:].min()
    ema20 = df['ema20'].iloc[-1] if 'ema20' in df.columns else price
    ema50 = df['ema50'].iloc[-1] if 'ema50' in df.columns else price

    # Distance calculations
    dist_to_low = abs(price - recent_low) / price * 100
    dist_to_high = abs(recent_high - price) / price * 100
    dist_to_ema20 = abs(price - ema20) / price * 100

    # -------------------------------------------------
    # 1. REGIME + MODE GATE
    # -------------------------------------------------
    allow_long = False
    allow_short = False

    if trading_mode == "SPOT":
        # SPOT → only LONG
        if regime in ["STRONG_BULL", "BULL"]:
            allow_long = True
    else:
        # PERP → both directions
        if regime in ["STRONG_BULL", "BULL"]:
            allow_long = True
        elif regime in ["STRONG_BEAR", "BEAR"]:
            allow_short = True
        elif regime == "RANGE":
            # Optional: allow both with stricter filters
            allow_long = True
            allow_short = True

    if not allow_long and not allow_short:
        return None

    # -------------------------------------------------
    # 2. LONG SETUP LOGIC
    # -------------------------------------------------
    if allow_long:
        # Ideal LONG conditions
        long_conditions = [
            dist_to_low <= min_distance or dist_to_ema20 <= min_distance,  # close to support / ema
            32 <= rsi <= 58,  # not overbought, preferably pullback
            price > ema50,  # still above medium trend
            regime in ["STRONG_BULL", "BULL", "RANGE"]
        ]

        if all(long_conditions):
            entry = price
            sl = min(recent_low, price - atr * 1.4)
            risk = entry - sl
            tp = entry + risk * 2.2  # 1:2.2 RR

            quality = 70
            if dist_to_low <= 0.40:
                quality += 10
            if 38 <= rsi <= 48:
                quality += 8
            if regime == "STRONG_BULL":
                quality += 7

            return {
                "direction": "LONG",
                "score": quality,
                "reason": f"LONG | Dist:{min(dist_to_low, dist_to_ema20):.2f}% | RSI:{rsi:.1f}",
                "entry": round(entry, 6),
                "sl": round(sl, 6),
                "tp": round(tp, 6)
            }

    # -------------------------------------------------
    # 3. SHORT SETUP LOGIC (PERP only)
    # -------------------------------------------------
    if allow_short and trading_mode == "PERP":
        # Ideal SHORT conditions
        short_conditions = [
            dist_to_high <= min_distance or dist_to_ema20 <= min_distance,  # close to resistance / ema
            42 <= rsi <= 68,  # not oversold, preferably rejection
            price < ema50,  # below medium trend
            regime in ["STRONG_BEAR", "BEAR", "RANGE"]
        ]

        if all(short_conditions):
            entry = price
            sl = max(recent_high, price + atr * 1.4)
            risk = sl - entry
            tp = entry - risk * 2.2

            quality = 70
            if dist_to_high <= 0.40:
                quality += 10
            if 52 <= rsi <= 62:
                quality += 8
            if regime == "STRONG_BEAR":
                quality += 7

            return {
                "direction": "SHORT",
                "score": quality,
                "reason": f"SHORT | Dist:{min(dist_to_high, dist_to_ema20):.2f}% | RSI:{rsi:.1f}",
                "entry": round(entry, 6),
                "sl": round(sl, 6),
                "tp": round(tp, 6)
            }

    # -------------------------------------------------
    # 4. No valid setup
    # -------------------------------------------------
    return None


'''
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
    '''
