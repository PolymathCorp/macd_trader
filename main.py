import asyncio
import logging
import time
import pandas as pd
import sys
from config_setup import SYMBOL_CHECK_INTERVAL, SELECTED_CSV, LOG_FILE
from symbol_selector import select_latest_symbols
from exchange_setup import init_exchange
from entry_manager import EntryManager
from position_manager import PositionManager

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Initialize exchange and managers
exchange = init_exchange()
entry_mgr = EntryManager(exchange)
pos_mgr = PositionManager(exchange)

async def symbol_updater():
    """Refresh the list of trading symbols periodically."""
    while True:
        try:
            select_latest_symbols()
            logger.info("Symbol list refreshed.")
        except Exception as e:
            logger.error(f"Symbol update error: {e}")
        await asyncio.sleep(SYMBOL_CHECK_INTERVAL)

async def entry_loop():
    """Check and place new entries for selected symbols."""
    while True:
        symbols = pd.read_csv(SELECTED_CSV)['symbol'].tolist()
        for symbol in symbols:
            try:
                await entry_mgr.check_and_place(symbol)
            except Exception as e:
                logger.error(f"EntryManager error for {symbol}: {e}")
        await asyncio.sleep(5)

def management_loop():
    """Synchronous loop to manage open positions continuously."""
    while True:
        try:
            pos_mgr.update_positions()
        except Exception as e:
            logger.error(f"PositionManager error: {e}")
        time.sleep(2)

async def main():
    # Initial cleanup run before starting loops
    try:
        logger.info("Running initial position cleanup before starting loops...")
        pos_mgr.update_positions()
    except Exception as e:
        logger.error(f"Initial cleanup error: {e}")

    # Schedule management loop as background task first
    management_task = asyncio.create_task(asyncio.to_thread(management_loop))
    # Then start symbol and entry loops
    symbol_task = asyncio.create_task(symbol_updater())
    entry_task = asyncio.create_task(entry_loop())

    # Await all tasks
    await asyncio.gather(management_task, symbol_task, entry_task)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Recieved shutdown signal, closing all positions...')
        pos_mgr.close_all_positions()
        logger.info('All positions closed. Exiting.')
        sys.exit(0)
