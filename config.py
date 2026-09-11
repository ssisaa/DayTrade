# ============================================================
# VeteranSR-Agent - Complete Config
# Easy Switch between SPOT and PERPETUAL
# ============================================================

# ====================== TRADING MODE ======================
# Change only this line:
# "SPOT"  = Spot trading (safer, recommended for beginners)
# "PERP"  = Perpetual contracts (higher risk)

# ====================== DYNAMIC PAIR DECISION ======================
# The bot will decide pairs automatically.
# These are only the allowed universe (high liquidity only)

# ====================== DYNAMIC PAIR UNIVERSE ======================
# High liquidity + reasonable pairs on Crypto.com (Spot)
ALLOWED_SPOT_PAIRS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
    "DOGE/USDT", "LTC/USDT", "ATOM/USDT", "NEAR/USDT",
    "APT/USDT", "SUI/USDT", "ARB/USDT", "OP/USDT",
    "CRO/USDT", "EGLD/USDT"
]

# Perpetual major pairs (only the more liquid ones)
ALLOWED_PERP_PAIRS = [
    "BTCUSD-PERP", "ETHUSD-PERP", "SOLUSD-PERP",
    "XRPUSD-PERP", "ADAUSD-PERP", "AVAXUSD-PERP"
]

# Current preferred mode (can still be overridden by the decision engine)
TRADING_MODE = "SPOT"

# Force the bot to re-decide pairs every time there is no open position
DYNAMIC_PAIR_SELECTION = True

# Maximum pairs to scan after decision (keep low for quality)
MAX_PAIRS_TO_SCAN = 2

# ====================== MODE ======================
# "PAPER" = Safe simulation (recommended)
# "LIVE"  = Real money

MODE = "PAPER"

# ====================== API KEYS ======================
API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"

# ====================== CAPITAL ======================
STARTING_EQUITY = 50.0

# ====================== AUTO SETTINGS BY MODE ======================
if TRADING_MODE == "SPOT":
    PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    DEFAULT_TYPE = "spot"
    LEVERAGE = 1
    RISK_PER_TRADE = 0.004              # 0.4%
    MAX_PORTFOLIO_HEAT = 0.35
    DAILY_LOSS_LIMIT = 0.020            # 2.0%
    MAX_DRAWDOWN = 0.08
    MIN_QUALITY_SCORE = 78
else:
    # PERPETUAL MODE
    PAIRS = ["CROUSD-PERP", "EGLDUSD-PERP"]
    DEFAULT_TYPE = "swap"
    LEVERAGE = 1                        # Keep 1x for safety
    RISK_PER_TRADE = 0.003              # 0.3% (stricter)
    MAX_PORTFOLIO_HEAT = 0.25
    DAILY_LOSS_LIMIT = 0.015            # 1.5%
    MAX_DRAWDOWN = 0.06
    MIN_QUALITY_SCORE = 80

# ====================== COMMON RISK SETTINGS ======================
MAX_OPEN_POSITIONS = 1                  # Very important - only 1 position at a time
WEEKLY_LOSS_LIMIT = 0.04
CONSECUTIVE_LOSS_PAUSE = 2
MARGIN_MODE = "isolated"

# ====================== TIMEFRAMES ======================
SIGNAL_TIMEFRAME = "1h"
HIGHER_TIMEFRAME = "1d"

# ====================== STRATEGY PARAMETERS ======================
MIN_RR = 1.7
ATR_PERIOD = 14
RSI_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 50

# ====================== FEES & SLIPPAGE ======================
MAKER_FEE = 0.0025
TAKER_FEE = 0.0050
SLIPPAGE = 0.0010

# ====================== LOOP ======================
LOOP_SLEEP_SECONDS = 30

# ====================== INTELLIGENT FILTERS ======================
ENABLE_SESSION_FILTER = True
SESSION_START_UTC = 7
SESSION_END_UTC = 21

ENABLE_VOLATILITY_PROTECTION = True
MAX_ATR_MULTIPLIER = 2.0

ENABLE_NEWS_PROTECTION = True
AVOID_FIRST_MINUTES = 25

# ====================== ADVANCED FEATURES ======================
ENABLE_ADAPTIVE_SIZING = True
ENABLE_PARTIAL_TP = True
ENABLE_DYNAMIC_SCORE = True

FULL_SIZE_SCORE = 88
MEDIUM_SIZE_SCORE = 78
MEDIUM_SIZE_MULTIPLIER = 0.60

PARTIAL_TP1_R = 1.5
PARTIAL_TP2_R = 2.5

RECENT_TRADES_WINDOW = 10
LOW_WINRATE_THRESHOLD = 0.42
DYNAMIC_SCORE_BOOST = 6

# ====================== TELEGRAM (Optional) ======================
ENABLE_TELEGRAM = False
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# ====================== NEWS FILTER ======================
ENABLE_NEWS_FILTER = True

# How many recent news items to check
NEWS_LOOKBACK_HOURS = 12

# Keywords (you can expand later)
POSITIVE_KEYWORDS = [
    "partnership", "adoption", "listing", "upgrade", "mainnet", 
    "bullish", "surge", "rally", "approval", "integration", "funding"
]

NEGATIVE_KEYWORDS = [
    "hack", "exploit", "sec", "lawsuit", "ban", "delist", "investigation",
    "crash", "dump", "bearish", "scam", "rug", "outage", "penalty", "fine"
]

# Score adjustment
NEWS_POSITIVE_BOOST = 6
NEWS_NEGATIVE_PENALTY = 10
NEWS_STRONG_NEGATIVE_BLOCK = True   # Block trade on strong negative news
