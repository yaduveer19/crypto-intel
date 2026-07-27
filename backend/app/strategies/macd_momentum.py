from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, ema, calculate_atr


@register_strategy
class MACDMomentumStrategy(BaseStrategy):
    @property
    def key(self) -> str: return "macd_momentum"
    @property
    def name(self) -> str: return "MACD Momentum"
    @property
    def description(self) -> str: return "MACD line vs signal line crossovers with histogram confirmation"
    @property
    def default_params(self) -> dict: return {"fast": 12, "slow": 26, "signal": 9, "atr_multiplier_sl": 1.8, "atr_multiplier_tp": 3.0}

    def analyze(self, symbol: str, ohlcv: list, params: dict = None) -> StrategyResult:
        p = {**self.default_params, **(params or {})}
        closes = [c["close"] for c in ohlcv]
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        if len(closes) < p["slow"] + p["signal"] + 5:
            return StrategyResult(reasoning="Insufficient data")

        fast_ema = ema(closes, p["fast"])
        slow_ema = ema(closes, p["slow"])
        macd_line = fast_ema - slow_ema

        # Build MACD history for signal line
        macd_values = []
        for i in range(p["slow"], len(closes)):
            fe = ema(closes[:i + 1], p["fast"])
            se = ema(closes[:i + 1], p["slow"])
            macd_values.append(fe - se)

        signal_line = ema(macd_values, p["signal"]) if len(macd_values) >= p["signal"] else 0
        histogram = macd_line - signal_line

        # Previous values for crossover detection
        prev_macd_values = macd_values[:-1] if len(macd_values) > 1 else []
        prev_signal = ema(prev_macd_values, p["signal"]) if len(prev_macd_values) >= p["signal"] else 0
        prev_hist = (macd_values[-2] if len(macd_values) > 1 else 0) - prev_signal if len(macd_values) > 1 else 0

        current_price = closes[-1]
        atr = calculate_atr(highs, lows, closes)

        if prev_hist <= 0 and histogram > 0:
            entry = current_price
            sl = entry - atr * p["atr_multiplier_sl"]
            tp1 = entry + atr * p["atr_multiplier_tp"]
            tp2 = entry + atr * p["atr_multiplier_tp"] * 2
            return StrategyResult(bias="BULL", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning="MACD Momentum: bullish crossover with rising histogram.", signals=["MACD bull cross", "Histogram turning positive"])
        elif prev_hist >= 0 and histogram < 0:
            entry = current_price
            sl = entry + atr * p["atr_multiplier_sl"]
            tp1 = entry - atr * p["atr_multiplier_tp"]
            tp2 = entry - atr * p["atr_multiplier_tp"] * 2
            return StrategyResult(bias="BEAR", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning="MACD Momentum: bearish crossover with falling histogram.", signals=["MACD bear cross", "Histogram turning negative"])

        return StrategyResult(reasoning="MACD Momentum: no crossover signal.", signals=[f"MACD histogram: {histogram:+.4f}"])
