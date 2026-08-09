# core/setup_scanner.py
from core.indicators import add_indicators
from core.smart_filters import passes_all_smart_filters
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


def find_setups(df_1h, df_4h, regime, pair):
    # 1. Smart Filters first
    allowed, reason = passes_all_smart_filters(df_1h)
    if not allowed:
        print(f"    → Filtered out: {reason}")
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
    # LONG SETUP
    # =========================================================
    if regime in ["BULL", "STRONG_BULL", "RANGE"] and htf_bias != "BEARISH":
        distance = abs(last['close'] - support) / last['close']

        # -----------------------------------------------------
        # LONG ENTRY CONDITIONS
        # -----------------------------------------------------
        long_rsi_pass = last['rsi'] < 36
        long_distance_pass = distance < 0.0065
        if long_distance_pass and long_rsi_pass:

            # =================================================
            # SCORE CALCULATION
            # =================================================
            score = 40
            score_reasons = []

            # -------------------------------------------------
            # Candle rejection
            # -------------------------------------------------
            candle_rejection = (
                    last['close'] > last['open']
                    and
                    (last['high'] - last['close'])
                    <
                    (last['close'] - last['low']) * 0.6
            )

            if candle_rejection:
                score += 18
                score_reasons.append(
                    "CandleRejection +18"
                )

            # -------------------------------------------------
            # Volume confirmation
            # -------------------------------------------------
            volume_confirmation = (
                    last['volume'] >
                    last['volume_ma'] * 1.3
            )

            if volume_confirmation:
                score += 15
                score_reasons.append(
                    "Volume +15"
                )

            # -------------------------------------------------
            # Higher timeframe confirmation
            # -------------------------------------------------
            if htf_bias == "BULLISH":

                score += 16
                score_reasons.append(
                    "HTF Bullish +16"
                )
            elif htf_bias == "NEUTRAL":

                score += 5
                score_reasons.append(
                    "HTF Neutral +5"
                )

            # -------------------------------------------------
            # Regime strength
            # -------------------------------------------------
            if regime == "STRONG_BULL":
                score += 14
                score_reasons.append(
                    "Strong Bull +14"
                )
            elif regime == "BULL":

                score += 9
                score_reasons.append(
                    "Bull +9"
                )

            # -------------------------------------------------
            # Distance to support
            # -------------------------------------------------
            if distance < 0.003:
                score += 10
                score_reasons.append(
                    "Near Support +10"
                )

            # -------------------------------------------------
            # RSI extreme
            # -------------------------------------------------
            if last['rsi'] < 30:
                score += 8
                score_reasons.append(
                    "RSI Extreme +8"
                )

            # =================================================
            # LONG RISK / REWARD
            # =================================================
            entry = float(last['close'])
            # Stop must be BELOW entry
            stop = float(
                support - atr * 0.8
            )
            # Risk distance
            risk = entry - stop

            # -------------------------------------------------
            # Validate LONG stop
            # -------------------------------------------------
            if risk <= 0:
                status = "REJECTED"
                reason = (
                    f"Invalid LONG risk | "
                    f"Entry={entry:.6f} | "
                    f"Stop={stop:.6f} | "
                    f"Risk={risk:.6f}"
                )
                print(
                    f"    [LONG REJECTED] "
                    f"{reason}"
                )
                setup_logger.log_setup(
                    pair=pair,
                    side="buy",
                    status=status,
                    score=score,
                    rsi=last['rsi'],
                    distance=distance,
                    net_rr=0.0,
                    htf_bias=htf_bias,
                    regime=regime,
                    entry=entry,
                    stop=stop,
                    target=entry,
                    reason=reason
                )
            else:
                # -------------------------------------------------
                # LONG target
                # -------------------------------------------------
                reward = risk * 2.5
                target = entry + reward

                # -------------------------------------------------
                # Fees + slippage
                # -------------------------------------------------
                cost = (
                        MAKER_FEE
                        +
                        TAKER_FEE
                        +
                        SLIPPAGE * 2
                )
                gross_rr = reward / risk
                net_rr = (
                        gross_rr -
                        (cost * 6)
                )

                # =================================================
                # DEBUG LOG
                # =================================================
                print(
                    f"    [LONG DEBUG] "
                    f"Score: {score} | "
                    f"RSI: {last['rsi']:.1f} | "
                    f"Distance: {distance * 100:.2f}% | "
                    f"HTF: {htf_bias} | "
                    f"Risk: {risk:.6f} | "
                    f"Gross RR: {gross_rr:.2f} | "
                    f"Net RR: {net_rr:.2f}"
                )
                print(
                    f"    [LONG SCORE] "
                    f"{', '.join(score_reasons) if score_reasons else 'Base Score 40'} "
                    f"| Total={score}"
                )

                # =================================================
                # FINAL FILTER CHECKS
                # =================================================
                score_pass = (
                        score >= MIN_QUALITY_SCORE
                )
                rr_pass = (
                        net_rr >= MIN_RR
                )
                risk_pass = (
                        risk > 0
                )

                # =================================================
                # ACCEPT / REJECT
                # =================================================
                if score_pass and rr_pass and risk_pass:
                    status = "ACCEPTED"
                    reason = (
                        "Passed all quality and risk filters"
                    )
                    setups.append({
                        "pair": pair,
                        "side": "buy",
                        "entry": round(entry, 4),
                        "stop": round(stop, 4),
                        "target": round(target, 4),
                        "score": score,
                        "rr": round(net_rr, 2),
                        "htf_bias": htf_bias,
                        "regime": regime
                    })
                    print(
                        f"    ✓ [LONG ACCEPTED] "
                        f"Score={score} >= {MIN_QUALITY_SCORE} | "
                        f"Net RR={net_rr:.2f} >= {MIN_RR} | "
                        f"Entry={entry:.6f} | "
                        f"Stop={stop:.6f} | "
                        f"Target={target:.6f}"
                    )
                else:
                    status = "REJECTED"
                    rejection_reasons = []
                    if not score_pass:
                        rejection_reasons.append(
                            f"Score {score} < {MIN_QUALITY_SCORE}"
                        )
                    if not rr_pass:
                        rejection_reasons.append(
                            f"Net RR {net_rr:.2f} < {MIN_RR}"
                        )
                    if not risk_pass:
                        rejection_reasons.append(
                            "Risk <= 0"
                        )
                    reason = " | ".join(
                        rejection_reasons
                    )
                    print(
                        f"    ✗ [LONG REJECTED] "
                        f"{reason}"
                    )

                # =================================================
                # SAVE TO CSV
                # =================================================
                setup_logger.log_setup(
                    pair=pair,
                    side="buy",
                    status=status,
                    score=score,
                    rsi=last['rsi'],
                    distance=distance,
                    net_rr=net_rr,
                    htf_bias=htf_bias,
                    regime=regime,
                    entry=entry,
                    stop=stop,
                    target=target,
                    reason=reason
                )
        else:
            # =================================================
            # LONG ENTRY CONDITION REJECTION
            # =================================================
            rejection_reasons = []
            if not long_distance_pass:
                rejection_reasons.append(
                    f"Distance {distance * 100:.2f}% >= 0.65%"
                )
            if not long_rsi_pass:
                rejection_reasons.append(
                    f"RSI {last['rsi']:.1f} >= 36"
                )
            reason = " | ".join(
                rejection_reasons
            )
            print(
                f"    [LONG FILTERED] "
                f"{reason}"
            )

    # =========================================================
    # SHORT SETUP
    # =========================================================
    if regime in ["BEAR", "STRONG_BEAR", "RANGE"] and htf_bias != "BULLISH":
        distance = abs(last['close'] - resistance) / last['close']

        # -----------------------------------------------------
        # SHORT ENTRY CONDITIONS
        # -----------------------------------------------------
        short_rsi_pass = last['rsi'] > 64
        short_distance_pass = distance < 0.0065
        if short_distance_pass and short_rsi_pass:

            # =================================================
            # SCORE CALCULATION
            # =================================================
            score = 40
            score_reasons = []

            # -------------------------------------------------
            # Candle rejection
            # -------------------------------------------------
            candle_rejection = (
                    last['close'] < last['open']
                    and
                    (last['close'] - last['low'])
                    <
                    (last['high'] - last['close']) * 0.6
            )
            if candle_rejection:
                score += 18
                score_reasons.append(
                    "CandleRejection +18"
                )

            # -------------------------------------------------
            # Volume confirmation
            # -------------------------------------------------
            volume_confirmation = (
                    last['volume'] >
                    last['volume_ma'] * 1.3
            )
            if volume_confirmation:
                score += 15

                score_reasons.append(
                    "Volume +15"
                )

            # -------------------------------------------------
            # Higher timeframe confirmation
            # -------------------------------------------------
            if htf_bias == "BEARISH":
                score += 16
                score_reasons.append(
                    "HTF Bearish +16"
                )
            elif htf_bias == "NEUTRAL":
                score += 5
                score_reasons.append(
                    "HTF Neutral +5"
                )

            # -------------------------------------------------
            # Regime strength
            # -------------------------------------------------
            if regime == "STRONG_BEAR":
                score += 14
                score_reasons.append(
                    "Strong Bear +14"
                )
            elif regime == "BEAR":
                score += 9
                score_reasons.append(
                    "Bear +9"
                )

            # -------------------------------------------------
            # Distance to resistance
            # -------------------------------------------------
            if distance < 0.003:
                score += 10
                score_reasons.append(
                    "Near Resistance +10"
                )

            # -------------------------------------------------
            # RSI extreme
            # -------------------------------------------------
            if last['rsi'] > 70:
                score += 8
                score_reasons.append(
                    "RSI Extreme +8"
                )

            # =================================================
            # SHORT RISK / REWARD
            # =================================================
            entry = float(last['close'])
            # IMPORTANT:
            # SHORT stop must be ABOVE entry.
            stop = float(
                resistance + atr * 0.8
            )
            # Risk distance
            risk = stop - entry

            # -------------------------------------------------
            # Validate SHORT stop
            # -------------------------------------------------
            if risk <= 0:
                status = "REJECTED"
                reason = (
                    f"Invalid SHORT risk | "
                    f"Entry={entry:.6f} | "
                    f"Stop={stop:.6f} | "
                    f"Risk={risk:.6f}"
                )
                print(
                    f"    [SHORT REJECTED] "
                    f"{reason}"
                )
                setup_logger.log_setup(
                    pair=pair,
                    side="sell",
                    status=status,
                    score=score,
                    rsi=last['rsi'],
                    distance=distance,
                    net_rr=0.0,
                    htf_bias=htf_bias,
                    regime=regime,
                    entry=entry,
                    stop=stop,
                    target=entry,
                    reason=reason
                )
            else:
                # -------------------------------------------------
                # SHORT target
                # -------------------------------------------------
                reward = risk * 2.5
                # IMPORTANT:
                # SHORT target must be BELOW entry.
                target = entry - reward
                # -------------------------------------------------
                # Fees + slippage
                # -------------------------------------------------
                cost = (
                        MAKER_FEE
                        +
                        TAKER_FEE
                        +
                        SLIPPAGE * 2
                )
                gross_rr = reward / risk
                net_rr = (
                        gross_rr -
                        (cost * 6)
                )

                # =================================================
                # DEBUG LOG
                # =================================================
                print(
                    f"    [SHORT DEBUG] "
                    f"Score: {score} | "
                    f"RSI: {last['rsi']:.1f} | "
                    f"Distance: {distance * 100:.2f}% | "
                    f"HTF: {htf_bias} | "
                    f"Risk: {risk:.6f} | "
                    f"Gross RR: {gross_rr:.2f} | "
                    f"Net RR: {net_rr:.2f}"
                )
                print(
                    f"    [SHORT SCORE] "
                    f"{', '.join(score_reasons) if score_reasons else 'Base Score 40'} "
                    f"| Total={score}"
                )

                # =================================================
                # FINAL FILTER CHECKS
                # =================================================
                score_pass = (
                        score >= MIN_QUALITY_SCORE
                )
                rr_pass = (
                        net_rr >= MIN_RR
                )
                risk_pass = (
                        risk > 0
                )

                # =================================================
                # ACCEPT / REJECT
                # =================================================
                if score_pass and rr_pass and risk_pass:

                    status = "ACCEPTED"

                    reason = (
                        "Passed all quality and risk filters"
                    )
                    setups.append({
                        "pair": pair,
                        "side": "sell",
                        "entry": round(entry, 4),
                        "stop": round(stop, 4),
                        "target": round(target, 4),
                        "score": score,
                        "rr": round(net_rr, 2),
                        "htf_bias": htf_bias,
                        "regime": regime
                    })
                    print(
                        f"    ✓ [SHORT ACCEPTED] "
                        f"Score={score} >= {MIN_QUALITY_SCORE} | "
                        f"Net RR={net_rr:.2f} >= {MIN_RR} | "
                        f"Entry={entry:.6f} | "
                        f"Stop={stop:.6f} | "
                        f"Target={target:.6f}"
                    )
                else:
                    status = "REJECTED"
                    rejection_reasons = []
                    if not score_pass:
                        rejection_reasons.append(
                            f"Score {score} < {MIN_QUALITY_SCORE}"
                        )
                    if not rr_pass:
                        rejection_reasons.append(
                            f"Net RR {net_rr:.2f} < {MIN_RR}"
                        )
                    if not risk_pass:
                        rejection_reasons.append(
                            "Risk <= 0"
                        )
                    reason = " | ".join(
                        rejection_reasons
                    )
                    print(
                        f"    ✗ [SHORT REJECTED] "
                        f"{reason}"
                    )

                # =================================================
                # SAVE TO CSV
                # =================================================
                setup_logger.log_setup(
                    pair=pair,
                    side="sell",
                    status=status,
                    score=score,
                    rsi=last['rsi'],
                    distance=distance,
                    net_rr=net_rr,
                    htf_bias=htf_bias,
                    regime=regime,
                    entry=entry,
                    stop=stop,
                    target=target,
                    reason=reason
                )
        else:
            # =================================================
            # SHORT ENTRY CONDITION REJECTION
            # =================================================
            rejection_reasons = []
            if not short_distance_pass:
                rejection_reasons.append(
                    f"Distance {distance * 100:.2f}% >= 0.65%"
                )
            if not short_rsi_pass:
                rejection_reasons.append(
                    f"RSI {last['rsi']:.1f} <= 64"
                )
            reason = " | ".join(
                rejection_reasons
            )
            print(
                f"    [SHORT FILTERED] "
                f"{reason}"
            )

    # =========================================================
    # FINAL SETUP RESULT
    # =========================================================
    if setups:
        best_setup = max(
            setups,
            key=lambda x: x["score"]
        )
        print(
            f"    → {len(setups)} setup(s) passed all filters | "
            f"Best score: {best_setup['score']} | "
            f"Side: {best_setup['side'].upper()} | "
            f"RR: {best_setup['rr']:.2f}"
        )
    else:
        print(
            "    → No setup passed the quality filters"
        )
        
    return sorted(
        setups,
        key=lambda x: x["score"],
        reverse=True
    )
