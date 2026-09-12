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


def get_24h_change_old(exchange, pair):
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

def get_24h_change_old1(exchange, pair):
    """Get 24h percentage change (always returns true % , e.g. 3.0 for +3%)"""
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
        else:
            percentage = float(percentage)
            # Crypto.com returns fraction (0.03 = 3%). Convert to true percent.
            if abs(percentage) < 1.0:          # heuristic: values under 1 are almost certainly fractions
                percentage *= 100

        return float(percentage)
    except Exception as e:
        logger.warning(f"Could not get 24h change for {pair}: {e}")
        return 0.0


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
        logger.warning(f"Could not get 24h change for {pair}: {e}")
        return 0.0


def decide_best_pairs():
    """
    Controlled Strong-Mover Decision Engine
    - Allows strong pairs in a safe way
    - Avoids chasing late dangerous pumps
    - Still prioritizes capital protection
    """

    logger.info("Running controlled strong-mover pair decision...")

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
                score -= 14
            else:
                score += 3

            # 3. Controlled Strength Scoring (Important)
            if 1.5 <= change_24h <= 4.5:
                score += 14          # healthy mild strength
            elif 4.5 < change_24h <= 9.0:
                score += 10          # strong but still acceptable
            elif 9.0 < change_24h <= 12.0:
                score -= 4           # getting extended
            elif change_24h > 12.0:
                score -= 16          # dangerous late pump - avoid chasing
            elif -3.5 <= change_24h < 1.5:
                score += 6           # normal / slight pullback
            elif change_24h < -6.5:
                score -= 13          # heavy dump

            # 4. Major pair liquidity bonus
            if pair in ["BTC/USDT", "ETH/USDT", "SOL/USDT",
                        "BTCUSD-PERP", "ETHUSD-PERP", "SOLUSD-PERP"]:
                score += 8

            # 5. Temporary strength bonus for mid/weaker pairs
            mid_pairs = [
                "CRO/USDT", "EGLD/USDT", "SUI/USDT", "ARB/USDT",
                "NEAR/USDT", "APT/USDT", "OP/USDT", "ATOM/USDT",
                "DOGE/USDT", "ADA/USDT", "LINK/USDT", "XRP/USDT"
            ]

            if pair in mid_pairs and 2.0 <= change_24h <= 9.0 and news["sentiment"] != "NEGATIVE":
                score += 11   # catch controlled strength on weaker pairs

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
    print("CONTROLLED STRONG-MOVER DECISION ENGINE")
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

"""# core/pair_decision.py
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
    Improved Daily Trader Decision Engine
    - Can select major pairs
    - Can also select temporarily strong / top-gainer style pairs
    - Still blocks dangerous news and extreme conditions
    """

    logger.info("Running improved pair decision engine...")

    feed = DataFeed()
    exchange = feed.exchange

    if TRADING_MODE == "SPOT":
        universe = ALLOWED_SPOT_PAIRS
    else:
        universe = ALLOWED_PERP_PAIRS

    candidates = []

    for pair in universe:
        try:
            # ---------- 1. News Check ----------
            news = get_news_decision(pair)

            # Hard block on strong negative news
            if news["should_block"]:
                print(f"  {pair} -> BLOCKED (strong negative news)")
                continue

            score = 50  # base score

            # News scoring
            if news["sentiment"] == "POSITIVE":
                score += 18
            elif news["sentiment"] == "NEGATIVE":
                score -= 15
            else:
                score += 3  # neutral

            # ---------- 2. Relative Strength / Top Gainer Logic ----------
            change_24h = get_24h_change(exchange, pair)

            # Strong daily gainer (potential opportunity)
            if 3.0 <= change_24h <= 9.0:
                score += 16          # healthy strong move
            elif 1.5 <= change_24h < 3.0:
                score += 9           # mild strength
            elif change_24h > 12.0:
                score -= 12          # already overextended (risky to chase)
            elif -4.0 <= change_24h < 1.5:
                score += 6           # normal / slight pullback
            elif change_24h < -7.0:
                score -= 14          # heavy dumping

            # ---------- 3. Liquidity Preference ----------
            major_pairs = [
                "BTC/USDT", "ETH/USDT", "SOL/USDT",
                "BTCUSD-PERP", "ETHUSD-PERP", "SOLUSD-PERP"
            ]
            if pair in major_pairs:
                score += 8

            # ---------- 4. Temporary Strength Bonus for Weaker Pairs ----------
            mid_weak_pairs = [
                "CRO/USDT", "EGLD/USDT", "SUI/USDT", "ARB/USDT",
                "NEAR/USDT", "APT/USDT", "OP/USDT", "ATOM/USDT",
                "DOGE/USDT", "ADA/USDT", "LINK/USDT"
            ]

            # If a normally weaker pair is suddenly strong + news is not negative
            if pair in mid_weak_pairs and change_24h >= 2.5 and news["sentiment"] != "NEGATIVE":
                score += 12   # catch temporary strength

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

    # Only keep decent candidates
    selected = [c for c in candidates if c["score"] >= 52][:MAX_PAIRS_TO_SCAN]

    print("\n" + "="*65)
    print("IMPROVED PAIR DECISION ENGINE")
    print("="*65)

    if not selected:
        print("No good pairs found. Staying in cash this cycle.")
        print("="*65 + "\n")
        return []

    for i, c in enumerate(selected, 1):
        print(f"{i}. {c['pair']:<15} | Score: {c['score']:<5} | "
              f"24h: {c['change_24h']:>6}% | News: {c['news']}")

    print("="*65 + "\n")

    chosen_pairs = [c["pair"] for c in selected]
    logger.info(f"Selected pairs: {chosen_pairs}")

    return chosen_pairs

========================================================================================================================================

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
    return chosen_pairs"""
