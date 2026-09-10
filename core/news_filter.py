# core/news_filter.py
import requests
from datetime import datetime, timedelta
from config import (
    ENABLE_NEWS_FILTER, NEWS_LOOKBACK_HOURS,
    POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS,
    NEWS_POSITIVE_BOOST, NEWS_NEGATIVE_PENALTY,
    NEWS_STRONG_NEGATIVE_BLOCK
)
from utils.logger import logger

def get_coin_from_pair(pair: str) -> str:
    """Extract coin symbol from pair name"""
    pair = pair.upper().replace("-", "").replace("/", "")
    if "PERP" in pair:
        pair = pair.replace("USDPERP", "").replace("USDTPERP", "")
    for quote in ["USDT", "USD", "USDC"]:
        if pair.endswith(quote):
            return pair.replace(quote, "")
    return pair[:4]  # fallback

def fetch_recent_news(coin: str):
    """
    Fetch recent news. 
    Uses a free public endpoint when possible.
    Returns list of titles (lowercase).
    """
    if not ENABLE_NEWS_FILTER:
        return []

    try:
        # Free public news endpoint (no key required)
        url = f"https://cryptocurrency.cv/api/search?q={coin}&limit=15"
        response = requests.get(url, timeout=8)
        
        if response.status_code != 200:
            # Fallback: try another simple source or return empty
            return []

        data = response.json()
        titles = []

        # Handle different possible response structures
        items = data if isinstance(data, list) else data.get("data", data.get("news", data.get("results", [])))
        
        for item in items:
            title = ""
            if isinstance(item, dict):
                title = item.get("title") or item.get("headline") or item.get("name") or ""
            elif isinstance(item, str):
                title = item
            if title:
                titles.append(title.lower())

        return titles[:12]

    except Exception as e:
        logger.warning(f"News fetch failed for {coin}: {e}")
        return []

def analyze_news_sentiment(titles: list) -> dict:
    """
    Simple keyword-based sentiment analysis.
    Returns: sentiment, score_adjustment, should_block, reason
    """
    if not titles:
        return {
            "sentiment": "NEUTRAL",
            "score_adjustment": 0,
            "should_block": False,
            "reason": "No relevant news found"
        }

    positive_count = 0
    negative_count = 0
    strong_negative = False

    for title in titles:
        for word in POSITIVE_KEYWORDS:
            if word in title:
                positive_count += 1
        for word in NEGATIVE_KEYWORDS:
            if word in title:
                negative_count += 1
                if word in ["hack", "exploit", "sec", "lawsuit", "ban", "delist", "scam"]:
                    strong_negative = True

    if strong_negative and NEWS_STRONG_NEGATIVE_BLOCK:
        return {
            "sentiment": "STRONG_NEGATIVE",
            "score_adjustment": -NEWS_NEGATIVE_PENALTY,
            "should_block": True,
            "reason": "Strong negative news detected (hack/regulation/lawsuit etc.)"
        }

    if negative_count > positive_count + 1:
        return {
            "sentiment": "NEGATIVE",
            "score_adjustment": -NEWS_NEGATIVE_PENALTY,
            "should_block": False,
            "reason": f"More negative news ({negative_count} neg vs {positive_count} pos)"
        }

    if positive_count > negative_count + 1:
        return {
            "sentiment": "POSITIVE",
            "score_adjustment": NEWS_POSITIVE_BOOST,
            "should_block": False,
            "reason": f"Positive news bias ({positive_count} pos vs {negative_count} neg)"
        }

    return {
        "sentiment": "NEUTRAL",
        "score_adjustment": 0,
        "should_block": False,
        "reason": "Mixed or neutral news"
    }

def get_news_decision(pair: str) -> dict:
    """
    Main function to call before placing a trade.
    """
    if not ENABLE_NEWS_FILTER:
        return {
            "sentiment": "DISABLED",
            "score_adjustment": 0,
            "should_block": False,
            "reason": "News filter disabled"
        }

    coin = get_coin_from_pair(pair)
    titles = fetch_recent_news(coin)
    result = analyze_news_sentiment(titles)
    
    logger.info(f"News for {coin}: {result['sentiment']} | {result['reason']}")
    return result
