# Crypto Trading Strategy Guide

This strategy combines **MACD**, **RSI**, **Stochastic RSI**, and **Volume** indicators to generate high-confidence trade signals, with dynamic position sizing and risk management. The goal is to support both intraday and swing trades on Bybit (spot and futures) with clear entry/exit rules, confidence weighting, and automated execution. Below are the key components and best practices:

## Technical Indicators & Signal Generation

* **MACD (Moving Average Convergence Divergence)** – A trend-following momentum oscillator calculated as the difference between the 12-period EMA and 26-period EMA.  Traders commonly **buy** when the MACD line crosses *above* its 9-period signal line (bullish momentum) and **sell/short** when it crosses *below*.  We can also use the MACD histogram (MACD minus signal line) to gauge momentum changes: a rising histogram suggests strengthening trend, a falling histogram suggests weakening.
* **RSI (Relative Strength Index)** – A momentum oscillator (0–100) measuring speed of recent price changes.  RSI above 70 is generally **overbought** (possible sell signal) and below 30 is **oversold** (possible buy signal).  Incorporate RSI by looking for crossovers of these thresholds or bouncing off them.  RSI also helps confirm trend strength; e.g., RSI above 50 signals bullish momentum, below 50 bearish.
* **Stochastic RSI (StochRSI)** – An indicator of RSI’s position relative to its high/low range (also 0–100).  It is more sensitive than RSI and can give timely signals on momentum shifts.  For example, StochRSI crossing above 20 from below (coming out of oversold) can indicate a buy opportunity, while crossing below 80 from above suggests a sell.  Convergence of StochRSI %K and %D lines at extreme values can also signal strong trend reversals.
* **Volume Filter** – Use trading volume to confirm moves. Volume measures market activity and sentiment.  For instance, require that a signal (e.g. MACD crossover) is supported by **higher-than-average volume** (e.g. current volume > 1.5× recent average) to improve reliability.  Low volume on a signal may indicate a false breakout.

&#x20;*Illustration: A chart combining MACD (oscillator at top), price, and volume. Multi-indicator strategies require confirming signals from several sources. For example, a valid long signal might need MACD bullish crossover, RSI moving up from oversold, StochRSI rising, and a volume spike – all together to reduce false signals.*

### Combining Signals

We generate an **entry signal** only when multiple indicators align:

* *Long Entry:* e.g. MACD line > signal line (positive momentum), RSI in a bullish zone (above 50 or rising from oversold), StochRSI turning up from oversold, AND volume above average.
* *Short Entry:* Opposite conditions (MACD below signal, RSI below 50 or falling from overbought, StochRSI falling from overbought, high volume on the downmove).

Requiring multiple indicators to agree greatly reduces false signals. In practice, implement this by checking each condition and only acting when **all** (or a weighted majority) are true.

## Confidence Scoring & Position Sizing

Instead of fixed trades, we assign a **confidence score** (0–1) to each signal based on indicator strength. For example:

* **MACD Score:** Normalize the current MACD histogram by a recent historical maximum (e.g. `MACD_hist / max(MACD_hist, lookback)`). Larger positive values yield higher score.
* **RSI Score:** Measure deviation from neutral (50). For example, `RSI_score = |RSI - 50| / 50`.  If RSI is 80 (strong bullish), score ≈0.6; if RSI is 20 (strong bearish), score ≈0.6 for shorts.
* **StochRSI Score:** If StochRSI %K and %D are deeply above 80 or below 20, the score is high. One way is `Stoch_score = 1 - min(StochRSI, 100 - StochRSI)/50` (so 100→1, 50→0).
* **Volume Score:** Current volume divided by its moving average (e.g. 20-period).  A spike (e.g. Vol/MA = 2) would score 1 (or cap it at 1); average volume (Vol/MA = 1) scores 0.5.

We then **average** these normalized scores to get an overall confidence (0–1).  Only trade if confidence exceeds a threshold (e.g. 0.7).  Higher confidence → larger position or higher leverage. This mimics “Kelly”-style sizing: risk more when signal is stronger. In practice, fix a *base risk per trade* (e.g. 1% of account) and multiply by the confidence factor.  For instance, 0.8 confidence means risk 0.8% of equity.  This ensures capital preservation – a core tenet of position sizing.  Never risk more than a small fraction per trade (commonly ≤2%).

## Dynamic Position Sizing and Leverage

* Determine **trade size** from confidence: e.g. `position_size = account_balance * base_risk * confidence`.
* For futures, adjust **leverage** by confidence: high confidence allows higher leverage (up to risk limits), low confidence uses minimal leverage. Always cap leverage (Bybit has max leverage per symbol).
* Example: If base risk is 1%, confidence = 0.5 → risk 0.5% of account. If confidence = 0.9 → risk 0.9%.

