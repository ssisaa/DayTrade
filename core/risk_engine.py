from config import *

from datetime import datetime, timezone, timedelta
import time


class RiskEngine:
    """
    Autonomous 24/7 crypto day-trading risk engine.

    Responsibilities:
        - Position-size calculation
        - Single-position enforcement
        - Daily loss protection
        - Maximum drawdown protection
        - Consecutive-loss recovery
        - Post-trade cooldown
        - UTC trading-day reset
        - Automatic recovery where safe

    Important:
        Temporary pauses recover automatically.
        Hard safety stops do NOT automatically recover.
    """

    def __init__(self, starting_equity):

        # =====================================================
        # ACCOUNT
        # =====================================================

        self.equity = float(starting_equity)

        self.peak_equity = float(starting_equity)

        # =====================================================
        # UTC TRADING DAY
        # =====================================================

        self.current_trading_day = self._get_trading_day()

        self.day_start_equity = float(starting_equity)

        self.daily_pnl = 0.0

        # =====================================================
        # POSITIONS
        # =====================================================

        self.open_positions = []

        # =====================================================
        # LOSS CONTROL
        # =====================================================

        self.consecutive_losses = 0

        # Temporary recovery pause
        self.consecutive_loss_pause_until = None

        # Daily safety pause
        self.daily_paused = False
        self.daily_pause_reason = None
        # Hard safety pause
        self.hard_paused = False
        self.hard_pause_reason = None

        # =====================================================
        # NORMAL COOLDOWN
        # =====================================================

        self.cooldown_until = None

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
            f"Daily Limit={DAILY_LOSS_LIMIT * 100:.2f}% | "
            f"Max DD={MAX_DRAWDOWN * 100:.2f}% | "
            f"Trading Day UTC={self.current_trading_day}"
        )

    # =========================================================
    # UTC TRADING DAY
    # =========================================================

    def _get_trading_day(self):
        """
        Returns the current trading-day identifier.

        Uses UTC, not machine local time.

        With:
            TRADING_DAY_RESET_HOUR_UTC = 0

        the trading day changes at:
            00:00 UTC
        """

        now_utc = datetime.now(timezone.utc)

        reset_hour = TRADING_DAY_RESET_HOUR_UTC

        if now_utc.hour < reset_hour:
            return (
                    now_utc -
                    timedelta(days=1)
            ).date()

        return now_utc.date()

    def _check_new_day(self):
        """
        Automatically starts a new UTC trading day.
        """

        trading_day = self._get_trading_day()

        if trading_day == self.current_trading_day:
            return

        previous_day = self.current_trading_day

        self.current_trading_day = trading_day

        # New daily baseline
        self.day_start_equity = self.equity

        # Reset daily statistics
        self.daily_pnl = 0.0

        # Reset consecutive loss sequence
        self.consecutive_losses = 0

        # Clear temporary cooldowns
        self.cooldown_until = None
        self.consecutive_loss_pause_until = None

        self.daily_paused = False
        self.daily_pause_reason = None

        self.hard_paused = False
        self.hard_pause_reason = None
        # -----------------------------------------------------
        # IMPORTANT
        #
        # A daily-loss pause may recover on a new UTC day.
        # A hard drawdown pause must NOT.
        # -----------------------------------------------------

        if not self.hard_paused:
            self.hard_pause_reason = None

        print(
            f"[RISK] NEW UTC TRADING DAY | "
            f"{previous_day} -> {trading_day} | "
            f"Start Equity=${self.equity:.2f}"
        )

    # =========================================================
    # DAILY P&L
    # =========================================================

    def update_daily_pnl(self):

        self.daily_pnl = (
                self.equity -
                self.day_start_equity
        )

        return self.daily_pnl

    def get_daily_loss_amount(self):

        return (
                self.day_start_equity *
                DAILY_LOSS_LIMIT
        )

    def get_daily_pnl_percentage(self):

        if self.day_start_equity <= 0:
            return 0.0

        return (
                self.daily_pnl /
                self.day_start_equity
        )

    # =========================================================
    # DRAW DOWN
    # =========================================================

    def get_drawdown(self):

        if self.peak_equity <= 0:
            return 1.0

        return max(
            0.0,
            (
                    self.peak_equity -
                    self.equity
            ) / self.peak_equity
        )

    # =========================================================
    # NORMAL COOLDOWN
    # =========================================================

    def start_cooldown(self, minutes=None):

        if minutes is None:
            minutes = TRADE_COOLDOWN_MINUTES

        new_until = (
                time.time() +
                minutes * 60
        )

        # Never shorten an existing cooldown
        if (
                self.cooldown_until is None
                or new_until > self.cooldown_until
        ):
            self.cooldown_until = new_until

        print(
            f"[RISK] Trade cooldown started | "
            f"{minutes} minutes"
        )

    def is_in_cooldown(self):

        if self.cooldown_until is None:
            return False

        if time.time() >= self.cooldown_until:
            self.cooldown_until = None

            print(
                "[RISK] Trade cooldown completed"
            )

            return False

        return True

    def cooldown_remaining_seconds(self):

        if self.cooldown_until is None:
            return 0

        return max(
            0,
            int(
                self.cooldown_until -
                time.time()
            )
        )

    # =========================================================
    # CONSECUTIVE LOSS RECOVERY
    # =========================================================

    def start_consecutive_loss_pause(self):

        self.consecutive_loss_pause_until = (
                time.time()
                +
                CONSECUTIVE_LOSS_COOLDOWN_MINUTES * 60
        )

        print(
            f"[RISK] CONSECUTIVE LOSS PAUSE | "
            f"{self.consecutive_losses} losses | "
            f"Recovery="
            f"{CONSECUTIVE_LOSS_COOLDOWN_MINUTES} minutes"
        )

    def is_consecutive_loss_paused(self):

        if self.consecutive_loss_pause_until is None:
            return False

        if time.time() >= self.consecutive_loss_pause_until:
            self.consecutive_loss_pause_until = None

            print(
                "[RISK] LOSS RECOVERY COMPLETE | "
                "Trading may resume"
            )

            return False

        return True

    def consecutive_loss_pause_remaining_seconds(self):

        if self.consecutive_loss_pause_until is None:
            return 0

        return max(
            0,
            int(
                self.consecutive_loss_pause_until -
                time.time()
            )
        )

    # =========================================================
    # HARD SAFETY STOP
    # =========================================================

    def hard_stop(self, reason):

        self.hard_paused = True
        self.hard_pause_reason = reason

        print(
            f"[RISK] !!! HARD SAFETY STOP !!! | "
            f"{reason}"
        )

    # =========================================================
    # MAIN TRADE PERMISSION
    # =========================================================

    def can_open_trade(self):

        # Always evaluate UTC day first
        self._check_new_day()

        # Recalculate daily P&L
        self.update_daily_pnl()

        # =====================================================
        # HARD SAFETY STOP
        # =====================================================

        if self.hard_paused:
            return False

        if self.daily_paused:
            return False

        # =====================================================
        # SINGLE POSITION
        # =====================================================

        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return False

        # =====================================================
        # NORMAL COOLDOWN
        # =====================================================

        if self.is_in_cooldown():
            return False

        # =====================================================
        # CONSECUTIVE LOSS RECOVERY
        # =====================================================

        if self.is_consecutive_loss_paused():
            return False

        # =====================================================
        # EQUITY PROTECTION
        # =====================================================

        if self.equity <= 0:
            self.hard_stop(
                "Equity depleted"
            )

            return False

        # =====================================================
        # DAILY LOSS LIMIT
        # =====================================================

        daily_loss_limit = (
                self.day_start_equity *
                DAILY_LOSS_LIMIT
        )

        if self.daily_pnl <= -daily_loss_limit:
            self.daily_paused = True
            self.daily_pause_reason = (
                f"Daily loss limit reached | "
                f"P&L=${self.daily_pnl:.4f}"
            )

            print(
                f"[RISK] DAILY PAUSE | "
                f"{self.daily_pause_reason} | "
                f"Resume at next 00:00 UTC"
            )

            return False

        # =====================================================
        # MAXIMUM DRAWDOWN
        # =====================================================

        drawdown = self.get_drawdown()

        if drawdown >= MAX_DRAWDOWN:
            self.hard_stop(
                f"Maximum drawdown reached | "
                f"DD={drawdown * 100:.2f}%"
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

        except (TypeError, ValueError):

            return 0.0

        if entry <= 0 or stop <= 0:
            return 0.0

        stop_distance = abs(
            entry - stop
        )

        if stop_distance <= 0:
            return 0.0

        stop_distance_pct = (
                stop_distance /
                entry
        )

        # =====================================================
        # MONEY AT RISK
        # =====================================================

        risk_amount = (
                self.equity *
                RISK_PER_TRADE
        )

        # =====================================================
        # POSITION NOTIONAL
        # =====================================================

        size = (
                risk_amount /
                stop_distance_pct
        )

        # =====================================================
        # MAX PORTFOLIO HEAT
        # =====================================================

        max_size = (
                self.equity *
                MAX_PORTFOLIO_HEAT
        )

        size = min(
            size,
            max_size
        )

        # =====================================================
        # EXISTING EXPOSURE
        # =====================================================

        existing_exposure = 0.0

        for position in self.open_positions:

            try:

                existing_exposure += float(
                    position.get(
                        "remaining_size",
                        position.get(
                            "size",
                            0
                        )
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
    # ADAPTIVE SIZE
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

        # A+ setup
        if score >= FULL_SIZE_SCORE:

            return base_size


        # A setup
        elif score >= MEDIUM_SIZE_SCORE:

            return (
                    base_size *
                    MEDIUM_SIZE_MULTIPLIER
            )


        # Below acceptable quality
        #
        # Do NOT trade a bad setup just
        # because the position is smaller.
        else:

            return 0.0

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

        self.equity = max(
            0.0,
            new_equity
        )

        # =====================================================
        # PEAK EQUITY
        # =====================================================

        if self.equity > self.peak_equity:
            self.peak_equity = self.equity

        # =====================================================
        # DAILY P&L
        # =====================================================

        self.update_daily_pnl()

        # =====================================================
        # ZERO EQUITY
        # =====================================================

        if self.equity <= 0:
            self.hard_stop(
                "Equity reached zero"
            )

    # =========================================================
    # TRADE COMPLETED
    # =========================================================

    def record_trade_result(self, pnl_usdt):

        try:

            pnl_usdt = float(pnl_usdt)

        except (
                TypeError,
                ValueError
        ):

            return

        self.total_trades += 1

        # =====================================================
        # WIN
        # =====================================================

        if pnl_usdt > 0:

            self.winning_trades += 1

            self.consecutive_losses = 0

            print(
                f"[RISK] WIN | "
                f"PnL=${pnl_usdt:.4f} | "
                f"Consecutive losses reset"
            )


        # =====================================================
        # LOSS
        # =====================================================

        elif pnl_usdt < 0:

            self.losing_trades += 1

            self.consecutive_losses += 1

            print(
                f"[RISK] LOSS | "
                f"PnL=${pnl_usdt:.4f} | "
                f"Consecutive losses="
                f"{self.consecutive_losses}"
            )

        # =====================================================
        # UPDATE DAILY P&L
        # =====================================================

        self.update_daily_pnl()

        # =====================================================
        # NORMAL COOLDOWN
        # =====================================================

        # Every COMPLETED position gets a normal cooldown.
        self.start_cooldown()

        # =====================================================
        # DAILY LOSS
        # =====================================================

        daily_loss_limit = (
                self.day_start_equity *
                DAILY_LOSS_LIMIT
        )

        if self.daily_pnl <= -daily_loss_limit:
            self.hard_stop(
                f"Daily loss limit reached | "
                f"P&L=${self.daily_pnl:.4f}"
            )

            return

        # =====================================================
        # MAXIMUM DRAWDOWN
        # =====================================================

        if self.get_drawdown() >= MAX_DRAWDOWN:
            self.hard_stop(
                f"Maximum drawdown reached | "
                f"DD={self.get_drawdown() * 100:.2f}%"
            )

            return

        # =====================================================
        # CONSECUTIVE LOSS RECOVERY
        # =====================================================

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
            print(
                "[RISK] Position registration rejected | "
                "Maximum open positions reached"
            )

            return False

        self.open_positions.append(trade)

        return True

    # =========================================================
    # POSITION REMOVAL
    # =========================================================

    def remove_position(self, trade):

        if trade in self.open_positions:
            self.open_positions.remove(trade)

    # =========================================================
    # STATUS
    # =========================================================

    def get_status(self):

        self._check_new_day()

        self.update_daily_pnl()

        return {

            "equity":
                round(
                    self.equity,
                    4
                ),

            "peak_equity":
                round(
                    self.peak_equity,
                    4
                ),

            "current_trading_day":
                str(
                    self.current_trading_day
                ),

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
                    self.get_daily_pnl_percentage() * 100,
                    3
                ),

            "drawdown_pct":
                round(
                    self.get_drawdown() * 100,
                    3
                ),

            "open_positions":
                len(
                    self.open_positions
                ),

            "consecutive_losses":
                self.consecutive_losses,

            "consecutive_loss_pause_seconds":
                self.consecutive_loss_pause_remaining_seconds(),

            "trade_cooldown_seconds":
                self.cooldown_remaining_seconds(),

            "total_trades":
                self.total_trades,

            "winning_trades":
                self.winning_trades,

            "losing_trades":
                self.losing_trades,

            "hard_paused":
                self.hard_paused,

            "hard_pause_reason":
                self.hard_pause_reason
        }
