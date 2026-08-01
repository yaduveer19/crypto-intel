"""CVD Divergence — tape-based signal: price vs cumulative volume delta divergence."""

from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, calculate_atr
from app.metrics.cvd import compute_cvd, cvd_divergence_signal


@register_strategy
class CVDDivergenceStrategy(BaseStrategy):
    @property
    def key(self): return "cvd_divergence"

    @property
    def name(self): return "CVD Divergence"

    @property
    def description(self):
        return "Spot smart money — divergence between price and cumulative volume delta"

    @property
    def default_params(self):
        return {"lookback": 30, "atr_multiplier_sl": 1.5, "atr_multiplier_tp": 2.5}

    def analyze(self, symbol, ohlcv, params=None, trades=None, **kwargs):
        params = {**self.default_params, **(params or {})}
        if not trades or not ohlcv:
            return StrategyResult(bias="NEUTRAL", reasoning="CVD needs live trade tape")
        last = ohlcv[-1]
        price = last["close"]
        atr = calculate_atr([k["high"] for k in ohlcv], [k["low"] for k in ohlcv], [k["close"] for k in ohlcv], 14)
        cvd_series = compute_cvd(trades)
        sig = cvd_divergence_signal(ohlcv, cvd_series, lookback=params["lookback"])
        sl_mult, tp_mult = params["atr_multiplier_sl"], params["atr_multiplier_tp"]

        if sig["divergence"] == "bullish":
            return StrategyResult(bias="BULL", tier="HIGH" if sig["strength"] > 0.4 else "MOD",
                                  entry_price=price, stop_loss=round(price - atr * sl_mult, 2),
                                  tp1=round(price + atr * tp_mult, 2), tp2=round(price + atr * tp_mult * 1.8, 2),
                                  reasoning=sig["message"])
        if sig["divergence"] == "bearish":
            return StrategyResult(bias="BEAR", tier="HIGH" if sig["strength"] > 0.4 else "MOD",
                                  entry_price=price, stop_loss=round(price + atr * sl_mult, 2),
                                  tp1=round(price - atr * tp_mult, 2), tp2=round(price - atr * tp_mult * 1.8, 2),
                                  reasoning=sig["message"])
        return StrategyResult(bias="NEUTRAL", reasoning=sig["message"])
