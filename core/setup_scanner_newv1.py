# core/setup_scanner.py

from core.indicators import add_indicators
from core.smart_filters import passes_all_smart_filters
from core.news_filter import get_news_decision
from utils.setup_logger import setup_logger
from config import *
import numpy as np


def find_swing_points(df, left=4, right=4):
    highs = []
    lows = []
    for i in range(left, len(df) - right):
        if all(df['high'].iloc[i] >= df['high'].iloc[i - j] for j in range(1, left + 1)) and \
                all(df['high'].iloc[i] >= df['high'].iloc[i + j] for j in range(1, right + 1)):
            highs.append(df['high'].iloc[i])
        if all(df['low'].iloc[i] <= df['low'].iloc[i - j] for j in range(1, left + 1)) and \
                all(df['low'].iloc[i] <= df['low'].iloc[i + j] for j in range(1, right + 1)):
            lows.append(df['low'].iloc[i])
    return highs, lows


def get_htf_bias(df_4h):
    if df_4h is None or len(df_4h) < 30:
        return "NEUTRAL"
    df_4h = add_indicators(df_4h)
    last = df_4h.iloc[-1]
    if last['close'] > last['ema20'] > last['ema50']:
        return "BULLISH"
    elif last['close'] < last['ema20'] < last['ema50']:
        return "BEARISH"
    return "NEUTRAL"


