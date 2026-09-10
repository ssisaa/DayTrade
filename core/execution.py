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

        # ---------- PAPER MODE ----------
        if MODE == "PAPER":
            logger.info(
                f"[PAPER] {setup['side'].upper()} {setup['pair']} | "
                f"Size: ${size_usdt:.2f} | Score: {setup.get('score', 0)}"
            )
            return True

        # ---------- LIVE MODE ----------
        try:
            # Safety: Check available balance
            balance = self.exchange.fetch_balance()
            
            free = 0
            if 'USDT' in balance and balance['USDT'].get('free'):
                free = float(balance['USDT']['free'])
            elif 'USD' in balance and balance['USD'].get('free'):
                free = float(balance['USD']['free'])

            if free < size_usdt * 0.6:
                logger.error(f"Insufficient balance. Free: ${free:.2f} | Required approx: ${size_usdt:.2f}")
                return False

            symbol = setup['pair']
            side = setup['side']          # 'buy' or 'sell'
            price = setup['entry']
            amount = size_usdt / price    # Approximate quantity

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

            order_id = order.get('id', 'unknown')
            logger.info(f"[LIVE] Order placed successfully | ID: {order_id} | {side.upper()} {symbol}")
            return True

        except Exception as e:
            logger.error(f"Order failed: {e}")
            return False
