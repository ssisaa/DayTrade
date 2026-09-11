# ============================================================
# VeteranSR-Agent - Clean Main (Perpetual Version)
# One position at a time + Safety focused
# ============================================================

import time
import traceback
from datetime import datetime

from config import *

print("\n" + "="*70)
print("LOADING MODULES...")
print("="*70)

try:
    from data.data_feed import DataFeed
    print("OK - data_feed")
except Exception as e:
    print(f"FAILED data_feed: {e}")
    raise

try:
    from core.indicators import add_indicators
    print("OK - indicators")
except Exception as e:
    print(f"FAILED indicators: {e}")
    raise

try:
    from core.regime import classify_regime
    print("OK - regime")
except Exception as e:
    print(f"FAILED regime: {e}")
    raise

try:
    from core.setup_scanner import find_setups
    print("OK - setup_scanner")
except Exception as e:
    print(f"FAILED setup_scanner: {e}")
    raise

try:
    from core.risk_engine import RiskEngine
    print("OK - risk_engine")
except Exception as e:
    print(f"FAILED risk_engine: {e}")
    raise

try:
    from core.execution import Execution
    print("OK - execution")
except Exception as e:
    print(f"FAILED execution: {e}")
    raise

try:
    from core.position_manager import PositionManager
    print("OK - position_manager")
except Exception as e:
    print(f"FAILED position_manager: {e}")
    raise

try:
    from core.performance import init_performance
    print("OK - performance")
except Exception as e:
    print(f"FAILED performance: {e}")
    raise

try:
    from utils.logger import logger
    print("OK - logger")
except Exception as e:
    print(f"FAILED logger: {e}")
    raise

try:
    from utils.daily_report import generate_daily_report
    print("OK - daily_report")
except Exception as e:
    print(f"FAILED daily_report: {e}")
    raise

try:
    from utils.telegram_alert import alert_risk_pause, alert_error, alert_daily_summary
    print("OK - telegram_alert")
except Exception as e:
    print(f"Telegram disabled: {e}")
    def alert_risk_pause(msg): pass
    def alert_error(msg): pass
    def alert_daily_summary(stats, risk): pass

print("="*70)
print("ALL MODULES LOADED")
print("="*70 + "\n")

def run_agent():
    print("\n" + "="*70)
    print("VETERAN SR-AGENT - PERPETUAL MODE")
    print(f"Mode             : {MODE}")
    print(f"Starting Equity  : ${STARTING_EQUITY}")
    print(f"Pairs            : {PAIRS}")
    print(f"Max Positions    : {MAX_OPEN_POSITIONS}")
    print(f"Min Quality Score: {MIN_QUALITY_SCORE}")
    print("="*70 + "\n")

    logger.info("Agent Started - Perpetual Version")

    # Initialize
    feed = DataFeed()
    risk = RiskEngine(STARTING_EQUITY)
    execution = Execution(feed.exchange)
    position_manager = PositionManager(execution, risk, feed)
    performance = init_performance(STARTING_EQUITY)

    last_report_day = datetime.now().day
    cycle = 0

    while True:
        try:
            cycle += 1
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n{'='*65}")
            print(f"CYCLE {cycle} | {now} | Equity: ${risk.equity:.2f}")
            print(f"{'='*65}")

            # 1. Always manage existing positions first
            print("-> Checking open positions (SL / TP / Trail / Partial)...")
            position_manager.manage_open_positions()
            open_count = len(position_manager.open_trades)
            print(f"   Open positions: {open_count}")

            # 2. ONE POSITION RULE - Most Important
            if open_count >= MAX_OPEN_POSITIONS:
                print("-> Position already open. Waiting for exit before new trades...")
                time.sleep(LOOP_SLEEP_SECONDS)
                continue

            # 3. Risk check
            if not risk.can_open_trade():
                print("-> RISK LIMIT REACHED - Agent paused")
                logger.warning("Risk limits reached")
                alert_risk_pause("Daily loss or Max Drawdown hit")
                time.sleep(90)
                continue

            print("-> No open position + Risk OK. Scanning for new setups...")

            # 4. Scan pairs
            trade_placed = False

            for pair in PAIRS:
                if trade_placed:
                    break

                print(f"\n-> Scanning {pair}...")

                try:
                    df_1h = feed.get_ohlcv(pair, "1h")
                    df_4h = feed.get_ohlcv(pair, "4h")
                    df_daily = feed.get_ohlcv(pair, "1d")
                except Exception as e:
                    print(f"   Data fetch error: {e}")
                    continue

                if df_1h is None or df_daily is None:
                    print(f"   No data for {pair}")
                    continue

                print(f"   Data OK | 1h candles: {len(df_1h)}")

                try:
                    df_daily = add_indicators(df_daily)
                    regime = classify_regime(df_daily)
                    print(f"   Regime: {regime}")
                except Exception as e:
                    print(f"   Regime error: {e}")
                    continue

                try:
                    setups = find_setups(df_1h, df_4h, regime, pair)
                except Exception as e:
                    print(f"   Setup scanner error: {e}")
                    traceback.print_exc()
                    continue

                if not setups:
                    print(f"   No valid setup")
                    continue

                best = setups[0]
                print(f"   Setup found | Score: {best['score']} | Side: {best['side'].upper()}")

                # Dynamic score check
                try:
                    current_min = performance.get_dynamic_min_score(MIN_QUALITY_SCORE)
                    if best["score"] < current_min:
                        print(f"   Rejected (Score {best['score']} < dynamic min {current_min})")
                        continue
                except:
                    pass

                # Calculate size
                try:
                    size = risk.calculate_adaptive_size(best["entry"], best["stop"], best["score"])
                    print(f"   Calculated size: ${size:.2f}")
                except Exception as e:
                    print(f"   Size error: {e}")
                    continue

                if size < 5:
                    print("   Size too small - skipped")
                    continue

                if not risk.can_open_trade():
                    print("   Risk blocked the trade")
                    continue

                # Place the order
                success = execution.place_order(best, size)
                if success:
                    position_manager.add_trade(best, size)
                    print(f"   TRADE PLACED -> {best['side'].upper()} {pair} | Size ${size:.2f}")
                    trade_placed = True
                else:
                    print("   Order placement failed")

            # 5. Daily report
            current_day = datetime.now().day
            if current_day != last_report_day:
                print("\n-> Generating daily report...")
                try:
                    generate_daily_report(performance, risk)
                    stats = performance.get_stats()
                    alert_daily_summary(stats, risk)
                    last_report_day = current_day
                except Exception as e:
                    print(f"   Daily report error: {e}")

            print(f"\n-> Sleeping {LOOP_SLEEP_SECONDS} seconds...")
            time.sleep(LOOP_SLEEP_SECONDS)

        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("AGENT STOPPED BY USER")
            print("="*70)
            try:
                generate_daily_report(performance, risk)
            except:
                pass
            break

        except Exception as e:
            print(f"\nCRITICAL ERROR: {e}")
            traceback.print_exc()
            try:
                alert_error(str(e))
            except:
                pass
            time.sleep(60)

if __name__ == "__main__":
    print(f"Trading Mode     : {TRADING_MODE}")
    print(f"Pairs            : {PAIRS}")
    print(f"Default Type     : {DEFAULT_TYPE}")
    run_agent()
