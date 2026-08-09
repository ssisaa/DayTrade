# core/performance.py
import csv
import os
from datetime import datetime
from utils.logger import logger
from config import RECENT_TRADES_WINDOW


class PerformanceTracker:
    def __init__(self, starting_equity):
        self.starting_equity = starting_equity
        self.equity = starting_equity
        self.trades = []
        self.recent_results = []  # True = win, False = loss

        os.makedirs("logs", exist_ok=True)

        self.trades_file = "logs/trades.csv"
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "pair", "side", "entry", "exit", "size",
                    "pnl_usdt", "pnl_pct", "reason", "score", "equity_after"
                ])

        self.equity_file = "logs/equity_curve.csv"
        if not os.path.exists(self.equity_file):
            with open(self.equity_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "equity"])

        self._log_equity(starting_equity)

    def record_trade(self, trade, exit_price, pnl_usdt, reason):
        pnl_pct = pnl_usdt / trade["size"] * 100
        self.equity += pnl_usdt

        is_win = pnl_usdt > 0
        self.recent_results.append(is_win)
        if len(self.recent_results) > RECENT_TRADES_WINDOW:
            self.recent_results.pop(0)

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            trade["pair"],
            trade["side"],
            round(trade["entry"], 4),
            round(exit_price, 4),
            round(trade["size"], 2),
            round(pnl_usdt, 2),
            round(pnl_pct, 2),
            reason,
            trade.get("score", 0),
            round(self.equity, 2)
        ]

        with open(self.trades_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        self._log_equity(self.equity)
        self.trades.append(row)
        logger.info(f"Trade recorded → Equity now ${self.equity:.2f}")

    def get_recent_winrate(self):
        if len(self.recent_results) < 5:
            return 0.50  # neutral until enough data
        wins = sum(1 for r in self.recent_results if r)
        return wins / len(self.recent_results)

    def get_dynamic_min_score(self, base_score):
        from config import ENABLE_DYNAMIC_SCORE, LOW_WINRATE_THRESHOLD, DYNAMIC_SCORE_BOOST
        if not ENABLE_DYNAMIC_SCORE:
            return base_score

        wr = self.get_recent_winrate()
        if wr < LOW_WINRATE_THRESHOLD:
            return base_score + DYNAMIC_SCORE_BOOST
        return base_score

    def _log_equity(self, equity):
        with open(self.equity_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), round(equity, 2)])

    def get_stats(self):
        try:
            if not self.trades:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "net_pnl": 0.0,
                    "current_equity": round(self.equity, 2),
                    "return_pct": 0.0,
                    "recent_winrate": 50.0
                }

            wins = sum(1 for t in self.trades if float(t[6]) > 0)
            total = len(self.trades)
            net_pnl = self.equity - self.starting_equity
            return_pct = (net_pnl / self.starting_equity * 100) if self.starting_equity > 0 else 0.0

            return {
                "total_trades": total,
                "wins": wins,
                "losses": total - wins,
                "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
                "net_pnl": round(net_pnl, 2),
                "current_equity": round(self.equity, 2),
                "return_pct": round(return_pct, 2),
                "recent_winrate": round(self.get_recent_winrate() * 100, 1)
            }
        except Exception as e:
            print(f"Error in get_stats: {e}")
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "net_pnl": 0.0,
                "current_equity": round(getattr(self, 'equity', 0), 2),
                "return_pct": 0.0,
                "recent_winrate": 0.0
            }


performance_tracker = None


def init_performance(starting_equity):
    global performance_tracker
    performance_tracker = PerformanceTracker(starting_equity)
    return performance_tracker
