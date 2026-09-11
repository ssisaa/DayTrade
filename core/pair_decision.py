import ccxt
from core.news_filter import get_news_decision
from config import (
    ALLOWED_SPOT_PAIRS, ALLOWED_PERP_PAIRS,
    TRADING_MODE, MAX_PAIRS_TO_SCAN, MODE
)
from utils.logger import logger
from data.data_feed import DataFeed

def get_24h_change(exchange, pair):
    """Get simple 24h price change percentage"""
    try:
        ticker = exchange.fetch_ticker(pair)
        percentage = ticker.get('percentage')
        if percentage is None:
            # fallback calculation
            last = ticker.get('last')
            open_ = ticker.get('open')
            if last and open_ and open_ != 0:
                percentage = ((last - open_) / open_) * 100
            else:
                percentage = 0
        return float(percentage)
    except Exception as e:
        logger.warning(f"Could not get 24h change for {pair}: {e}")
        return 0.0

def decide_best_pairs():
    """
    Intelligent pair selection for daily trading.
    Called only when there is no open position.
    """
    logger.info("Re-evaluating best pairs (expanded universe)...")

    feed = DataFeed()
    exchange = feed.exchange

    universe = ALLOWED_SPOT_PAIRS if TRADING_MODE == "SPOT" else ALLOWED_PERP_PAIRS
    candidates = []

    for pair in universe:
        try:
            # 1. News analysis
            news = get_news_decision(pair)
            
            if news["should_block"]:
                print(f"  {pair} -> Blocked by strong negative news")
                continue

            # 2. Base score
            score = 50

            # News adjustment
            if news["sentiment"] == "POSITIVE":
                score += 18
            elif news["sentiment"] == "NEGATIVE":
                score -= 14
            elif news["sentiment"] == "NEUTRAL":
                score += 2

            # 3. Relative Strength (24h performance)
            change_24h = get_24h_change(exchange, pair)

            # Prefer pairs that are not crashing hard, 
            # but also not extremely extended
            if -3.5 <= change_24h <= 6.0:
                score += 12          # Healthy range
            elif change_24h > 8.0:
                score -= 8           # Already extended (risky for new long)
            elif change_24h < -6.0:
                score -= 10          # Heavy dumping

            # Small bonus for mild relative strength
            if 1.0 <= change_24h <= 4.5:
                score += 6

            # 4. Liquidity preference (simple)
            major_pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", 
                           "BTCUSD-PERP", "ETHUSD-PERP", "SOLUSD-PERP"]
            if pair in major_pairs:
                score += 8

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

    # Sort by score (best first)
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)

    # Only keep decent candidates
    selected = [c for c in candidates if c["score"] >= 48][:MAX_PAIRS_TO_SCAN]

    print("\n" + "="*60)
    print("PAIR DECISION ENGINE")
    print("="*60)

    if not selected:
        print("No suitable pairs found. Staying in cash.")
        print("="*60 + "\n")
        return []

    for i, c in enumerate(selected, 1):
        print(f"{i}. {c['pair']:<15} | Score: {c['score']:<5} | "
              f"24h: {c['change_24h']:>6}% | News: {c['news']}")

    print("="*60 + "\n")

    chosen_pairs = [c["pair"] for c in selected]
    logger.info(f"Selected pairs: {chosen_pairs}")
    
    return chosen_pairs
