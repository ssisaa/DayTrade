from config import *


class RiskEngine:
    def __init__(self, starting_equity):
        self.equity = starting_equity
        self.peak_equity = starting_equity
        self.open_positions = []
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.paused = False

    def can_open_trade(self):
        if self.paused:
            return False
        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return False
        if self.daily_pnl <= -DAILY_LOSS_LIMIT * self.equity:
            self.paused = True
            return False
        drawdown = (self.peak_equity - self.equity) / self.peak_equity
        if drawdown >= MAX_DRAWDOWN:
            self.paused = True
            return False
        return True

    def calculate_size(self, entry, stop):
        risk_amount = self.equity * RISK_PER_TRADE
        stop_distance = abs(entry - stop) / entry
        if stop_distance == 0:
            return 0
        size = risk_amount / stop_distance
        max_size = self.equity * MAX_PORTFOLIO_HEAT
        return min(size, max_size)

    def update_equity(self, new_equity):
        self.equity = new_equity
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity

    def calculate_adaptive_size(self, entry, stop, score):
        """Reduce size on medium-quality setups"""
        from config import ENABLE_ADAPTIVE_SIZING, FULL_SIZE_SCORE, MEDIUM_SIZE_SCORE, MEDIUM_SIZE_MULTIPLIER

        base_size = self.calculate_size(entry, stop)

        if not ENABLE_ADAPTIVE_SIZING:
            return base_size

        if score >= FULL_SIZE_SCORE:
            return base_size
        elif score >= MEDIUM_SIZE_SCORE:
            return base_size * MEDIUM_SIZE_MULTIPLIER
        else:
            return base_size * 0.4  # very small size (should rarely happen)
