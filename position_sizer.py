# position_sizer.py
from config_setup import MIN_LEVERAGE, MAX_LEVERAGE, BASE_RISK_PCT
def calculate_position_size(balance, confidence, price, atr, base_risk_pct=BASE_RISK_PCT):
    """
    Compute the position size (in base currency units) such that:
        it uses volatility adjustment (cap at 3x ATR)
    """
    risk_amount = balance * base_risk_pct * confidence

    atr_adjusted_risk = min(risk_amount / (atr * 3), risk_amount)
    if price <= 0 or atr <=0:
        return 0.0

    size = atr_adjusted_risk / price
    return round(size, 8)


def calc_leverage(confidence, min_leverage=MIN_LEVERAGE, max_leverage=MAX_LEVERAGE):
    """
    Linearly interpolate leverage from [min_leverage .. max_leverage] by confidence [0..1]:
      lev = min + (max - min) * confidence
    """
    lev = min_leverage + (max_leverage - min_leverage) * confidence
    return round(lev, 2)