def find_setups(df_1h, df_4h, regime, pair, change_24h=0.0):
    """
    Balanced + Reactive setup scanner.
    - Strongly negative 24h change forces SHORT preference
    - SPOT → only LONG
    - PERP → both directions
    """

    # 1. Smart Filters
    allowed, reason = passes_all_smart_filters(df_1h)
    if not allowed:
        print(f"    -> Filtered out: {reason}")
        return []

    if df_1h is None or len(df_1h) < 70:
        return []

    df_1h = add_indicators(df_1h)
    last = df_1h.iloc[-1]
    atr = last['atr']
    htf_bias = get_htf_bias(df_4h)

    swing_highs, swing_lows = find_swing_points(df_1h)
    support = min(swing_lows[-5:]) if len(swing_lows) >= 5 else df_1h['low'].tail(30).min()
    resistance = max(swing_highs[-5:]) if len(swing_highs) >= 5 else df_1h['high'].tail(30).max()

    setups = []

    # =========================================================
    # FORCE SHORT PREFERENCE when 24h is strongly negative
    # =========================================================
    force_short = change_24h <= -3.5 and TRADING_MODE == "PERP"
    force_long  = change_24h >= 3.5

    if force_short:
        print(f"    -> Strong negative 24h ({change_24h:.2f}%) → Preferring SHORT")
    elif force_long:
        print(f"    -> Strong positive 24h ({change_24h:.2f}%) → Preferring LONG")

    # =========================================================
    # LONG SETUP
    # =========================================================
    allow_long = False

    if TRADING_MODE == "SPOT":
        allow_long = regime in ["BULL", "STRONG_BULL", "RANGE"] and htf_bias != "BEARISH"
    else:  # PERP
        if force_short:
            allow_long = False
        else:
            allow_long = regime in ["BULL", "STRONG_BULL", "RANGE"] and htf_bias != "BEARISH"

    if allow_long:
        distance = abs(last['close'] - support) / last['close']
        long_rsi_pass = 28 <= last['rsi'] <= 52
        long_distance_pass = distance < 0.0065

        if long_distance_pass and long_rsi_pass:
            score = 42
            score_reasons = []

            candle_rejection = (
                last['close'] > last['open'] and
                (last['high'] - last['close']) < (last['close'] - last['low']) * 0.55
            )
            if candle_rejection:
                score += 16
                score_reasons.append("CandleRejection +16")

            if last['volume'] > last['volume_ma'] * 1.25:
                score += 13
                score_reasons.append("Volume +13")

            if htf_bias == "BULLISH":
                score += 15
                score_reasons.append("HTF Bullish +15")
            elif htf_bias == "NEUTRAL":
                score += 5
                score_reasons.append("HTF Neutral +5")

            if regime == "STRONG_BULL":
                score += 14
                score_reasons.append("Strong Bull +14")
            elif regime == "BULL":
                score += 9
                score_reasons.append("Bull +9")
            elif regime == "RANGE":
                score += 4
                score_reasons.append("Range +4")

            if distance < 0.0035:
                score += 10
                score_reasons.append("Near Support +10")

            if 34 <= last['rsi'] <= 45:
                score += 8
                score_reasons.append("RSI Sweet +8")

            news = get_news_decision(pair)
            print(f"    -> News: {news['sentiment']} | {news['reason']}")

            if not news["should_block"]:
                score += news.get("score_adjustment", 0)

                entry = float(last['close'])
                stop = float(support - atr * 0.75)
                risk = entry - stop

                if risk > 0:
                    reward = risk * 2.4
                    target = entry + reward
                    cost = MAKER_FEE + TAKER_FEE + SLIPPAGE * 2
                    net_rr = (reward / risk) - (cost * 5)

                    print(f"    [LONG DEBUG] Score: {score} | RSI: {last['rsi']:.1f} | "
                          f"Distance: {distance*100:.2f}% | Net RR: {net_rr:.2f}")

                    if score >= MIN_QUALITY_SCORE and net_rr >= MIN_RR:
                        setups.append({
                            "pair": pair,
                            "side": "buy",
                            "entry": round(entry, 6),
                            "stop": round(stop, 6),
                            "target": round(target, 6),
                            "score": score,
                            "rr": round(net_rr, 2),
                            "htf_bias": htf_bias,
                            "regime": regime,
                            "news_sentiment": news["sentiment"]
                        })
                        print(f"    [LONG ACCEPTED] Score={score} | Net RR={net_rr:.2f}")
                    else:
                        print(f"    [LONG REJECTED] Score={score} | Net RR={net_rr:.2f}")
        else:
            reasons = []
            if not long_distance_pass:
                reasons.append(f"Distance {distance*100:.2f}% >= 0.65%")
            if not long_rsi_pass:
                reasons.append(f"RSI {last['rsi']:.1f} not in 28-52")
            print(f"    [LONG FILTERED] {' | '.join(reasons)}")

    # =========================================================
    # SHORT SETUP (PERP only)
    # =========================================================
    if TRADING_MODE == "PERP":
        allow_short = False

        if force_short:
            allow_short = True
        else:
            allow_short = regime in ["BEAR", "STRONG_BEAR", "RANGE"] and htf_bias != "BULLISH"

        if allow_short:
            distance = abs(last['close'] - resistance) / last['close']
            short_rsi_pass = 48 <= last['rsi'] <= 72
            short_distance_pass = distance < 0.0065

            if short_distance_pass and short_rsi_pass:
                score = 42
                score_reasons = []

                candle_rejection = (
                    last['close'] < last['open'] and
                    (last['close'] - last['low']) < (last['high'] - last['close']) * 0.55
                )
                if candle_rejection:
                    score += 16
                    score_reasons.append("CandleRejection +16")

                if last['volume'] > last['volume_ma'] * 1.25:
                    score += 13
                    score_reasons.append("Volume +13")

                if htf_bias == "BEARISH":
                    score += 15
                    score_reasons.append("HTF Bearish +15")
                elif htf_bias == "NEUTRAL":
                    score += 5
                    score_reasons.append("HTF Neutral +5")

                if regime == "STRONG_BEAR":
                    score += 14
                    score_reasons.append("Strong Bear +14")
                elif regime == "BEAR":
                    score += 9
                    score_reasons.append("Bear +9")
                elif regime == "RANGE":
                    score += 4
                    score_reasons.append("Range +4")

                # Bonus when we forced short due to strong 24h dump
                if force_short:
                    score += 8
                    score_reasons.append("Forced by 24h dump +8")

                if distance < 0.0035:
                    score += 10
                    score_reasons.append("Near Resistance +10")

                if 55 <= last['rsi'] <= 66:
                    score += 8
                    score_reasons.append("RSI Sweet +8")

                news = get_news_decision(pair)
                print(f"    -> News: {news['sentiment']} | {news['reason']}")

                if not news["should_block"]:
                    score += news.get("score_adjustment", 0)

                    entry = float(last['close'])
                    stop = float(resistance + atr * 0.75)
                    risk = stop - entry

                    if risk > 0:
                        reward = risk * 2.4
                        target = entry - reward
                        cost = MAKER_FEE + TAKER_FEE + SLIPPAGE * 2
                        net_rr = (reward / risk) - (cost * 5)

                        print(f"    [SHORT DEBUG] Score: {score} | RSI: {last['rsi']:.1f} | "
                              f"Distance: {distance*100:.2f}% | Net RR: {net_rr:.2f}")

                        if score >= MIN_QUALITY_SCORE and net_rr >= MIN_RR:
                            setups.append({
                                "pair": pair,
                                "side": "sell",
                                "entry": round(entry, 6),
                                "stop": round(stop, 6),
                                "target": round(target, 6),
                                "score": score,
                                "rr": round(net_rr, 2),
                                "htf_bias": htf_bias,
                                "regime": regime,
                                "news_sentiment": news["sentiment"]
                            })
                            print(f"    [SHORT ACCEPTED] Score={score} | Net RR={net_rr:.2f}")
                        else:
                            print(f"    [SHORT REJECTED] Score={score} | Net RR={net_rr:.2f}")
            else:
                reasons = []
                if not short_distance_pass:
                    reasons.append(f"Distance {distance*100:.2f}% >= 0.65%")
                if not short_rsi_pass:
                    reasons.append(f"RSI {last['rsi']:.1f} not in 48-72")
                print(f"    [SHORT FILTERED] {' | '.join(reasons)}")

    # =========================================================
    # FINAL
    # =========================================================
    if setups:
        best = max(setups, key=lambda x: x["score"])
        print(f"    -> {len(setups)} setup(s) passed | Best: {best['score']} | Side: {best['side'].upper()}")
    else:
        print("    -> No setup passed the quality filters")

    return sorted(setups, key=lambda x: x["score"], reverse=True)
