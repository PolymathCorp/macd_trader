import pandas as pd
import numpy as np
import tulipy as ti
from config_setup import (
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    RSI_PERIOD, STOCH_RSI_PERIOD,
    fastk_period, fastd_period,
    ATR_PERIOD, TIMEFRAME, FETCH_LIMIT,
    EMA_SLOW, EMA_FAST
)

def fetch_ohlcv(exchange, symbol, timeframe=TIMEFRAME, limit=FETCH_LIMIT):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def compute_indicators(df):
    close = df['close'].to_numpy()
    high  = df['high'].to_numpy()
    low   = df['low'].to_numpy()
    vol   = df['volume'].to_numpy()

    # 1. MACD → dif/dea/hist
    dif, dea, macd_hist = ti.macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    pad = len(close) - len(dif)
    df['dif']        = np.concatenate([np.full(pad, np.nan), dif])
    df['dea']        = np.concatenate([np.full(pad, np.nan), dea])
    df['macd_hist']  = np.concatenate([np.full(pad, np.nan), macd_hist])

    # 2. MACD ROC
    df['dif_roc'] = df['dif'].pct_change() * 100
    df['dea_roc'] = df['dea'].pct_change() * 100

    # 3. Multi-period RSI
    for p in (6, 12, 24):
        arr = ti.rsi(close, p)
        df[f'rsi{p}'] = np.concatenate([np.full(len(close)-len(arr), np.nan), arr])

    # EMA Calculations
    df['ema_fast'] = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()

    # 4. StochRSI (k/d)
    raw = ti.stochrsi(close, STOCH_RSI_PERIOD)
    k = pd.Series(raw).rolling(fastk_period).mean().to_numpy()
    d = pd.Series(k).rolling(fastd_period).mean().to_numpy()
    df['stochrsi_k'] = np.concatenate([np.full(len(close)-len(k), np.nan), k*100])
    df['stochrsi_d'] = np.concatenate([np.full(len(close)-len(d), np.nan), d*100])

    # 5. ATR
    atr = ti.atr(high, low, close, ATR_PERIOD)
    df['atr'] = np.concatenate([np.full(len(close)-len(atr), np.nan), atr])

    # 6. Volume MA5 and MA20
    df['vol_ma5']  = df['volume'].rolling(window=5).mean()
    df['vol_ma20'] = df['volume'].rolling(window=20).mean()

    # 7. Placeholder model predictions (replace with your actual model)
    # X could be [dif, dea, macd_hist, dif_roc, dea_roc, rsi6, rsi12, rsi24]
    # For demo, we flag bullish when MACD histogram > 0 & ROC > 0
    df['predicted_bullish'] = (df['macd_hist'] > 0) & (df['dif_roc'] > df['dea_roc'])
    df['predicted_bearish'] = (df['macd_hist'] < 0) & (df['dif_roc'] < df['dea_roc'])

    return df

