import joblib
import numpy as np

# Load trained model and define features
model = joblib.load('models/10m_WedMay2816:06:362025_lgbm_model.pkl')

FEATURES = [
    'ema_12','ema_26','macd_hist','rsi_14','stochrsi_k','stochrsi_d','cci_20',
    'atr_14','obv','bull_bear','vol_ratio','volatility_30m','vwap'
] + [f'{f}_lag{lag}' for f in [
    'ema_12','ema_26','macd_hist','rsi_14','stochrsi_k',
    'stochrsi_d','cci_20','atr_14','obv','bull_bear',
    'vol_ratio','volatility_30m'
] for lag in (1,2,3)]

def generate_signal(df):
    if len(df) < 1 or not all(col in df.columns for col in FEATURES):
        return None, 0.0

    # Prepare feature vector
    #latest = df[FEATURES].iloc[-1].values.reshape(1, -1)
    latest = df[FEATURES].iloc[[-1]]

    # Model prediction
    pred = model.predict(latest)[0]
    proba = model.predict_proba(latest)[0]
    confidence = np.max(proba)  # Use maximum probability

    # Map prediction to signal
    signal_map = {
        0: ('sell', confidence),
        2: ('buy', confidence),
        1: (None, 0.0)
    }
    signal, conf = signal_map.get(pred, (None, 0.0))
    
    # Determine signal strength
    if signal:
        if conf >= 0.9:
            strength = 'strong'
        elif conf >= 0.7:
            strength = 'moderate'
        else:
            strength = 'weak'
        return f'{strength} {signal}', round(conf, 2)

    return None, 0.0


