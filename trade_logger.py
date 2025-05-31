##File: trade_logger.py

import csv
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import ccxt  # for exception handling

filename = 'logs/trades.csv'
sl_tp_log = 'logs/sl_tp_updates.csv'

class TradeLogger:
    def __init__(self, exchange):
        self.filename = filename
        self.sl_tp_log = sl_tp_log
        self.exchange = exchange
        self.config_file = 'balance_config.json'
        self._create_files()
        self.initial_balance = self._initialize_balance()
        self.last_reconcile = None

    def _create_files(self):
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'order_id', 'entry_time', 'exit_time', 'symbol', 'side', 'size',
                    'entry_price', 'exit_price', 'pnl', 'duration',
                    'atr', 'rr_ratio', 'confidence', 'close_type'
                ])
        if not os.path.exists(self.sl_tp_log):
            with open(self.sl_tp_log, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'order_id', 'timestamp', 'old_sl', 'new_sl', 'old_tp', 'new_tp'
                ])
        if not os.path.exists('cash_flows.csv'):
            with open('cash_flows.csv', 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'type', 'amount'])

    def _initialize_balance(self):
        if os.path.exists(self.config_file):
            with open(self.config_file) as f:
                return json.load(f)['initial_balance']
        balance = self.exchange.fetch_balance()['USDT']['total']
        with open(self.config_file, 'w') as f:
            json.dump({'initial_balance': balance}, f)
        return balance

    def log_trade(self, order_id, **kwargs):
        '''Log a new trade entry with the exchange order ID.'''
        with open(self.filename, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                order_id,
                kwargs.get('entry_time', datetime.utcnow().isoformat()),
                '',  # exit_time
                kwargs['symbol'],
                kwargs['side'],
                kwargs['size'],
                kwargs['entry_price'],
                '',  # exit_price
                '',  # pnl
                '',  # duration
                kwargs['atr'],
                '',  # rr_ratio
                kwargs['confidence'],
                ''   # close_type
            ])

    def update_trade_exit(self, order_id, exit_price, close_type='manual'):
        df = pd.read_csv(self.filename)
        mask = (df['order_id'] == order_id) & (df['exit_time'].isna())
        if not mask.any():
            return False
        idx = df[mask].index[0]
        entry_time = datetime.fromisoformat(df.at[idx, 'entry_time'])
        entry_price = df.at[idx, 'entry_price']
        size = df.at[idx, 'size']
        side = df.at[idx, 'side']
        pnl = size * (exit_price - entry_price) * (1 if side == 'buy' else -1)
        duration = (datetime.utcnow() - entry_time).total_seconds() / 3600
        rr = abs(pnl) / (df.at[idx, 'atr'] * size)
        df.at[idx, 'exit_time'] = datetime.utcnow().isoformat()
        df.at[idx, 'exit_price'] = exit_price
        df.at[idx, 'pnl'] = pnl
        df.at[idx, 'duration'] = duration
        df.at[idx, 'rr_ratio'] = rr
        df.at[idx, 'close_type'] = close_type
        df.to_csv(self.filename, index=False)
        return True

    def log_sl_tp_update(self, order_id, old_sl, new_sl, old_tp, new_tp):
        '''Log each SL/TP update for later auditing.'''
        with open(self.sl_tp_log, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                order_id,
                datetime.utcnow().isoformat(),
                old_sl,
                new_sl,
                old_tp,
                new_tp
            ])

    def reconcile_closed_orders(self):
        '''Fetch closed orders from exchange and reconcile recent closures only.'''
        if self.last_reconcile is None:
            since = (datetime.utcnow() - timedelta(days=30)).timestamp() * 1000
        else:
            since = self.last_reconcile
        symbols = set(pd.read_csv(self.filename)['symbol'])
        for symbol in symbols:
            try:
                orders = self.exchange.fetch_closed_orders(symbol, since=int(since), limit=100)
                for order in orders:
                    exit_price=order.get('average')
                    print('exit_price', exit_price, type(exit_price))
                    if order['status'] == 'closed':
                        self.update_trade_exit(
                            order_id=order['id'],
                            exit_price=order.get('average'),
                            close_type=order['info'].get('type', 'sl_tp')
                        )
            except ccxt.BaseError:
                continue
        self.last_reconcile = datetime.utcnow().timestamp() * 1000

    def get_open_trade_by_symbol(self, symbol):
        '''Fetch the most recent open trade for a symbol.'''
        df = pd.read_csv(self.filename)
        open_trades = df[(df['symbol'] == symbol) & (df['exit_time'].isna())]
        if not open_trades.empty:
            return open_trades.iloc[-1].to_dict()
        return None

    def calculate_performance(self, start_time=None, end_time=None):
        """
        Calculate performance metrics optionally within a time window.

        Args:
            start_time (str|datetime, optional): ISO string or datetime to start period.
            end_time (str|datetime, optional): ISO string or datetime to end period.
        Returns:
            dict: win_rate, max_drawdown, profit_factor, sharpe_ratio
        """
        # Load trades
        trades = pd.read_csv(self.filename, parse_dates=['entry_time', 'exit_time'])
        # Filter by dates
        if start_time:
            start = pd.to_datetime(start_time)
            trades = trades[trades['entry_time'] >= start]
        if end_time:
            end = pd.to_datetime(end_time)
            trades = trades[trades['entry_time'] <= end]

        if trades.empty:
            return {'win_rate': None, 'max_drawdown': None,
                    'profit_factor': None, 'sharpe_ratio': None}

        trades['pnl'] = trades['pnl'].fillna(0)
        trades['cum_pnl'] = trades['pnl'].cumsum()
        equity = self.initial_balance + trades['cum_pnl']

        # Compute drawdown
        peak = equity.cummax()
        drawdown = (peak - equity) / peak

        # Performance metrics
        wins = trades[trades['pnl'] > 0]['pnl'].sum()
        losses = abs(trades[trades['pnl'] < 0]['pnl'].sum())

        return {
            'win_rate': len(trades[trades['pnl'] > 0]) / len(trades),
            'max_drawdown': drawdown.max(),
            'profit_factor': wins / losses if losses > 0 else None,
            'sharpe_ratio': trades['pnl'].mean() / trades['pnl'].std() if trades['pnl'].std() else None
        }

