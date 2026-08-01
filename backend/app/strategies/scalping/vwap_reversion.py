"""VWAP Mean Reversion — buy when price tags below VWAP in an uptrend, sell above in a downtrend."""

from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, calculate_atr, ema


@register_strategy
class VWAPReversionStrategy(BaseStrategy):
    @property
    def key(self): return "vwap_reversion"

    @property
    def name(self): return "VWAP Reversion"

    @property
    def description(self):
        return "Scalp against VWAP — fade extremes back to the mean with volume confirmation"

    @property
    def default_params(self):
        return {"deviation": 0.0025, "atr_multiplier_sl": 1.2, "atr_multiplier_tp": 1.8}

    def analyze(self, symbol, ohlcv, params=None, **kwargs):
        params = {**self.default_params, **(params or {})}
        if not ohlcv or len(ohlcv) < 20:
            return StrategyResult(bias="NEUTRAL", reasoning="Not enough data for VWAP")
        cum_pv, cum_v = 0.0, 0.0
        for k in ohlcv:
            typ = (k["high"] + k["low"] + k["close"]) / 3
            vol = k.get("volume", 0) or 0
            cum_pv += typ * vol
            cum_v += vol
        vwap = cum_pv / cum_v if cum_v else ohlcv[-1]["close"]
        last = ohlcv[-1]
        price = last["close"]
        dev = params["deviation"]
        atr = calculate_atr([k["high"] for k in ohlcv], [k["low"] for k in ohlcv], [k["close"] for k in ohlcv], 14)
        trend = ema([k["close"] for k in ohlcv], 50)
        dist = (price - vwap) / vwap if vwap else 0
        sl_mult = params["atr_multiplier_sl"]
        tp_mult = params["atr_multiplier_tp"]
        volume_confirm = last.get("volume", 0) or 0 > sum((k.get("volume", 0) or 0) for k in ohlcv[-10:]) / 10 * 0.8

        if price < vwap * (1 - dev) and trend > 0:
            if not volume_confirm:
                return StrategyResult(bias="BULL", tier="MOD", entry_price=price, stop_loss=round(price - atr * sl_mult, 2),
                                      tp1=round(vwap, 2), tp2=round(vwap + atr * tp_mult, 2),
                                      reasoning=f"Price {dist*100:.2f}% below VWAP ({vwap:.2f}) in an uptrend — mean reversion long. Volume weak, keep size modest.")
            return StrategyResult(bias="BULL", tier="HIGH", entry_price=price, stop_loss=round(price - atr * sl_mult, 2),
                                  tp1=round(vwap, 2), tp2=round(vwap + atr * tp_mult, 2),
                                  reasoning=f"Price {dist*100:.2f}% below VWAP with above-average volume — high-conviction mean reversion long back to VWAP {vwap:.2f}.")
        if price > vwap * (1 + dev) and trend < 0:
            return StrategyResult(bias="BEAR", tier="HIGH", entry_price=price, stop_loss=round(price + atr * sl_mult, 2),
                                  tp1=round(vwap, 2), tp2=round(vwap - atr * tp_mult, 2),
                                  reasoning=f"Price {dist*100:.2f}% above VWAP in a downtrend — mean reversion short back to VWAP {vwap:.2f}.")
        return StrategyResult(bias="NEUTRAL", reasoning=f"Price {dist*100:.2f}% from VWAP — within normal range, no edge.")
