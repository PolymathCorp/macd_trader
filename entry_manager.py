## File: entry_manager.py

import asyncio
import logging
from data_and_indicators import fetch_ohlcv, compute_indicators
from hybrid_signal import generate_signal
from position_sizer import calculate_position_size
from order_execution import place_bracket_order
from config_setup import TIMEFRAME, FETCH_LIMIT, RR_RATIO
from trade_logger import TradeLogger
from datetime import datetime

logger = logging.getLogger(__name__)

class EntryManager:
    def __init__(self, exchange=None):
        self.exchange = exchange
        self.logger = TradeLogger(exchange)

    async def check_and_place(self, symbol: str):
        df = await asyncio.to_thread(fetch_ohlcv, self.exchange, symbol, TIMEFRAME, FETCH_LIMIT)
        df = await asyncio.to_thread(compute_indicators, df)
        signal, confidence = generate_signal(df)
        if not signal or not confidence:
            return

        price = float(df['close'].iloc[-1])
        balance = float(self.exchange.fetch_balance()['USDT']['total'])
        atr = float(df['atr_14'].iloc[-1])
        size = calculate_position_size(balance, confidence, price, atr)
        
        sl = price - (atr * 1.5) if 'buy' in signal else price + (atr * 1.5)
        tp = price + (atr * RR_RATIO * 1.5) if 'buy' in signal else price - (atr * RR_RATIO * 1.5)
        side = 'buy' if 'buy' in signal else 'sell'
        logger.info(f"Placing {signal.upper()} {symbol} | conf={confidence:.2f} | size={size:.6f} | SL={sl:.2f} | TP={tp:.2f}")
        try:
            order = await asyncio.to_thread(
                place_bracket_order,
                exchange=self.exchange,
                symbol=symbol,
                side=side,
                amount=size,
                entry_type='market',
                entry_price=price,
                atr=atr,
            )
            self.logger.log_trade(
                order_id=order['id'],
                entry_time=datetime.utcnow().isoformat(),
                symbol=symbol,
                size=size,
                side=signal,
                entry_price=price,
                atr=atr,
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"Order failed for {symbol}: {e}")

