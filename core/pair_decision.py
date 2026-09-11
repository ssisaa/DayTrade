# core/pair_decision.py
import ccxt
from core.news_filter import get_news_decision
from config import (
    ALLOWED_SPOT_PAIRS,
    ALLOWED_PERP_PAIRS,
    TRADING_MODE,
    MAX_PAIRS_TO_SCAN
)
from utils.logger import logger
from data.data_feed import DataFeed


def get_24h_change(exchange, pair):
    """Get 24h percentage change"""
    try:
        ticker = exchange.fetch_ticker(pair)
        percentage = ticker.get("percentage")

        if percentage is None:
            last = ticker.get("last")
            open_ = ticker.get("open")
            if last and open_ and open_ != 0:
                percentage = ((last - open_) / open_) * 100
            else:
                percentage = 0.0

        return float(percentage)
    except Exception as e:
        logger.warning(f"Could not get 24h change for {pair}: {e}")
        return 0.0


def decide_best_pairs():
    """
    Daily Trader Decision Engine
    - Looks at major pairs
    - Also allows temporarily strong weaker pairs
    - Ranks them intelligently
    - Returns only the best 1–2 pairs
    """

    logger.info("Running intelligent pair decision engine...")

    feed = DataFeed()
    exchange = feed.exchange

    if TRADING_MODE == "SPOT":
        universe = ALLOWED_SPOT_PAIRS
    else:
        universe = ALLOWED_PERP_PAIRS

    candidates = []

    for pair in universe:
        try:
            # -------- News Check --------
            news = get_news_decision(pair)

            # Hard block on dangerous news
            if news["should_block"]:
                print(f"  {pair} -> BLOCKED (strong negative news)")
                continue

            score = 50  # base score

            # News scoring
            if news["sentiment"] == "POSITIVE":
                score += 18
            elif news["sentiment"] == "NEGATIVE":
                score -= 14
            else:
                score += 2   # neutral

            # -------- Relative Strength --------
            change_24h = get_24h_change(exchange, pair)

            # Healthy movement
            if -3.5 <= change_24h <= 6.0:
                score += 12

            # Mild strength bonus
            if 1.0 <= change_24h <= 4.5:
                score += 8

            # Overextended (already pumped)
            if change_24h > 8.0:
                score -= 10

            # Heavy dump
            if change_24h < -6.0:
                score -= 12

            # Major pair liquidity bonus
            if pair in ["BTC/USDT", "ETH/USDT", "SOL/USDT",
                        "BTCUSD-PERP", "ETHUSD-PERP", "SOLUSD-PERP"]:
                score += 8

            # Mild bonus for mid-cap pairs that are suddenly strong
            mid_cap_pairs = ["CRO/USDT", "EGLD/USDT", "SUI/USDT", "ARB/USDT", "NEAR/USDT"]
            if pair in mid_cap_pairs and change_24h > 2.0 and news["sentiment"] != "NEGATIVE":
                score += 10   # temporary strength bonus

            candidates.append({
                "pair": pair,
                "score": round(score, 1),
                "news": news["sentiment"],
                "change_24h": round(change_24h, 2),
                "reason": news["reason"]
            })

        except Exception as e:
            logger.warning(f"Error evaluating {pair}: {e}")
            continue

    # Sort best to worst
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

    # Select top pairs
    selected = [c for c in candidates if c["score"] >= 50][:MAX_PAIRS_TO_SCAN]

    print("\n" + "="*65)
    print("DAILY TRADER PAIR DECISION")
    print("="*65)

    if not selected:
        print("No good pairs found. Staying in cash this cycle.")
        print("="*65 + "\n")
        return []

    for i, c in enumerate(selected, 1):
        print(f"{i}. {c['pair']:<15} | Score: {c['score']:<5} | 24h: {c['change_24h']:>6}% | News: {c['news']}")

    print("="*65 + "\n")

    chosen_pairs = [c["pair"] for c in selected]
    return chosen_pairs
