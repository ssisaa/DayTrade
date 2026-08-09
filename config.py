# ====================== CONFIG ======================
# MODE: "PAPER" (safe, recommended) or "LIVE"
MODE = "LIVE"

# Crypto.com Exchange API (only needed for LIVE)
API_KEY = 'xxxxxxxxxxxxxxxxxxxxxx'
API_SECRET = 'xxxxxxxxxxxxxxxxxxxxxx'
# API_KEY = 'htd1ZMNGVU79K3e3Usu2eh'
# API_SECRET = 'PLNf7NrJNpRSaXyJEhXY2o'

# Starting capital simulation
STARTING_EQUITY = 50.0

# ====================== RISK MANAGEMENT ======================
# Strong risk controls kept (only very mild relaxation)
RISK_PER_TRADE = 0.007  # 0.7% (was 0.6%) – still conservative
MAX_OPEN_POSITIONS = 1
MAX_PORTFOLIO_HEAT = 0.48  # slight increase from 0.45
DAILY_LOSS_LIMIT = 0.025  # 2.5% kept (strong daily protection)
WEEKLY_LOSS_LIMIT = 0.055
MAX_DRAWDOWN = 0.12
CONSECUTIVE_LOSS_PAUSE = 2
TRADE_COOLDOWN_MINUTES = 15
CONSECUTIVE_LOSS_COOLDOWN_MINUTES = 60
# Crypto trades 24/7.
# Trading day resets at 00:00 UTC.
TRADING_DAY_RESET_HOUR_UTC = 0

# ====================== TRADE LIFECYCLE ======================
# Only one position may exist at a time.
# New trade scanning starts only after the previous position is closed.
SINGLE_POSITION_MODE = True

# When an order is rejected because available balance is insufficient,
# stop trying to place another order until the next valid trading state.
STOP_ON_INSUFFICIENT_BALANCE = True


# ====================== TRADING PAIRS (Crypto.com format) ======================
PAIRS = ["CRO/USDT", "EGLD/USDT"]
# PAIRS = ["CRO/USDT", "SOL/USDT", "EGLD/USDT"]
# PAIRS = ["SPCXUSD-PERP"]

# Timeframes
SIGNAL_TIMEFRAME = "1h"
HIGHER_TIMEFRAME = "1d"

# ====================== STRATEGY PARAMETERS ======================
# More trades while keeping quality
MIN_QUALITY_SCORE = 78  # lowered from 72 → more setups
MIN_RR = 1.8  # lowered from 1.6 → more valid R:R opportunities
ATR_PERIOD = 14
RSI_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 50

# Fees (Crypto.com approximate base rates)
MAKER_FEE = 0.0025
TAKER_FEE = 0.0050
SLIPPAGE = 0.0008

# Loop settings
LOOP_SLEEP_SECONDS = 45

# ====================== INTELLIGENT FILTERS ======================
ENABLE_SESSION_FILTER = True
# High volume sessions (UTC)
SESSION_START_UTC = 7
SESSION_END_UTC = 21

ENABLE_VOLATILITY_PROTECTION = True
MAX_ATR_MULTIPLIER = 2.3  # relaxed from 2.1 → allows a bit more volatility

ENABLE_NEWS_PROTECTION = True
AVOID_FIRST_MINUTES = 20  # slightly less restrictive (was 25)

# ====================== ADVANCED RISK & PROFIT ======================
ENABLE_ADAPTIVE_SIZING = True
ENABLE_PARTIAL_TP = True
ENABLE_DYNAMIC_SCORE = True

# Adaptive sizing – starts a bit earlier so more trades get reasonable size
FULL_SIZE_SCORE = 85  # was 88
MEDIUM_SIZE_SCORE = 75  # was 78
MEDIUM_SIZE_MULTIPLIER = 0.65  # slightly higher than 0.60

# Partial Take Profit
PARTIAL_TP1_R = 1.4  # slightly earlier first partial
PARTIAL_TP2_R = 2.4

# Dynamic Score (Win-rate based)
RECENT_TRADES_WINDOW = 12
MIN_WINRATE_TO_LOWER = 0.53  # slightly more forgiving
LOW_WINRATE_THRESHOLD = 0.40
DYNAMIC_SCORE_BOOST = 5  # milder boost than 6
