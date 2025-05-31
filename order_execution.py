import time
import logging
import ccxt
from config_setup import RR_RATIO, MIN_SL_PERCENTAGE, DEFAULT_TP_PERCENTAGE

logger = logging.getLogger(__name__)
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.0  # seconds

def _retry(fn, *args, **kwargs):
    """Retry wrapper for CCXT calls."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return fn(*args, **kwargs)
        except ccxt.NetworkError as e:
            logger.warning(f"[Retry {attempt}] NetworkError: {e}")
            time.sleep(RETRY_DELAY)
        except ccxt.ExchangeError as e:
            logger.error(f"ExchangeError: {e}")
            break
    return None

def place_bracket_order(
    exchange,
    symbol: str,
    side: str,
    amount: float,
    entry_type: str = 'market',
    entry_price: float = None,
    atr: float = None,
    leverage: float = None
):
    """
    Place a market or limit order with attached stop-loss and take-profit
    on Bybit via CCXT.

    :param exchange: CCXT exchange instance
    :param symbol: trading symbol, e.g. 'BTC/USDT'
    :param side: 'buy' or 'sell'
    :param amount: contract or asset amount
    :param entry_type: 'market' or 'limit'
    :param entry_price: required for limit orders
    :param atr: latest ATR value (from data_and_indicators)
    :param leverage: leverage multiplier
    """
    if entry_price is None or atr is None:
        logger.error("entry_price and atr must be provided for bracket orders.")
        return None

    # dynamic ATR based sl/tp placement
    if side == 'buy':
        sl = entry_price - (atr * 1.5)
        default_sl = entry_price * (1 - MIN_SL_PERCENTAGE)
        sl = max(sl, default_sl)    
        tp = entry_price + (atr * RR_RATIO * 1.5)
        default_tp = entry_price * (1 + DEFAULT_TP_PERCENTAGE)
        tp = max(tp, default_tp)

        if tp <= entry_price:
            logger.error(f"Invalid TP for buy: TP={tp} must be > entry={entry_price}")
            return None
    else:  # sell
        sl = entry_price + (atr * 1.5)
        default_sl = entry_price * (1 + MIN_SL_PERCENTAGE)
        sl = min(sl, default_sl)
        tp = entry_price - (atr * RR_RATIO * 1.5)
        default_tp = entry_price * (1 - DEFAULT_TP_PERCENTAGE)
        tp = min(tp, default_tp)

        if tp >= entry_price:
            logger.error(f"Invalid TP for sell: TP={tp} must be < entry={entry_price}")
            return None
    print(side, entry_price, sl, default_sl, tp, default_tp)
    params = {
        'reduceOnly': False,
        'stopLoss': {
            'triggerPrice':    sl,
            'triggerDirection': 2,
        },
        'takeProfit': {
            'triggerPrice':    tp,
            'triggerDirection': 1,
        },
    }
    try:
        print(side)
        if entry_type == 'market':
            order = _retry(
                exchange.create_order,
                symbol,
                entry_type,
                side,
                amount,
                None,
                params
            )
        else:
            order = _retry(
                exchange.create_order,
                symbol,
                'limit',
                side,
                amount,
                entry_price,
                params
            )

        if order:
            order_id = order.get('id') or order.get('info', {}).get('orderId')
            logger.info(f"Bracket order placed: id={order_id}, side={side}, amount={amount}")
        else:
            logger.error("Failed to place bracket order after retries.")
        return order

    except Exception as e:
        logger.exception(f"Exception during order placement: {e}")
        return None

