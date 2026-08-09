# ============================================================
# EMERGENCY SAFE MAIN.PY - VeteranSR-Agent
# Heavy logging + safety checks for easy debugging
# ============================================================

import time
import traceback
from datetime import datetime
from config import *

print("\n" + "=" * 70)
print("LOADING MODULES...")
print("=" * 70)

# ----- Safe imports with clear error messages -----
try:
    from data.data_feed import DataFeed

    print("✓ data_feed imported")
except Exception as e:
    print(f"✗ FAILED to import data_feed: {e}")
    raise

try:
    from core.indicators import add_indicators

    print("✓ indicators imported")
except Exception as e:
    print(f"✗ FAILED to import indicators: {e}")
    raise

try:
    from core.regime import classify_regime

    print("✓ regime imported")
except Exception as e:
    print(f"✗ FAILED to import regime: {e}")
    raise

try:
    from core.setup_scanner import find_setups

    print("✓ setup_scanner imported")
except Exception as e:
    print(f"✗ FAILED to import setup_scanner: {e}")
    raise

try:
    from core.risk_engine import RiskEngine

    print("✓ risk_engine imported")
except Exception as e:
    print(f"✗ FAILED to import risk_engine: {e}")
    raise

try:
    from core.execution import Execution

    print("✓ execution imported")
except Exception as e:
    print(f"✗ FAILED to import execution: {e}")
    raise

try:
    from core.position_manager import PositionManager

    print("✓ position_manager imported")
except Exception as e:
    print(f"✗ FAILED to import position_manager: {e}")
    raise

try:
    from core.performance import init_performance

    print("✓ performance imported")
except Exception as e:
    print(f"✗ FAILED to import performance: {e}")
    raise

try:
    from utils.logger import logger

    print("✓ logger imported")
except Exception as e:
    print(f"✗ FAILED to import logger: {e}")
    raise

try:
    from utils.daily_report import generate_daily_report

    print("✓ daily_report imported")
except Exception as e:
    print(f"✗ FAILED to import daily_report: {e}")
    raise

print("=" * 70)
print("ALL MODULES LOADED SUCCESSFULLY")
print("=" * 70 + "\n")


