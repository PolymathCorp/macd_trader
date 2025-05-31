# exit_strat.py
import numpy as np
from config_setup import PROFIT_LOCK_RATIO, ADVERSE_CLOSE_EXIT

def update_trailing_levels(side, close, prev_sl, prev_tp,
                           mark_price: float,
                           atr, ema, trail_atr_factor=1.0,
                           tp_atr_factor=2.0,
                           step_threshold=0.3
                           ):
    current_profit = (close - (prev_tp - 2*atr)) / (prev_tp - 2*atr) if prev_tp else 0
    dynamic_step = step_threshold * max(1, abs(current_profit)*10)
    
    if side == 'long':
        # Profit locking
        if close > prev_tp and prev_tp > 0:
            new_tp = close + atr * tp_atr_factor
        else:
            new_tp = max(prev_tp, close + atr * tp_atr_factor)
        
        # SL logic
        cand_sl = max(close - atr * trail_atr_factor, ema)
        new_sl = max(prev_sl, cand_sl) if cand_sl > prev_sl else prev_sl
        
        # Step filter
        if (new_sl - prev_sl) < atr * dynamic_step:
            new_sl = prev_sl

    else:  # short
        if close < prev_tp and prev_tp > 0:
            new_tp = close - atr * tp_atr_factor
        else:
            new_tp = min(prev_tp, close - atr * tp_atr_factor)
            
        cand_sl = min(close + atr * trail_atr_factor, ema)
        new_sl = min(prev_sl, cand_sl) if cand_sl < prev_sl else prev_sl
        
        if (prev_sl - new_sl) < atr * dynamic_step:
            new_sl = prev_sl

    if side == 'long':
        if new_sl >= mark_price:
            new_sl = mark_price * 0.999  # just below mark
            print(f'adjusted sl for {side}')
        if new_tp <= mark_price:
            new_tp = mark_price * 1.001  # just above mark
            print(f'adjusted tp for {side}')
    else:  # short
        if new_sl <= mark_price:
            new_sl = mark_price * 1.001
            print(f'adjusted sl for {side}')
        if new_tp >= mark_price:
            new_tp = mark_price * 0.999
            print(f'adjusted tp for {side}')

    """
    if position == 'SHORT':
        # Ensure SL stays above mark price
        new_sl = max(new_sl, mark_price * 1.001)
        # TP should stay below mark price
        new_tp = min(new_tp, mark_price * 0.999)
        
    else:  # LONG
        # Ensure SL stays below mark price
        new_sl = min(new_sl, mark_price * 0.999)
        # TP should stay above mark price
        new_tp = max(new_tp, mark_price * 1.001)
    """

    return new_sl, new_tp

def should_exit(side, closes, macd, macd_signal, ema_fast, ema_slow):
    adverse_closes = 0
    for i in range(-ADVERSE_CLOSE_EXIT, 0):
        if side == 'long' and closes[i] < ema_fast[i]:
            adverse_closes += 1
        elif side == 'short' and closes[i] > ema_fast[i]:
            adverse_closes += 1
    
    return adverse_closes >= ADVERSE_CLOSE_EXIT
