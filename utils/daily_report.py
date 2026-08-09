# utils/daily_report.py
import os
from datetime import datetime
from utils.logger import logger


def generate_daily_report(performance_tracker, risk_engine):
    try:
        stats = performance_tracker.get_stats()
        now = datetime.now()

        report = f"""
=======================================================
       VeteranSR-Agent Daily Report
       {now.strftime('%Y-%m-%d %H:%M')}
=======================================================

Starting Equity : ${performance_tracker.starting_equity:.2f}
Current Equity  : ${stats.get('current_equity', 0):.2f}
Net PnL         : ${stats.get('net_pnl', 0):.2f}  ({stats.get('return_pct', 0)}%)

Total Trades    : {stats.get('total_trades', 0)}
Wins / Losses   : {stats.get('wins', 0)} / {stats.get('losses', 0)}
Win Rate        : {stats.get('win_rate', 0)}%
Recent Win Rate : {stats.get('recent_winrate', 0)}%

Open Positions  : {len(risk_engine.open_positions)}
Daily PnL       : ${getattr(risk_engine, 'daily_pnl', 0):.2f}
Consecutive Loss: {getattr(risk_engine, 'consecutive_losses', 0)}
Paused          : {getattr(risk_engine, 'paused', False)}

=======================================================
"""
        os.makedirs("logs/daily_reports", exist_ok=True)
        filename = f"logs/daily_reports/report_{now.strftime('%Y%m%d')}.txt"

        with open(filename, "w") as f:
            f.write(report)

        print(report)
        logger.info("Daily report generated")
        return report

    except Exception as e:
        print(f"Daily report failed: {e}")
        logger.error(f"Daily report error: {e}")
        return None
