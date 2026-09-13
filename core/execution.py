# core/execution.py
from config import MODE, TRADING_MODE, LEVERAGE
from utils.logger import logger

class Execution:
    def __init__(self, exchange):
        self.exchange = exchange

    def place_order(self, setup, size_usdt):
        """
        Place order in PAPER or LIVE mode.
        Returns True if successful, False otherwise.
        """
        if MODE == "PAPER":
            logger.info(
                f"[PAPER] {setup['side'].upper()} {setup['pair']} | "
                f"Size: ${size_usdt:.2f} | Score: {setup.get('score', 0)}"
            )
            return True

        # ---------- LIVE MODE ----------
        try:
            balance = self.exchange.fetch_balance()

            free = 0
            if 'USDT' in balance and balance['USDT'].get('free'):
                free = float(balance['USDT']['free'])
            elif 'USD' in balance and balance['USD'].get('free'):
                free = float(balance['USD']['free'])

            if free < size_usdt * 0.6:
                logger.error(f"Insufficient balance. Free: ${free:.2f}")
                return False

            symbol = setup['pair']
            side = setup['side']
            price = setup['entry']
            amount = size_usdt / price

            params = {}
            if TRADING_MODE == "PERP":
                params['leverage'] = LEVERAGE

            order = self.exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=amount,
                price=price,
                params=params
            )

            logger.info(f"[LIVE] Order placed | ID: {order.get('id')} | {side.upper()} {symbol}")
            return True

        except Exception as e:
            logger.error(f"Order failed: {e}")
            return False

    def close_position(self, trade, exit_price=None):
    """
    Close an open position (PAPER or LIVE)
    Fixed for Spot balance issues
    """
    if MODE == "PAPER":
        logger.info(f"[PAPER] Closing {trade['side'].upper()} {trade['pair']}")
        return True

    try:
        symbol = trade["pair"]
        side = "sell" if trade["side"] == "buy" else "buy"

        # ---------- Get actual free balance of base currency ----------
        base_currency = symbol.split('/')[0]   # e.g. DOT from DOT/USDT
        balance = self.exchange.fetch_balance()

        free_amount = 0.0
        if base_currency in balance and balance[base_currency].get('free') is not None:
            free_amount = float(balance[base_currency]['free'])

        if free_amount <= 0:
            logger.error(f"No free {base_currency} balance to close position")
            return False

        # Use almost all free balance (leave tiny buffer for rounding)
        amount = free_amount * 0.995

        # Safety minimum
        if amount <= 0:
            logger.error(f"Calculated close amount too small: {amount}")
            return False

        params = {}
        if TRADING_MODE == "PERP":
            params["reduceOnly"] = True

        order = self.exchange.create_order(
            symbol=symbol,
            type="market",
            side=side,
            amount=amount,
            params=params
        )

        logger.info(
            f"[LIVE] Position CLOSED | {symbol} | {side.upper()} | "
            f"Amount: {amount:.6f} | Order ID: {order.get('id')}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to close position: {e}")
        return False
