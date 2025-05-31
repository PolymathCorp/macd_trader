## File: position_manager.py

import time
import logging
from exchange_setup import init_exchange
from data_and_indicators import fetch_ohlcv, compute_indicators
from exit_strat import update_trailing_levels, should_exit
from config_setup import TIMEFRAME, FETCH_LIMIT
from trade_logger import TradeLogger

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, exchange=None):
        self.exchange = exchange or init_exchange()
        self.logger = TradeLogger(self.exchange)

    def close_position(self, symbol, side, size, exit_price):
        '''Close market position and log exit using stored order_id.'''
        try:
            # 1) Execute the actual market close
            close_order = self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=abs(size)
            )
            logger.info(f"Closed {symbol} position @ {exit_price}")
            
            # 2) Look up our original entry to get its order_id
            open_trade = self.logger.get_open_trade_by_symbol(symbol)
            if open_trade:
                # 3) Tell the logger “this order_id just exited at exit_price”
                self.logger.update_trade_exit(
                    order_id=open_trade['order_id'],
                    exit_price=exit_price,
                    close_type='manual'
                )
            else:
                logger.warning(f"No open trade found for {symbol} to update exit.")

        except Exception as e:
            logger.error(f"Failed to close {symbol}: {e}")

    def close_all_positions(self):
        """
        Immediately close all open positions on the exchange and log exits.
        """
        positions = self.exchange.fetch_positions()
        for pos in positions:
            symbol = pos['symbol'].replace('/','').replace(':USDT','')
            size = float(pos['contracts'])
            if size == 0:
                continue
            side = 'sell' if pos['side'] == 'long' else 'buy'
            # latest price
            ticker = self.exchange.fetch_ticker(pos['symbol'])
            exit_price = float(ticker['last'])
            self.close_position(symbol, side, size, exit_price)


    def update_positions(self):
        try:
            self.logger.reconcile_closed_orders()
            print('checking the reconcile')
            positions = self.exchange.fetch_positions()
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return

        for pos in positions:
            symbol = pos['symbol'].replace('/','').replace(':USDT','')
            size = float(pos['contracts'])
            if size == 0:
                continue
            df = fetch_ohlcv(self.exchange, symbol, '3m', FETCH_LIMIT)
            df = compute_indicators(df)
            current_price = float(df['close'].iloc[-1])
            atr = df['atr'].iloc[-1]
            if should_exit(
                side=pos['side'],
                closes=df['close'].to_numpy(),
                macd=df['dif'].to_numpy(),
                macd_signal=df['dea'].to_numpy(),
                ema_fast=df['ema_fast'].to_numpy(),
                ema_slow=df['ema_slow'].to_numpy()
            ):
                #ord_id = self.exchange.fetch_open_orders(symbol)['id']
                self.close_position(
                    #order_id = ord_id,
                    symbol=symbol,
                    side='sell' if pos['side']=='long' else 'buy',
                    size=size,
                    exit_price=current_price
                )
                continue
            old_sl = float(pos.get('stopLossPrice', 0))
            old_tp = float(pos.get('takeProfitPrice', 0))
            ticker = self.exchange.fetch_ticker(symbol)
            mark_price = float(ticker['info']['markPrice'])
            new_sl, new_tp = update_trailing_levels(
                side=pos['side'],
                close=current_price,
                prev_sl=old_sl,
                prev_tp=old_tp,
                atr=atr,
                ema=df['ema_fast'].iloc[-1],
                mark_price=mark_price
            )

            THRESHOLD = current_price * 0.000000005
            if abs(new_sl-old_sl)>THRESHOLD or abs(new_tp-old_tp)>THRESHOLD:
                open_trade = self.logger.get_open_trade_by_symbol(symbol)
                updated = self._update_order(symbol, new_sl, new_tp)
                if updated and open_trade and open_trade.get('order_id'):
                    self.logger.log_sl_tp_update(
                        order_id=open_trade['order_id'],
                        old_sl=old_sl,
                        new_sl=new_sl,
                        old_tp=old_tp,
                        new_tp=new_tp                                                                                   )
                time.sleep(0.3)

    def _update_order(self, symbol, sl, tp):
        params = {
            'category': 'linear',
            'symbol': symbol,
            'takeProfit': f"{tp:.10f}",
            'stopLoss': f"{sl:.10f}",
            'tpslMode': 'Full'
        }
        try:
            resp = self.exchange.private_post_v5_position_trading_stop(params)
            if resp['retCode'] == '0':
                logger.info(f"Updated SL/TP for {symbol} | SL={sl:.4f} TP={tp:.4f}")
                return 1
            elif resp['retCode'] == '34040':
                logger.info(f"No SL/TP changes made")
        except Exception as e:
            logger.error(f"Order update failed: {e}")


