# core/risk_engine.py

from config import *
from datetime import datetime, timezone, timedelta


class RiskEngine:
    """
    Day-Trading Risk Engine

    Primary objectives:
        1. Preserve capital
        2. Limit losses
        3. Allow only one live position
        4. Enforce daily loss protection
        5. Enforce consecutive-loss protection
        6. Enforce maximum drawdown
        7. Enforce trade cooldown
        8. Calculate position size from actual stop risk
    """

    def __init__(self, starting_equity):

        # =====================================================
        # ACCOUNT STATE
        # =====================================================
        self.equity = float(starting_equity)
        self.peak_equity = float(starting_equity)
        # Equity at beginning of current trading day
        self.day_start_equity = float(starting_equity)
        self.daily_pnl = 0.0

        # =====================================================
        # POSITION STATE
        # =====================================================
        self.open_positions = []

        # =====================================================
        # LOSS CONTROL
        # =====================================================
        self.consecutive_losses = 0
        self.paused = False
        self.pause_reason = None

        # =====================================================
        # COOLDOWN
        # =====================================================
        self.cooldown_until = None
        # Consecutive-loss recovery cooldown
        self.consecutive_loss_pause_until = None

        # =====================================================
        # DAY TRACKING
        # =====================================================
        self.current_trading_day = self._get_trading_day()

        # =====================================================
        # STATISTICS
        # =====================================================
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        print(
            f"[RISK] Initialized | "
            f"Equity=${self.equity:.2f} | "
            f"Risk/Trade={RISK_PER_TRADE * 100:.2f}% | "
            f"Max DD={MAX_DRAWDOWN * 100:.2f}%"
        )

    def _get_trading_day(self):
        """
        Returns the current trading-day identifier based on UTC.

        Example:
            TRADING_DAY_RESET_HOUR_UTC = 0

            2026-08-09 23:59 UTC
                -> Trading day = 2026-08-09

            2026-08-10 00:00 UTC
                -> Trading day = 2026-08-10
        """

        now_utc = datetime.now(timezone.utc)

        reset_hour = TRADING_DAY_RESET_HOUR_UTC

        if now_utc.hour < reset_hour:

            trading_day = (
                    now_utc -
                    timedelta(days=1)
            ).date()

        else:

            trading_day = now_utc.date()

        return trading_day

    # =========================================================
    # DAY RESET
    # =========================================================

    def _check_new_day(self):

        trading_day = self._get_trading_day()
        if trading_day == self.current_trading_day:
            return

        # =====================================================
        # NEW UTC TRADING DAY
        # =====================================================
        previous_day = self.current_trading_day
        self.current_trading_day = trading_day
        # New day's starting equity
        self.day_start_equity = self.equity
        # Reset daily P&L
        self.daily_pnl = 0.0
        # Reset consecutive losses
        self.consecutive_losses = 0
        # Clear temporary pauses
        self.consecutive_loss_pause_until = None
        self.cooldown_until = None

        # Clear daily pause
        #
        # IMPORTANT:
        # Only the daily pause should automatically
        # clear at the new trading day.
        #
        # If there is some future permanent safety
        # lock, handle it separately.
        self.paused = False
        self.pause_reason = None
        print(
            f"[RISK] New UTC trading day | "
            f"{previous_day} → {trading_day} | "
            f"Start Equity=${self.equity:.2f}"
        )

    # =========================================================
    # DAILY P&L
    # =========================================================

    def update_daily_pnl(self):

        self.daily_pnl = (
                self.equity - self.day_start_equity
        )

        return self.daily_pnl

    # =========================================================
    # DAILY LOSS LIMIT
    # =========================================================

    def daily_loss_limit_amount(self):

        return (
                self.day_start_equity *
                DAILY_LOSS_LIMIT
        )

    def daily_loss_percentage(self):

        if self.day_start_equity <= 0:
            return 1.0

        loss = self.day_start_equity - self.equity

        return max(
            0.0,
            loss / self.day_start_equity
        )

    # =========================================================
    # DRAWDOWN
    # =========================================================

    def get_drawdown(self):

        if self.peak_equity <= 0:
            return 1.0

        return (
                self.peak_equity - self.equity
        ) / self.peak_equity

    # =========================================================
    # COOLDOWN
    # =========================================================

    def start_cooldown(self, minutes=None):
        import time
        if minutes is None:
            minutes = TRADE_COOLDOWN_MINUTES
        new_until = (
                time.time() +
                minutes * 60
        )

        # Keep whichever cooldown is longer
        if (
                self.cooldown_until is None
                or new_until > self.cooldown_until
        ):
            self.cooldown_until = new_until
        print(
            f"[RISK] Trade cooldown | "
            f"{minutes} minutes"
        )

    def is_in_cooldown(self):

        if self.cooldown_until is None:
            return False

        import time

        if time.time() >= self.cooldown_until:
            self.cooldown_until = None

            print(
                "[RISK] Cooldown completed"
            )

            return False

        return True

    def cooldown_remaining_seconds(self):

        if self.cooldown_until is None:
            return 0

        import time

        remaining = (
                self.cooldown_until -
                time.time()
        )

        return max(
            0,
            int(remaining)
        )

    # =========================================================
    # PAUSE
    # =========================================================

    def pause(self, reason):

        self.paused = True
        self.pause_reason = reason

        print(
            f"[RISK] TRADING PAUSED | "
            f"Reason: {reason}"
        )

    def resume(self):

        self.paused = False
        self.pause_reason = None

        print(
            "[RISK] Trading resumed"
        )

    # =========================================================
    # MAIN TRADE PERMISSION
    # =========================================================

    def can_open_trade(self):
        self._check_new_day()
        self.update_daily_pnl()

        # -----------------------------------------------------
        # 1. Manual/system pause
        # -----------------------------------------------------
        if self.paused:
            return False
        if self.is_consecutive_loss_paused():
            return False

        # -----------------------------------------------------
        # 2. Single-position protection
        # ----------------------------------------------------
        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return False

        # -----------------------------------------------------
        # 3. Cooldown protection
        # -----------------------------------------------------
        if self.is_in_cooldown():
            return False

        # -----------------------------------------------------
        # 4. Equity protection
        # -----------------------------------------------------
        if self.equity <= 0:
            self.pause(
                "Equity depleted"
            )
            return False

        # -----------------------------------------------------
        # 5. Daily loss limit
        # -----------------------------------------------------
        daily_loss_limit = (
                self.day_start_equity *
                DAILY_LOSS_LIMIT
        )

        if self.daily_pnl <= -daily_loss_limit:
            self.pause(
                f"Daily loss limit reached "
                f"(${abs(self.daily_pnl):.2f})"
            )
            return False

        # -----------------------------------------------------
        # 6. Maximum drawdown
        # -----------------------------------------------------
        drawdown = self.get_drawdown()
        if drawdown >= MAX_DRAWDOWN:
            self.pause(
                f"Maximum drawdown reached "
                f"({drawdown * 100:.2f}%)"
            )
            return False

        # -----------------------------------------------------
        # 7. Consecutive loss protection
        # -----------------------------------------------------
        if (
                self.consecutive_losses
                >= CONSECUTIVE_LOSS_PAUSE
        ):
            self.pause(
                f"Consecutive loss limit reached "
                f"({self.consecutive_losses})"
            )
            return False
        return True

    # =========================================================
    # POSITION SIZE
    # =========================================================

    def calculate_size(self, entry, stop):

        try:

            entry = float(entry)
            stop = float(stop)

        except (
                TypeError,
                ValueError
        ):

            return 0.0

        if entry <= 0 or stop <= 0:
            return 0.0

        # -----------------------------------------------------
        # Stop distance
        # -----------------------------------------------------

        stop_distance = abs(
            entry - stop
        )

        if stop_distance <= 0:
            return 0.0

        stop_distance_pct = (
                stop_distance / entry
        )

        # -----------------------------------------------------
        # Risk capital
        # -----------------------------------------------------

        risk_amount = (
                self.equity *
                RISK_PER_TRADE
        )

        # -----------------------------------------------------
        # Position size
        #
        # Example:
        #
        # Equity = $50
        # Risk = 0.5%
        # Risk amount = $0.25
        #
        # If stop distance = 2%
        #
        # Position size =
        # $0.25 / 0.02 = $12.50
        # -----------------------------------------------------

        size = (
                risk_amount /
                stop_distance_pct
        )

        # -----------------------------------------------------
        # Portfolio heat protection
        # -----------------------------------------------------

        max_size = (
                self.equity *
                MAX_PORTFOLIO_HEAT
        )

        size = min(
            size,
            max_size
        )

        # -----------------------------------------------------
        # Existing exposure
        # -----------------------------------------------------

        existing_exposure = 0.0

        for position in self.open_positions:

            try:

                existing_exposure += float(
                    position.get(
                        "remaining_size",
                        position.get("size", 0)
                    )
                )

            except (
                    TypeError,
                    ValueError
            ):

                continue

        available_heat = max(
            0.0,
            max_size -
            existing_exposure
        )

        size = min(
            size,
            available_heat
        )

        return max(
            0.0,
            size
        )

    # =========================================================
    # ADAPTIVE POSITION SIZE
    # =========================================================

    def calculate_adaptive_size(
            self,
            entry,
            stop,
            score
    ):

        base_size = self.calculate_size(
            entry,
            stop
        )

        if base_size <= 0:
            return 0.0

        if not ENABLE_ADAPTIVE_SIZING:
            return base_size

        # -----------------------------------------------------
        # A+ setup
        # -----------------------------------------------------

        if score >= FULL_SIZE_SCORE:

            multiplier = 1.0


        # -----------------------------------------------------
        # A setup
        # -----------------------------------------------------

        elif score >= MEDIUM_SIZE_SCORE:

            multiplier = MEDIUM_SIZE_MULTIPLIER


        # -----------------------------------------------------
        # Anything below medium quality
        #
        # Do NOT use tiny size to justify bad trades.
        # -----------------------------------------------------

        else:

            return 0.0

        return base_size * multiplier

    # =========================================================
    # EQUITY UPDATE
    # =========================================================

    def update_equity(self, new_equity):

        try:

            new_equity = float(new_equity)

        except (
                TypeError,
                ValueError
        ):

            return

        if new_equity < 0:
            new_equity = 0.0

        self.equity = new_equity

        # -----------------------------------------------------
        # Update peak equity
        # -----------------------------------------------------

        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        # -----------------------------------------------------
        # Update daily P&L
        # -----------------------------------------------------

        self.update_daily_pnl()

        # -----------------------------------------------------
        # Emergency equity protection
        # -----------------------------------------------------

        if self.equity <= 0:
            self.pause(
                "Equity reached zero"
            )

    # =========================================================
    # TRADE CLOSED
    # =========================================================

    def record_trade_result(self, pnl_usdt):
        try:
            pnl_usdt = float(pnl_usdt)
        except (TypeError, ValueError):
            return

        self.total_trades += 1
        # -----------------------------------------------------
        # WIN
        # -----------------------------------------------------
        if pnl_usdt > 0:
            self.winning_trades += 1
            # A profitable completed trade resets
            # consecutive-loss sequence.
            self.consecutive_losses = 0
            print(
                "[RISK] Winning trade | "
                "Consecutive losses reset"
            )

        # -----------------------------------------------------
        # LOSS
        # -----------------------------------------------------
        elif pnl_usdt < 0:
            self.losing_trades += 1
            self.consecutive_losses += 1
        print(
            f"[RISK] Trade closed | "
            f"PnL=${pnl_usdt:.4f} | "
            f"Daily P&L=${self.daily_pnl:.4f} | "
            f"Consecutive Losses="
            f"{self.consecutive_losses}"
        )
        # =====================================================
        # UPDATE DAILY P&L
        # =====================================================
        self.update_daily_pnl()

        # -----------------------------------------------------
        # Start cooldown after EVERY completed trade
        # -----------------------------------------------------
        self.start_cooldown()

        # -----------------------------------------------------
        # Daily loss protection
        # -----------------------------------------------------
        daily_loss_limit = (self.day_start_equity * DAILY_LOSS_LIMIT)
        if self.daily_pnl <= -daily_loss_limit:
            self.pause("Daily loss limit reached")
            return

        # =====================================================
        # MAXIMUM DRAWDOWN
        # =====================================================

        if self.get_drawdown() >= MAX_DRAWDOWN:
            self.pause("Maximum drawdown reached")
            return

        # -----------------------------------------------------
        # Consecutive loss protection
        # -----------------------------------------------------
        if (
                self.consecutive_losses
                >= CONSECUTIVE_LOSS_PAUSE
        ):
            self.start_consecutive_loss_pause()

    # =========================================================
    # POSITION REGISTRATION
    # =========================================================
    def register_position(self, trade):

        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return False

        self.open_positions.append(
            trade
        )

        return True

    # =========================================================
    # POSITION REMOVAL
    # =========================================================

    def remove_position(self, trade):

        if trade in self.open_positions:
            self.open_positions.remove(
                trade
            )

    # =========================================================
    # STATUS
    # =========================================================

    def get_status(self):

        self._check_new_day()
        self.update_daily_pnl()

        return {

            "equity":
                round(self.equity, 4),

            "peak_equity":
                round(self.peak_equity, 4),

            "day_start_equity":
                round(
                    self.day_start_equity,
                    4
                ),

            "daily_pnl":
                round(
                    self.daily_pnl,
                    4
                ),

            "daily_pnl_pct":
                round(
                    (
                            self.daily_pnl /
                            self.day_start_equity
                    ) * 100,
                    3
                )
                if self.day_start_equity > 0
                else 0,

            "drawdown_pct":
                round(
                    self.get_drawdown() * 100,
                    3
                ),

            "open_positions":
                len(self.open_positions),

            "consecutive_losses":
                self.consecutive_losses,

            "total_trades":
                self.total_trades,

            "winning_trades":
                self.winning_trades,

            "losing_trades":
                self.losing_trades,

            "paused":
                self.paused,

            "pause_reason":
                self.pause_reason,

            "cooldown_seconds":
                self.cooldown_remaining_seconds()
        }

    def start_consecutive_loss_pause(self):

        import time

        self.consecutive_loss_pause_until = (
                time.time()
                + CONSECUTIVE_LOSS_COOLDOWN_MINUTES * 60
        )

        print(
            f"[RISK] Consecutive-loss pause started | "
            f"{CONSECUTIVE_LOSS_COOLDOWN_MINUTES} minutes"
        )

    def is_consecutive_loss_paused(self):
        if self.consecutive_loss_pause_until is None:
            return False
        import time
        if time.time() >= self.consecutive_loss_pause_until:
            self.consecutive_loss_pause_until = None
            print(
                "[RISK] Consecutive-loss recovery complete | "
                "Trading may resume"
            )
            return False
        return True

    def consecutive_loss_pause_remaining_seconds(self):

        if self.consecutive_loss_pause_until is None:
            return 0

        import time

        return max(
            0,
            int(
                self.consecutive_loss_pause_until
                - time.time()
            )
        )
