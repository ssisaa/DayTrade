# utils/setup_logger.py
import csv
import os
from datetime import datetime


class SetupLogger:
    def __init__(self):
        os.makedirs("logs", exist_ok=True)
        self.filename = "logs/all_setups.csv"

        # Create file with headers if it doesn't exist
        if not os.path.exists(self.filename):
            with open(self.filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp",
                    "pair",
                    "side",
                    "status",  # ACCEPTED or REJECTED
                    "score",
                    "rsi",
                    "distance_pct",
                    "net_rr",
                    "htf_bias",
                    "regime",
                    "entry",
                    "stop",
                    "target",
                    "reason"
                ])

    def log_setup(self, pair, side, status, score, rsi, distance, net_rr,
                  htf_bias, regime, entry=None, stop=None, target=None, reason=""):
        try:
            with open(self.filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    pair,
                    side,
                    status,
                    round(score, 1) if score is not None else "",
                    round(rsi, 2) if rsi is not None else "",
                    round(distance * 100, 3) if distance is not None else "",
                    round(net_rr, 2) if net_rr is not None else "",
                    htf_bias,
                    regime,
                    round(entry, 4) if entry else "",
                    round(stop, 4) if stop else "",
                    round(target, 4) if target else "",
                    reason
                ])
        except Exception as e:
            print(f"Failed to log setup: {e}")


# Global instance
setup_logger = SetupLogger()
