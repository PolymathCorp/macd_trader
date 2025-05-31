# exchange_setup.py

import ccxt
from config_setup import API_KEY, API_SECRET, EXCHANGE_ID

def init_exchange():
    exchange_class = getattr(ccxt, EXCHANGE_ID)
    exchange = exchange_class({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        #'options': {'defaultType': 'swap'},
    })

    # Enable demo mode
    exchange.enable_demo_trading(True)
    return exchange

