# core/smart_filters.py
from datetime import datetime, timezone
from config import *
from utils.helpers import calculate_atr  # we will use this


def is_high_volume_session():
    """Only allow trading during high-volume hours (UTC)"""
    if not ENABLE_SESSION_FILTER:
        return True

    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    return SESSION_START_UTC <= hour < SESSION_END_UTC


def is_safe_from_news():
    """Basic news / session open protection"""
    if not ENABLE_NEWS_PROTECTION:
        return True

    now_utc = datetime.now(timezone.utc)
    minute = now_utc.minute

    if now_utc.hour in [7, 8, 12, 13, 14] and minute < AVOID_FIRST_MINUTES:
        return False
    return True


def is_volatility_safe(df):
    """Block trading when volatility is extreme"""
    if not ENABLE_VOLATILITY_PROTECTION or df is None or len(df) < 40:
        return True

    # Calculate ATR if it does not exist yet
    if 'atr' not in df.columns:
        df = df.copy()
        df['atr'] = calculate_atr(df, period=14)

    current_atr = df['atr'].iloc[-1]
    avg_atr = df['atr'].rolling(40).mean().iloc[-1]

    if avg_atr == 0 or current_atr != current_atr:  # check for NaN
        return True

    return current_atr < (avg_atr * MAX_ATR_MULTIPLIER)


def passes_all_smart_filters(df_1h):
    """Master filter – must pass everything"""
    if not is_high_volume_session():
        return False, "Outside high-volume session"

    if not is_safe_from_news():
        return False, "News / session open protection"

    if not is_volatility_safe(df_1h):
        return False, "Volatility too high (Chaos protection)"

    return True, "All smart filters passed"
