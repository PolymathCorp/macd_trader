#File: config_setup.py

import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# CCXT / Exchange configuration
EXCHANGE_ID = os.getenv("EXCHANGE_ID", "bybit")  # default to Bybit
API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")

# Trading parameters
TIMEFRAME = os.getenv("TIMEFRAME", "5m") # prev 15m
FETCH_LIMIT = int(os.getenv("FETCH_LIMIT", 300)) # prev 1000
BASE_RISK_PCT = float(os.getenv("BASE_RISK_PCT", 0.01))  # 1% risk
MIN_LEVERAGE = float(os.getenv("MIN_LEVERAGE", 2))
MAX_LEVERAGE = float(os.getenv("MAX_LEVERAGE", 25))
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

RSI_PERIOD = 14
RSI6_PERIOD = 6
RSI12_PERIOD = 12
RSI24_PERIOD = 24

VOLUME_MA5_PERIOD = 5
VOLUME_MA10_PERIOD = 10

STOCH_RSI_PERIOD = 14
fastk_period = 14
fastd_period = 3
ATR_PERIOD = 20 # prev. 14
EMA_FAST = 40   # Prev. 20
EMA_SLOW = 100  # Prev. 50

DEFAULT_TP_PERCENTAGE = 0.10  # 10% default TP
MIN_SL_PERCENTAGE = 0.005  # 2%

RR_RATIO = 2
PROFIT_LOCK_RATIO = 0.5  # Close 50% at 2x RR
ADVERSE_CLOSE_EXIT = 3    # Exit after 3 adverse closes

# Scheduler parameters
SYMBOL_CHECK_INTERVAL = int(os.getenv("SYMBOL_CHECK_INTERVAL", 10 * 60))  # 10 minutes

# File paths
POSITIVE_CSV = os.getenv("POSITIVE_CSV", "../positive.csv")
NEGATIVE_CSV = os.getenv("NEGATIVE_CSV", "../negative.csv")
SELECTED_CSV = os.getenv("SELECTED_CSV", "../selected_symbols.csv")

# Logging
LOG_FILE = os.getenv("LOG_FILE", "./logs/bot.log")


