from config import MODE
from utils.logger import logger


class Execution:
    def __init__(self, exchange):
        self.exchange = exchange
        self.paper_positions = []

    def place_order(self, setup, size_usdt):
        if MODE == "PAPER":
            logger.info(
                f"[PAPER] {setup['side'].upper()} {setup['pair']} | Size: ${size_usdt:.2f} | Score: {setup['score']}")
            self.paper_positions.append({
                **setup,
                "size": size_usdt,
                "status": "open"
            })
            return True
        else:
            # LIVE order code (use with extreme caution)
            try:
                side = setup['side']
                symbol = setup['pair']
                amount = size_usdt / setup['entry']
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=side,
                    amount=amount,
                    price=setup['entry']
                )
                logger.info(f"[LIVE] Order placed: {order['id']}")
                return True
            except Exception as e:
                logger.error(f"Order failed: {e}")
                return False
