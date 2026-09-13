# core/pair_decision.py

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
    """
    Get 24h percentage change.
    Always returns true percentage (e.g. 3.0 means +3%).
    Prefers calculating from last/open for maximum reliability,
    especially important for Crypto.com which returns fraction values.
    """
    try:
        ticker = exchange.fetch_ticker(pair)
        last = ticker.get("last")
        open_ = ticker.get("open")

        # Prefer calculating ourselves – most reliable method
        if last is not None and open_ is not None and open_ != 0:
            percentage = ((last - open_) / open_) * 100
            return float(percentage)

        # Fallback to exchange-provided percentage
        percentage = ticker.get("percentage")
        if percentage is not None:
            percentage = float(percentage)
            # Crypto.com returns the value as a fraction (0.03 = +3%)
            if exchange.id == "cryptocom":
                percentage *= 100
            return percentage

        return 0.0
    except Exception as e:
        # logger.warning(f"Could not get 24h change for {pair}: {e}")
        return 0.0


def decide_best_pairs():
    """
    Balanced Strong-Mover Decision Engine
    - Supports both strong LONG and strong SHORT candidates
    - Avoids chasing extreme late pumps and dumps
    - Still prioritizes capital protection
    """
    feed = DataFeed()
    exchange = feed.exchange
    universe = ALLOWED_SPOT_PAIRS if TRADING_MODE == "SPOT" else ALLOWED_PERP_PAIRS

    candidates = []

    for pair in universe:
        try:
            # 1. News filter
            news = get_news_decision(pair)
            if news["should_block"]:
                print(f"  {pair} -> BLOCKED (strong negative news)")
                continue

            score = 50
            change_24h = get_24h_change(exchange, pair)

            # 2. News scoring
            if news["sentiment"] == "POSITIVE":
                score += 16
            elif news["sentiment"] == "NEGATIVE":
                if TRADING_MODE == "SPOT":
                    score -=14
                else:
                    score += 14          # Negative news is now useful for SHORT
            else:
                score += 3

            # 3. Balanced Controlled Strength Scoring (LONG + SHORT)
            # ----- Upside (LONG friendly) -----
            if 1.5 <= change_24h <= 4.5:
                score += 14          # healthy mild strength (LONG)
            elif 4.5 < change_24h <= 9.0:
                score += 10          # strong but still acceptable (LONG)
            elif 9.0 < change_24h <= 12.0:
                score -= 4           # getting extended
            elif change_24h > 12.0:
                score -= 16          # dangerous late pump

            # ----- Downside (SHORT friendly) -----
            elif -4.5 <= change_24h <= -1.5:
                score += 14          # healthy mild strength (SHORT)
            elif -9.0 <= change_24h < -4.5:
                score += 10          # strong but still acceptable (SHORT)
            elif -12.0 <= change_24h < -9.0:
                score -= 4           # getting extended on downside
            elif change_24h < -12.0:
                score -= 16          # dangerous late dump

            # ----- Quiet / normal range -----
            elif -1.5 < change_24h < 1.5:
                score += 6

            # 4. Major pair liquidity bonus
            major_pairs = [
                "BTC/USDT", "ETH/USDT", "SOL/USDT", "CRO/USDT", "EGLD/USDT",
                "BTCUSD-PERP", "ETHUSD-PERP", "SOLUSD-PERP"
            ]
            if pair in major_pairs:
                score += 8

            # 5. Temporary strength bonus for mid/weaker pairs (both directions)
            mid_pairs = [
                "XRP/USDT", "ADA/USDT", "SUI/USDT", "ARB/USDT",
                "NEAR/USDT", "APT/USDT", "OP/USDT", "ATOM/USDT",
                "DOGE/USDT", "LINK/USDT"
            ]
            if pair in mid_pairs:
                if 2.0 <= abs(change_24h) <= 9.0:
                    score += 12   # controlled strength in either direction

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

    # Rank best to worst
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

    # Keep only acceptable pairs
    selected = [c for c in candidates if c["score"] >= 53][:MAX_PAIRS_TO_SCAN]

    print("\n" + "="*65)
    print("BALANCED STRONG-MOVER DECISION ENGINE")
    print("="*65)

    if not selected:
        print("No good pairs found. Staying in cash this cycle.")
        print("="*65 + "\n")
        return []

    for i, c in enumerate(selected, 1):
        print(f"{i}. {c['pair']:<15} | Score: {c['score']:<5} | "
              f"24h: {c['change_24h']:>6}% | News: {c['news']}")
    print("="*65 + "\n")

    return [c["pair"] for c in selected]
