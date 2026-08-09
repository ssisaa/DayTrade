# core/position_manager.py
from utils.logger import logger
from config import *
import time


class PositionManager:
    def __init__(self, execution, risk_engine, data_feed):
        self.execution = execution
        self.risk = risk_engine
        self.feed = data_feed
        self.open_trades = []

    def add_trade(self, setup, size_usdt):
        if SINGLE_POSITION_MODE and self.open_trades:
            logger.warning(
                f"Trade rejected internally - "
                f"position already open: "
                f"{self.open_trades[0]['id']}"
            )
            return False

        if len(self.open_trades) >= MAX_OPEN_POSITIONS:
            logger.warning(
                f"Maximum open positions reached: "
                f"{MAX_OPEN_POSITIONS}"
            )
            return False

        risk_distance = abs(setup["entry"] - setup["stop"])

        trade = {
            "id": f"{setup['pair']}_{int(time.time())}",
            "pair": setup["pair"],
            "side": setup["side"],
            "entry": setup["entry"],
            "stop": setup["stop"],
            "original_stop": setup["stop"],
            "target": setup["target"],
            "size": size_usdt,
            "remaining_size": size_usdt,
            "score": setup["score"],
            "status": "open",
            "entry_time": time.time(),
            "risk_distance": risk_distance,
            "breakeven_activated": False,
            "trailing_activated": False,
            "tp1_hit": False,
            "tp2_hit": False
        }
        self.open_trades.append(trade)
        self.risk.open_positions.append(trade)
        logger.info(
            f"Position opened | "
            f"{trade['id']} | "
            f"{trade['side'].upper()} "
            f"{trade['pair']} | "
            f"Size ${size_usdt:.2f}"
        )

        return True

    def manage_open_positions(self):
        if not self.open_trades:
            return

        still_open = []

        for trade in self.open_trades:
            df = self.feed.get_ohlcv(trade["pair"], "1m", limit=5)
            if df is None or len(df) == 0:
                still_open.append(trade)
                continue

            current_price = df["close"].iloc[-1]

            # Current R multiple
            if trade["side"] == "buy":
                current_r = (current_price - trade["entry"]) / trade["risk_distance"]
            else:
                current_r = (trade["entry"] - current_price) / trade["risk_distance"]

            # ----- BREAK-EVEN -----
            if not trade["breakeven_activated"] and current_r >= 1.0:
                if trade["side"] == "buy":
                    trade["stop"] = trade["entry"] + trade["risk_distance"] * 0.15
                else:
                    trade["stop"] = trade["entry"] - trade["risk_distance"] * 0.15
                trade["breakeven_activated"] = True
                logger.info(f"Break-Even activated → {trade['id']}")

            # ----- TRAILING -----
            if current_r >= 1.8:
                trade["trailing_activated"] = True
                trail = trade["risk_distance"] * 0.7
                if trade["side"] == "buy":
                    new_stop = current_price - trail
                    if new_stop > trade["stop"]:
                        trade["stop"] = new_stop
                else:
                    new_stop = current_price + trail
                    if new_stop < trade["stop"]:
                        trade["stop"] = new_stop

            # ----- PARTIAL TAKE PROFIT -----
            if ENABLE_PARTIAL_TP:
                # TP1 at 1.5R → close 50%
                if not trade["tp1_hit"] and current_r >= PARTIAL_TP1_R:
                    close_size = trade["remaining_size"] * 0.50
                    self._partial_close(trade, current_price, close_size, "PARTIAL TP1 (1.5R)")
                    trade["tp1_hit"] = True
                    trade["remaining_size"] -= close_size

                # TP2 at 2.5R → close another 30% of original
                if trade["tp1_hit"] and not trade["tp2_hit"] and current_r >= PARTIAL_TP2_R:
                    close_size = trade["size"] * 0.30
                    if close_size > trade["remaining_size"]:
                        close_size = trade["remaining_size"]
                    self._partial_close(trade, current_price, close_size, "PARTIAL TP2 (2.5R)")
                    trade["tp2_hit"] = True
                    trade["remaining_size"] -= close_size

            # ----- FULL EXIT -----
            closed = False
            exit_price = None
            reason = ""

            if trade["remaining_size"] <= 0:
                closed = True
                exit_price = current_price
                reason = "FULLY SCALED OUT"
            else:
                if trade["side"] == "buy":
                    if current_price <= trade["stop"]:
                        exit_price = trade["stop"]
                        reason = "STOP / TRAIL"
                        closed = True
                    elif current_price >= trade["target"]:
                        exit_price = trade["target"]
                        reason = "FINAL TAKE-PROFIT"
                        closed = True
                else:
                    if current_price >= trade["stop"]:
                        exit_price = trade["stop"]
                        reason = "STOP / TRAIL"
                        closed = True
                    elif current_price <= trade["target"]:
                        exit_price = trade["target"]
                        reason = "FINAL TAKE-PROFIT"
                        closed = True

            if closed:
                self._close_trade(trade, exit_price, reason)
            else:
                still_open.append(trade)

        self.open_trades = still_open
        self.risk.open_positions = still_open

    def _partial_close(self, trade, price, size, reason):
        if trade["side"] == "buy":
            pnl_pct = (price - trade["entry"]) / trade["entry"]
        else:
            pnl_pct = (trade["entry"] - price) / trade["entry"]

        pnl_usdt = size * pnl_pct
        self.risk.equity += pnl_usdt
        self.risk.update_equity(self.risk.equity)

        logger.info(f"{reason} | {trade['pair']} | Closed ${size:.2f} | PnL ${pnl_usdt:.2f}")

        from core.performance import performance_tracker
        # Record partial as a separate trade record
        partial_trade = trade.copy()
        partial_trade["size"] = size
        performance_tracker.record_trade(partial_trade, price, pnl_usdt, reason)

    def _close_trade_oldx(self, trade, exit_price, reason):
        size = trade["remaining_size"]
        if size <= 0:
            return

        if trade["side"] == "buy":
            pnl_pct = (exit_price - trade["entry"]) / trade["entry"]
        else:
            pnl_pct = (trade["entry"] - exit_price) / trade["entry"]

        pnl_usdt = size * pnl_pct
        self.risk.equity += pnl_usdt
        self.risk.update_equity(self.risk.equity)
        self.risk.record_trade_result(pnl_usdt)

        if pnl_usdt < 0:
            self.risk.consecutive_losses += 1
        else:
            self.risk.consecutive_losses = 0

        logger.info(f"CLOSED {reason} | {trade['pair']} | PnL ${pnl_usdt:.2f} | Equity ${self.risk.equity:.2f}")

        from core.performance import performance_tracker
        trade["size"] = size
        performance_tracker.record_trade(trade, exit_price, pnl_usdt, reason)

    def _close_trade(self, trade, exit_price, reason):

        size = trade["remaining_size"]

        if size <= 0:
            return

        if trade["side"] == "buy":
            pnl_pct = (
                              exit_price - trade["entry"]
                      ) / trade["entry"]

        else:
            pnl_pct = (
                              trade["entry"] - exit_price
                      ) / trade["entry"]

        pnl_usdt = size * pnl_pct

        # Update equity
        self.risk.equity += pnl_usdt
        self.risk.update_equity(
            self.risk.equity
        )

        # Record result in RiskEngine
        self.risk.record_trade_result(
            pnl_usdt
        )

        # Remove from risk engine
        self.risk.remove_position(
            trade
        )

        logger.info(
            f"CLOSED {reason} | "
            f"{trade['pair']} | "
            f"PnL ${pnl_usdt:.2f} | "
            f"Equity ${self.risk.equity:.2f}"
        )

        from core.performance import performance_tracker

        trade["size"] = size

        performance_tracker.record_trade(
            trade,
            exit_price,
            pnl_usdt,
            reason
        )
