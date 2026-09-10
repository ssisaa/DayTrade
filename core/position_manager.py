import time
from config import MODE, ENABLE_PARTIAL_TP, PARTIAL_TP1_R, PARTIAL_TP2_R
from utils.logger import logger

class PositionManager:
    def __init__(self, execution, risk_engine, data_feed):
        self.execution = execution
        self.risk = risk_engine
        self.feed = data_feed
        self.open_trades = []

    def add_trade(self, setup, size_usdt):
        """Add a new trade (only called when no position is open)"""
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
            "score": setup.get("score", 0),
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
            f"Position opened -> {trade['id']} | "
            f"{trade['side'].upper()} {trade['pair']} | Size ${size_usdt:.2f}"
        )

        try:
            from utils.telegram_alert import alert_trade_opened
            alert_trade_opened(trade)
        except:
            pass

    def manage_open_positions(self):
        """Check and manage all open positions (SL, TP, Break-even, Trailing, Partial)"""
        if not self.open_trades:
            return

        still_open = []

        for trade in self.open_trades:
            try:
                df = self.feed.get_ohlcv(trade["pair"], "1m", limit=5)
                if df is None or len(df) == 0:
                    still_open.append(trade)
                    continue

                current_price = float(df["close"].iloc[-1])

                # Calculate current R multiple
                if trade["side"] == "buy":
                    current_r = (current_price - trade["entry"]) / trade["risk_distance"]
                else:
                    current_r = (trade["entry"] - current_price) / trade["risk_distance"]

                # ---------- BREAK-EVEN ----------
                if not trade["breakeven_activated"] and current_r >= 1.0:
                    if trade["side"] == "buy":
                        trade["stop"] = trade["entry"] + (trade["risk_distance"] * 0.12)
                    else:
                        trade["stop"] = trade["entry"] - (trade["risk_distance"] * 0.12)
                    
                    trade["breakeven_activated"] = True
                    logger.info(f"Break-Even activated -> {trade['id']} | New stop: {trade['stop']:.4f}")

                # ---------- TRAILING STOP ----------
                if current_r >= 1.8:
                    trade["trailing_activated"] = True
                    trail_distance = trade["risk_distance"] * 0.7

                    if trade["side"] == "buy":
                        new_stop = current_price - trail_distance
                        if new_stop > trade["stop"]:
                            trade["stop"] = new_stop
                    else:
                        new_stop = current_price + trail_distance
                        if new_stop < trade["stop"]:
                            trade["stop"] = new_stop

                # ---------- PARTIAL TAKE PROFIT ----------
                if ENABLE_PARTIAL_TP:
                    # TP1 - Close 50% at 1.5R
                    if not trade["tp1_hit"] and current_r >= PARTIAL_TP1_R:
                        close_size = trade["remaining_size"] * 0.50
                        self._partial_close(trade, current_price, close_size, "PARTIAL TP1 (1.5R)")
                        trade["tp1_hit"] = True
                        trade["remaining_size"] -= close_size

                    # TP2 - Close another 30% at 2.5R
                    if trade["tp1_hit"] and not trade["tp2_hit"] and current_r >= PARTIAL_TP2_R:
                        close_size = trade["size"] * 0.30
                        if close_size > trade["remaining_size"]:
                            close_size = trade["remaining_size"]
                        self._partial_close(trade, current_price, close_size, "PARTIAL TP2 (2.5R)")
                        trade["tp2_hit"] = True
                        trade["remaining_size"] -= close_size

                # ---------- FULL EXIT CHECK ----------
                closed = False
                exit_price = None
                reason = ""

                if trade["remaining_size"] <= 0.01:
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
                    else:  # sell / short
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

            except Exception as e:
                logger.error(f"Error managing trade {trade.get('id')}: {e}")
                still_open.append(trade)

        self.open_trades = still_open
        self.risk.open_positions = still_open

    def _partial_close(self, trade, price, size, reason):
        if size <= 0:
            return

        if trade["side"] == "buy":
            pnl_pct = (price - trade["entry"]) / trade["entry"]
        else:
            pnl_pct = (trade["entry"] - price) / trade["entry"]

        pnl_usdt = size * pnl_pct
        self.risk.equity += pnl_usdt
        self.risk.update_equity(self.risk.equity)

        logger.info(f"{reason} | {trade['pair']} | Closed ${size:.2f} | PnL ${pnl_usdt:.2f}")

        try:
            from core.performance import performance_tracker
            partial_trade = trade.copy()
            partial_trade["size"] = size
            performance_tracker.record_trade(partial_trade, price, pnl_usdt, reason)
        except:
            pass

    def _close_trade(self, trade, exit_price, reason):
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

        if pnl_usdt < 0:
            self.risk.consecutive_losses += 1
        else:
            self.risk.consecutive_losses = 0

        logger.info(
            f"CLOSED {reason} | {trade['pair']} | {trade['side'].upper()} | "
            f"PnL: ${pnl_usdt:.2f} | Equity: ${self.risk.equity:.2f}"
        )

        try:
            from utils.telegram_alert import alert_trade_closed
            alert_trade_closed(trade, exit_price, pnl_usdt, reason)
        except:
            pass

        try:
            from core.performance import performance_tracker
            trade_copy = trade.copy()
            trade_copy["size"] = size
            performance_tracker.record_trade(trade_copy, exit_price, pnl_usdt, reason)
        except:
            pass
