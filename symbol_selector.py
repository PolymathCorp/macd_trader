## File: symbol_selector.py

import pandas as pd
import os
from config_setup import POSITIVE_CSV, NEGATIVE_CSV, SELECTED_CSV

def select_latest_symbols():
    # Load both positive and negative momentum files
    pos = pd.read_csv(POSITIVE_CSV, parse_dates=["retrieval_time"])
    neg = pd.read_csv(NEGATIVE_CSV, parse_dates=["retrieval_time"])

    # Combine and sort by symbol and retrieval_time
    combined = pd.concat([pos, neg], ignore_index=True)

    # Filter only pure USDT pairs (exclude futures like BTCUSDT-09MAY25)
    combined = combined[ combined["symbol"].str.upper().str.endswith("USDT") ]

    # For each symbol, pick the row with max retrieval_time
    latest = combined.sort_values("retrieval_time").groupby("symbol").tail(1)

    # Ensure file does not exist as gzip or binary
    if os.path.exists(SELECTED_CSV):
        os.remove(SELECTED_CSV)

    # Save clean CSV
    latest.to_csv(SELECTED_CSV, index=False)

if __name__ == "__main__":
    select_latest_symbols()

