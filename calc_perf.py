from trade_logger import TradeLogger
from exchange_setup import init_exchange
import pprint
import sys

USAGE = '[USAGE]: calc_performance.py {start-time} {end-time} <arguments are optional>'
exchange = init_exchange()
logger = TradeLogger(exchange)
if len(sys.argv) == 1 or len(sys.argv) == 3:

    if len(sys.argv) == 1:
        print('PERFORMANCE SO FAR')
        pprint.pprint(logger.calculate_performance())

    elif len(sys.argv) == 3:
        starttime, endtime = sys.argv[1:]
        print('PERFORMANCE FOR SPECIFIED TIME')
        pprint.pprint(logger.calculate_performance(start_time=starttime, end_time=endtime))
else:
    print(USAGE)
