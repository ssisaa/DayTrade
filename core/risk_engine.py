from config import (
    RISK_PER_TRADE,
    MAX_OPEN_POSITIONS,
    MAX_PORTFOLIO_HEAT,
    DAILY_LOSS_LIMIT,
    WEEKLY_LOSS_LIMIT,
    MAX_DRAWDOWN,
    CONSECUTIVE_LOSS_PAUSE,
    ENABLE_ADAPTIVE_SIZING,
    FULL_SIZE_SCORE,
    MEDIUM_SIZE_SCORE,
    MEDIUM_SIZE_MULTIPLIER
)
from utils.logger import logger

class RiskEngine:
    def __init__(self, starting_equity):
        self.equity = float(starting_equity)
        self.peak_equity = float(starting_equity)
        self.starting_equity = float(starting_equity)
        
        self.open_positions = []
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.consecutive_losses = 0
        self.paused = False

        logger.info(f"RiskEngine initialized | Equity: ${self.equity:.2f}")

    def can_open_trade(self):
        """Main risk check before opening any new trade"""
        if self.paused:
            return False

        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return False

        # Daily loss limit
        if self.daily_pnl <= -abs(DAILY_LOSS_LIMIT) * self.equity:
            self.paused = True
            logger.warning("Daily loss limit reached - Trading paused")
            return False

        # Max drawdown
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - self.equity) / self.peak_equity
            if drawdown >= MAX_DRAWDOWN:
                self.paused = True
                logger.warning(f"Max drawdown reached ({drawdown*100:.2f}%) - Trading paused")
                return False

        # Consecutive losses protection
        if self.consecutive_losses >= CONSECUTIVE_LOSS_PAUSE:
            logger.warning(f"Consecutive losses ({self.consecutive_losses}) - Temporary pause")
            return False

        return True

    def calculate_size(self, entry, stop):
        """Basic position size calculation"""
        if entry <= 0 or stop <= 0:
            return 0.0

        risk_amount = self.equity * RISK_PER_TRADE
        stop_distance = abs(entry - stop) / entry

        if stop_distance <= 0:
            return 0.0

        size = risk_amount / stop_distance

        # Apply portfolio heat limit
        max_size = self.equity * MAX_PORTFOLIO_HEAT
        size = min(size, max_size)

        return round(size, 2)

    def calculate_adaptive_size(self, entry, stop, score):
        """Adaptive sizing based on setup quality score"""
        base_size = self.calculate_size(entry, stop)

        if not ENABLE_ADAPTIVE_SIZING:
            return base_size

        if score >= FULL_SIZE_SCORE:
            return base_size
        elif score >= MEDIUM_SIZE_SCORE:
            return round(base_size * MEDIUM_SIZE_MULTIPLIER, 2)
        else:
            # Very low score → much smaller size
            return round(base_size * 0.40, 2)

    def update_equity(self, new_equity):
        """Update equity and peak equity"""
        self.equity = float(new_equity)
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

    def reset_daily_pnl(self):
        """Call this at the start of a new day"""
        self.daily_pnl = 0.0

    def add_pnl(self, pnl):
        """Add realized PnL"""
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        self.equity += pnl
        self.update_equity(self.equity)

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def get_status(self):
        """Return current risk status for logging"""
        drawdown = 0.0
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - self.equity) / self.peak_equity * 100

        return {
            "equity": round(self.equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "drawdown_pct": round(drawdown, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "open_positions": len(self.open_positions),
            "consecutive_losses": self.consecutive_losses,
            "paused": self.paused
        }