Use appropriate margin and ensure the notional risk (in USD) equals the risk fraction. Always incorporate **volatility**: on volatile assets, use lower leverage for same risk.

## Trade Management & Risk Controls

* **Stop-Loss (SL):** Place an initial SL based on volatility, e.g. 2× ATR (Average True Range) from entry.  This adapts to current volatility.
* **Take-Profit (TP):** Set profit targets via a fixed risk-reward ratio (e.g. 1:2 or 1:3).  For example, if SL = 2×ATR, TP might be 4×ATR above entry. This ensures a consistent reward/risk.
* **Trailing Stop:** Instead of a fixed TP, use a trailing stop to lock profits.  For instance, as price moves in favor, raise the stop by 1×ATR behind price. If the price reverses, the trade exits when hitting this trailing stop. Trailing stops allow riding strong trends while protecting gains.

&#x20;*Example backtest of the strategy: the blue equity curve rises gradually with a few drawdowns. Triangular markers show trade entries/exits, and colored markers (green) indicate trailing stop adjustments. Trailing stops move with price, locking in profits as the trend continues.  This reflects how dynamic stops (ATR- or EMA-based) prevent major losses during reversals.*

* **Time-Based Exit:** Cap trade duration to avoid stale positions. For intraday trades, exit at end of day if still open; for swing trades, exit after a max hold (e.g. 5 trading days) if no signal. This prevents tying up capital indefinitely.
* **EMA Crossover Exit (optional):** As an alternative TP/exit signal, one can exit when a fast EMA (e.g. 20-period) crosses the slow EMA (e.g. 50-period) against the position. For example, exit long when 20-EMA crosses below 50-EMA.

## Implementation Notes & Best Practices

* **Environment & Config:** Store API keys and parameters securely using `python-dotenv` in a `.env` file. Never hard-code secrets. For example, use `load_dotenv()` and access `os.getenv("BYBIT_API_KEY")`.
* **Libraries:** Use **CCXT** or **PyBit** for Bybit API. CCXT offers a unified interface for Spot and Futures.  For example, `exchange = ccxt.bybit({apiKey, secret, enableRateLimit: True})`.  (CCXT also supports Bybit’s unified V5 APIs for spot and USDT-perpetual.)  Use **Pandas** for data handling, and **TA-Lib** or **Pandas-TA** for indicators.  TA-Lib is widely used for 150+ indicators (including MACD, RSI, Stochastic).
* **Modular Code:** Organize code into modules/functions (data fetcher, indicator calculator, signal logic, execution, risk manager). This eases maintenance and testing. For example, separate files like `indicators.py`, `signals.py`, `execution.py`, etc. Maintain a clear folder structure (see below).
* **Logging:** Implement robust logging of all signals, trades, and errors. Log entry/exit reasons and confidence scores. Use timestamps and include P\&L. A logging file (e.g. `logs/trading_bot.log`) helps debugging and performance analysis.
* **Backtesting:** Before live trading, backtest the strategy over historical data (e.g. a year of 1h bars) to validate logic and risk settings. The diagrams above come from such a backtest. Analyze metrics (Sharpe, drawdown) to refine parameters.
* **Paper Trading:** Start on Bybit’s testnet or using small sizes to verify the live integration. Once confidence and performance are acceptable, move to live funds.

### Example Signal Flow

1. **Data Fetch:** Retrieve latest OHLCV bars from Bybit via CCXT (e.g. `fetch_ohlcv('BTC/USDT', '1h', limit=500)`).
2. **Compute Indicators:** Calculate MACD, RSI, StochRSI, ATR on the DataFrame.
3. **Generate Signal:** Check indicator conditions (as above). If MACD crossover + RSI favorable + StochRSI alignment + high volume, signal = “LONG”; if opposite, “SHORT”; else “HOLD”.
4. **Calculate Confidence:** Normalize each indicator’s strength and average them.
5. **Determine Position Size:** Multiply confidence by base risk.
6. **Place Order:** Via CCXT, send a limit or market order on Bybit (spot `exchange.createOrder`, futures via `exchange.createOrder` with params).
7. **Set Stops:** After entry, place stop-loss (and optional take-profit or trailing order).
8. **Monitor:** On each tick or new bar, update trailing stop, exit if TP/SL hit, or reverse if an opposite signal triggers.

This structured, rule-based approach with multiple confirmations and dynamic sizing helps navigate volatile crypto markets while managing risk.
