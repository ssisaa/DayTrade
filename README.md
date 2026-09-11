**README.md**

```markdown
# VeteranSR-Agent
### Intelligent Crypto Daily Trading Bot for Crypto.com

A risk-focused algorithmic trading bot designed for **daily trading** on Crypto.com Exchange.  
It supports both **Spot** and **Perpetual** markets, uses dynamic pair selection, news filtering, and strict risk management.

---

## Key Features

- One position at a time (prevents overtrading)
- Dynamic pair selection (chooses best pairs every cycle)
- News-aware decision making
- Support & Resistance based setups
- Multi-timeframe confirmation
- Adaptive position sizing
- Partial Take Profit + Break-even + Trailing Stop
- Paper trading mode (safe testing)
- Easy switch between Spot and Perpetual

---

## Project Structure

```
Tradexx/
├── main.py
├── config.py
├── data/
│   └── data_feed.py
├── core/
│   ├── indicators.py
│   ├── regime.py
│   ├── setup_scanner.py
│   ├── smart_filters.py
│   ├── news_filter.py
│   ├── pair_decision.py
│   ├── risk_engine.py
│   ├── execution.py
│   ├── position_manager.py
│   └── performance.py
├── utils/
│   ├── logger.py
│   ├── helpers.py
│   ├── daily_report.py
│   ├── telegram_alert.py
│   └── setup_logger.py
└── logs/
```

---

## How the Bot Works (Simple Explanation)

1. Checks if any position is already open
2. If a position is open → only manages it (Stop Loss / Take Profit / Trailing)
3. If no position is open:
   - Re-evaluates the market
   - Selects the best 1–2 pairs based on news + strength
   - Scans those pairs for high-quality setups
   - Places maximum **1 trade**
4. After the trade closes → decides again

This makes the bot behave more like a disciplined daily trader.

---

## Quick Start Guide

### 1. Install Requirements

```bash
pip install ccxt pandas numpy requests
```

### 2. Configure the Bot

Open `config.py` and set:

```python
MODE = "PAPER"              # Start with PAPER (very important)
TRADING_MODE = "SPOT"       # or "PERP"
```

Add your API keys only when ready for LIVE:

```python
API_KEY = "your_key"
API_SECRET = "your_secret"
```

### 3. Run the Bot

```bash
python main.py
```

---

## Important Settings

| Setting | Recommended | Description |
|--------|-------------|-------------|
| `MODE` | `"PAPER"` | Use Paper first |
| `TRADING_MODE` | `"SPOT"` | Safer than Perpetual |
| `MAX_OPEN_POSITIONS` | `1` | Only one trade at a time |
| `RISK_PER_TRADE` | `0.003 – 0.004` | 0.3% – 0.4% risk |
| `MIN_QUALITY_SCORE` | `78 – 82` | Higher = more selective |

---

## Switching Between Spot and Perpetual

In `config.py`:

```python
TRADING_MODE = "SPOT"   # Safer
```

or

```python
TRADING_MODE = "PERP"   # Higher risk
```

The bot will automatically adjust pairs and settings.

---

## Safety Features

- Maximum 1 open position
- Daily loss limit
- Maximum drawdown protection
- Consecutive loss pause
- News filter (blocks dangerous news)
- Volatility (Chaos) protection
- Adaptive position sizing

---

## Recommended Usage Flow

1. Run in **PAPER** mode for at least 7–14 days
2. Review results (win rate, drawdown, number of trades)
3. If results are acceptable, switch to **LIVE** with small capital
4. Keep risk very low in the beginning
5. Monitor the bot daily

---

## Risk Warning

- This bot does **not** guarantee profits
- Crypto trading involves significant risk
- You can lose money
- Never use money you cannot afford to lose
- Past performance does not guarantee future results

---

## Goal of This System

Priority order:

1. Capital Preservation  
2. Risk Management  
3. Positive Expectancy  
4. Consistent Profitability  
5. Scalability  

The bot is designed to take fewer but higher-quality trades rather than trading frequently.

---

## Support

If you face errors:

1. Make sure all files are updated
2. Check that `MODE = "PAPER"` while testing
3. Read the console logs carefully
4. Ensure your API key has **no withdrawal** permission

---

**Trade carefully. Protect your capital first.**
```

---

You can save this as `README.md` in your project folder.
