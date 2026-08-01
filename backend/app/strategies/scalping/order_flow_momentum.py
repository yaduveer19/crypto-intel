"""Order Flow Momentum — tape aggression: buy/sell pressure, delta bars, absorption."""

from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, calculate_atr


@register_strategy
class OrderFlowMomentumStrategy(BaseStrategy):
    @property
    def key(self): return "order_flow_momentum"

    @property
    def name(self): return "Order Flow Momentum"

    @property
    def description(self):
        return "Read the tape — aggression ratio and delta bars for momentum entries"

    @property
    def default_params(self):
        return {"aggression_threshold": 0.55, "atr_multiplier_sl": 1.2, "atr_multiplier_tp": 2.0}

    def _aggression(self, trades, window=None):
        if not trades:
            return 0.5, 0.0, 0
        recent = trades[-window:] if window else trades
        buy = sum(t["amount"] for t in recent if str(t.get("side", "BUY")).upper() == "BUY")
        sell = sum(t["amount"] for t in recent if str(t.get("side", "BUY")).upper() == "SELL")
        total = buy + sell
        if total == 0:
            return 0.5, 0.0, 0
        return buy / total, (buy - sell) / total, len(recent)

    def analyze(self, symbol, ohlcv, params=None, trades=None, **kwargs):
        params = {**self.default_params, **(params or {})}
        if not trades or not ohlcv:
            return StrategyResult(bias="NEUTRAL", reasoning="Order flow needs live trade tape")
        last = ohlcv[-1]
        price = last["close"]
        atr = calculate_atr([k["high"] for k in ohlcv], [k["low"] for k in ohlcv], [k["close"] for k in ohlcv], 14)
        thresh = params["aggression_threshold"]
        sl_mult, tp_mult = params["atr_multiplier_sl"], params["atr_multiplier_tp"]

        buy_ratio_short, delta_short, n_short = self._aggression(trades, 50)
        buy_ratio_long, _, _ = self._aggression(trades, 300)
        active = n_short >= 10

        if buy_ratio_short > thresh and delta_short > 0 and active:
            tier = "HIGH" if buy_ratio_long < buy_ratio_short else "MOD"
            return StrategyResult(bias="BULL", tier=tier, entry_price=price, stop_loss=round(price - atr * sl_mult, 2),
                                  tp1=round(price + atr * tp_mult, 2), tp2=round(price + atr * tp_mult * 1.6, 2),
                                  reasoning=f"Buy aggression {buy_ratio_short*100:.0f}% (vs {buy_ratio_long*100:.0f}% baseline) — buyers in control, ride momentum.")
        if buy_ratio_short < 1 - thresh and delta_short < 0 and active:
            tier = "HIGH" if buy_ratio_long > buy_ratio_short else "MOD"
            return StrategyResult(bias="BEAR", tier=tier, entry_price=price, stop_loss=round(price + atr * sl_mult, 2),
                                  tp1=round(price - atr * tp_mult, 2), tp2=round(price - atr * tp_mult * 1.6, 2),
                                  reasoning=f"Buy aggression {buy_ratio_short*100:.0f}% (vs {buy_ratio_long*100:.0f}% baseline) — sellers in control, ride downside.")
        return StrategyResult(bias="NEUTRAL", reasoning=f"Aggression {buy_ratio_short*100:.0f}% — tape balanced, no edge.")