def run_agent():
    print("\n" + "=" * 70)
    print("VETERAN SR-AGENT - EMERGENCY SAFE MODE")
    print(f"Mode          : {MODE}")
    print(f"Starting Equity: ${STARTING_EQUITY}")
    print(f"Pairs         : {PAIRS}")
    print(f"Min Quality   : {MIN_QUALITY_SCORE}")
    print("=" * 70 + "\n")

    logger.info("Emergency Safe Agent Started")

    # ----- Initialize components with safety -----
    try:
        print("Initializing DataFeed...")
        feed = DataFeed()
        print("✓ DataFeed ready")
    except Exception as e:
        print(f"✗ DataFeed failed: {e}")
        return

    try:
        print("Initializing RiskEngine...")
        risk = RiskEngine(STARTING_EQUITY)
        print("✓ RiskEngine ready")
    except Exception as e:
        print(f"✗ RiskEngine failed: {e}")
        return

    try:
        print("Initializing Execution...")
        execution = Execution(feed.exchange)
        print("✓ Execution ready")
    except Exception as e:
        print(f"✗ Execution failed: {e}")
        return

    try:
        print("Initializing PositionManager...")
        position_manager = PositionManager(execution, risk, feed)
        print("✓ PositionManager ready")
    except Exception as e:
        print(f"✗ PositionManager failed: {e}")
        return

    try:
        print("Initializing Performance Tracker...")
        performance = init_performance(STARTING_EQUITY)
        print("✓ Performance Tracker ready")
    except Exception as e:
        print(f"✗ Performance Tracker failed: {e}")
        return

    print("\n" + "=" * 70)
    print("AGENT IS NOW RUNNING - Press Ctrl+C to stop")
    print("=" * 70 + "\n")

    last_report_day = datetime.now().day
    cycle = 0

    while True:
        try:
            cycle += 1
            now = datetime.now().strftime("%H:%M:%S")

            print(f"\n{'=' * 60}")
            print(f"CYCLE {cycle} | {now} | Equity: ${risk.equity:.2f}")
            print(f"{'=' * 60}")

            # =====================================================
            # 1. MANAGE EXISTING POSITION
            # =====================================================

            print("→ Checking open positions for SL / TP / Partial / Trail...")

            try:
                position_manager.manage_open_positions()

                open_count = len(position_manager.open_trades)

                print(f"  Open positions: {open_count}")

            except Exception as e:
                print(f"  ✗ Error in position management: {e}")
                traceback.print_exc()

                # Safety: DO NOT open a new trade if position management failed
                print("  ⚠ Position state uncertain - skipping new trade")
                time.sleep(LOOP_SLEEP_SECONDS)
                continue

            # =====================================================
            # 2. SINGLE POSITION GATE
            # =====================================================

            if SINGLE_POSITION_MODE and position_manager.open_trades:
                trade = position_manager.open_trades[0]

                print(
                    f"  ⏳ Existing position still OPEN: "
                    f"{trade['side'].upper()} {trade['pair']} "
                    f"| Size ${trade['remaining_size']:.2f}"
                )

                print("  → No new trades will be scanned")
                print(f"→ Sleeping {LOOP_SLEEP_SECONDS} seconds...")

                time.sleep(LOOP_SLEEP_SECONDS)
                continue

            # =====================================================
            # 3. RISK CHECK
            # =====================================================

            print("→ Checking risk limits...")

            if not risk.can_open_trade():
                print("  ⚠️ RISK LIMIT REACHED - Agent paused")
                logger.warning("Risk limits reached - paused")

                time.sleep(90)
                continue

            print("  ✓ Risk OK - can open new trade")

            # =====================================================
            # 4. SCAN FOR ONE NEW TRADE
            # =====================================================

            trade_opened = False

            for pair in PAIRS:

                # -------------------------------------------------
                # Double safety check
                # -------------------------------------------------

                if position_manager.open_trades:
                    print(
                        "  → Position already exists. "
                        "Stopping pair scan."
                    )
                    break

                print(f"\n→ Scanning {pair} ...")

                # -------------------------------------------------
                # Fetch data
                # -------------------------------------------------

                try:

                    df_1h = feed.get_ohlcv(pair, "1h")
                    df_4h = feed.get_ohlcv(pair, "4h")
                    df_daily = feed.get_ohlcv(pair, "1d")

                except Exception as e:

                    print(f"  ✗ Data fetch error: {e}")
                    continue

                if df_1h is None or df_daily is None:
                    print(f"  ✗ No data received for {pair}")
                    continue

                print(
                    f"  ✓ Data received | "
                    f"1h candles: {len(df_1h)}"
                )

                # -------------------------------------------------
                # Regime
                # -------------------------------------------------

                try:

                    df_daily = add_indicators(df_daily)

                    regime = classify_regime(df_daily)

                    print(f"  → Regime: {regime}")

                except Exception as e:

                    print(f"  ✗ Regime error: {e}")
                    continue

                # -------------------------------------------------
                # Find setup
                # -------------------------------------------------

                try:

                    setups = find_setups(
                        df_1h,
                        df_4h,
                        regime,
                        pair
                    )

                except Exception as e:

                    print(f"  ✗ Setup scanner error: {e}")
                    traceback.print_exc()
                    continue

                if not setups:
                    print("  → No valid setup found")
                    continue

                best = setups[0]

                print(
                    f"  → Setup found! "
                    f"Score: {best['score']} | "
                    f"Side: {best['side'].upper()} | "
                    f"RR: {best.get('rr', 'N/A')}"
                )

                # -------------------------------------------------
                # Dynamic score
                # -------------------------------------------------

                try:

                    current_min_score = (
                        performance.get_dynamic_min_score(
                            MIN_QUALITY_SCORE
                        )
                    )

                    print(
                        f"  → Dynamic Min Score: "
                        f"{current_min_score}"
                    )

                    if best["score"] < current_min_score:
                        print("  → Rejected (score too low)")
                        continue

                except Exception as e:

                    print(f"  ✗ Dynamic score error: {e}")

                    current_min_score = MIN_QUALITY_SCORE

                # -------------------------------------------------
                # Calculate position size
                # -------------------------------------------------

                try:

                    size = risk.calculate_adaptive_size(
                        best["entry"],
                        best["stop"],
                        best["score"]
                    )

                    print(f"  → Calculated size: ${size:.2f}")

                except Exception as e:

                    print(f"  ✗ Size calculation error: {e}")
                    continue

                if size < 8:
                    print("  → Size too small, skipped")
                    continue

                # -------------------------------------------------
                # FINAL POSITION SAFETY CHECK
                # -------------------------------------------------

                if position_manager.open_trades:
                    print(
                        "  → Existing position detected. "
                        "Trade rejected."
                    )

                    break

                if not risk.can_open_trade():
                    print("  → Risk blocked the trade")
                    continue

                # =================================================
                # PLACE EXACTLY ONE ORDER
                # =================================================

                try:

                    print(
                        f"  → Preparing "
                        f"{best['side'].upper()} order "
                        f"for {pair}"
                    )

                    print(f"  → Size: ${size:.2f}")

                    success = execution.place_order(
                        best,
                        size
                    )

                    if success:

                        # -----------------------------------------
                        # Register position ONLY after successful
                        # order placement
                        # -----------------------------------------

                        position_added = position_manager.add_trade(
                            best,
                            size
                        )

                        if position_added:
                            trade_opened = True

                            print(
                                f"  ✅ TRADE PLACED → "
                                f"{best['side'].upper()} "
                                f"{pair} | Size ${size:.2f}"
                            )

                        else:
                            print(
                                "  ⚠ Order accepted but "
                                "position registration failed"
                            )
                        logger.info(
                            f"Trade lifecycle started | "
                            f"{best['side'].upper()} {pair}"
                        )

                        # -----------------------------------------
                        # IMPORTANT:
                        # Stop scanning all other pairs
                        # -----------------------------------------

                        break


                    else:

                        print(
                            "  ✗ Order placement failed"
                        )

                        # Do NOT immediately try another pair
                        break

                except Exception as e:

                    error_text = str(e)

                    print(
                        f"  ✗ Execution error: {error_text}"
                    )

                    traceback.print_exc()

                    # ---------------------------------------------
                    # INSUFFICIENT BALANCE
                    # ---------------------------------------------

                    if (
                            "INSUFFICIENT_AVAILABLE_BALANCE"
                            in error_text
                    ):
                        print(
                            "  ⚠ INSUFFICIENT_AVAILABLE_BALANCE"
                        )

                        print(
                            "  → New order attempts paused"
                        )

                        # DO NOT keep submitting orders
                        break

                    # ---------------------------------------------
                    # Any other execution failure
                    # ---------------------------------------------

                    break

            # =====================================================
            # 5. STATUS
            # =====================================================

            if trade_opened:

                print(
                    "\n→ Trade successfully opened."
                )

                print(
                    "→ Agent will NOT scan for another "
                    "trade until this position closes."
                )

            else:

                print(
                    "\n→ No trade opened this cycle."
                )

            # =====================================================
            # 6. DAILY REPORT
            # =====================================================

            current_day = datetime.now().day

            if current_day != last_report_day:

                print("\n→ Generating daily report...")

                try:

                    generate_daily_report(
                        performance,
                        risk
                    )

                    stats = performance.get_stats()

                    last_report_day = current_day

                    print("  ✓ Daily report done")

                except Exception as e:

                    print(
                        f"  ✗ Daily report error: {e}"
                    )

            # =====================================================
            # 7. WAIT
            # =====================================================

            print(
                f"\n→ Sleeping "
                f"{LOOP_SLEEP_SECONDS} seconds..."
            )

            time.sleep(LOOP_SLEEP_SECONDS)

        except KeyboardInterrupt:

            print(
                "\n\n" +
                "=" * 70
            )

            print(
                "AGENT STOPPED BY USER (Ctrl+C)"
            )

            print(
                "=" * 70
            )

            try:
                generate_daily_report(
                    performance,
                    risk
                )
            except:
                pass

            break

        except Exception as e:

            print(
                f"\n✗ CRITICAL ERROR "
                f"in main loop: {e}"
            )

            traceback.print_exc()

            print(
                "Sleeping 60 seconds before retry..."
            )

            time.sleep(60)


if __name__ == "__main__":
    run_agent()
