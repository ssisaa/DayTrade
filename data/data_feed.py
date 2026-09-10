import ccxt
import pandas as pd
from config import (
    API_KEY, API_SECRET, MODE, 
    TRADING_MODE, DEFAULT_TYPE, 
    LEVERAGE, PAIRS
)
from utils.logger import logger

class DataFeed:
    def __init__(self):
        self.exchange = ccxt.cryptocom({
            'apiKey': API_KEY if MODE == "LIVE" else None,
            'secret': API_SECRET if MODE == "LIVE" else None,
            'enableRateLimit': True,
            'options': {
                'defaultType': DEFAULT_TYPE,   # "spot" or "swap"
            }
        })

        # Set leverage only in LIVE + PERP mode
        if MODE == "LIVE" and TRADING_MODE == "PERP":
            try:
                for pair in PAIRS:
                    self.exchange.set_leverage(LEVERAGE, pair)
                    logger.info(f"Leverage set to {LEVERAGE}x for {pair}")
            except Exception as e:
                logger.warning(f"Could not set leverage: {e}")

        logger.info(f"DataFeed ready | Mode: {TRADING_MODE} | Type: {DEFAULT_TYPE}")

    def get_ohlcv(self, symbol, timeframe, limit=200):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Data error on {symbol}: {e}")
            return None

    def get_balance(self):
        try:
            return self.exchange.fetch_balance()
        except Exception as e:
            logger.error(f"Balance fetch error: {e}")
            return None


if __name__ == "__main__":
    feed = DataFeed()
    print("Testing BTC/USDT 1h data...")
    df = feed.get_ohlcv("BTC/USDT", "1h", limit=10)
    print(df.tail() if df is not None else "Failed to fetch data")
