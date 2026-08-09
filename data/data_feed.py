import ccxt
import pandas as pd
from config import API_KEY, API_SECRET, MODE
from utils.logger import logger


class DataFeed:
    def __init__(self):
        self.exchange = ccxt.cryptocom({
            'apiKey': API_KEY if MODE == "LIVE" else None,
            'secret': API_SECRET if MODE == "LIVE" else None,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def get_ohlcv(self, symbol, timeframe, limit=200):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Data error {symbol}: {e}")
            return None


if __name__ == "__main__":
    feed = DataFeed()
    print("Testing BTC/USDT 1h data...")
    df = feed.get_ohlcv("BTC/USDT", "1h", limit=10)
    print(df.tail() if df is not None else "Failed to fetch data")
