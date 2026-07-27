from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, calculate_atr


@register_strategy
class BreakoutStrategy(BaseStrategy):
    @property
    def key(self) -> str: return "breakout"
    @property
    def name(self) -> str: return "Breakout"
    @property
    def description(self) -> str: return "Bollinger Band breakout — price breaking above/below bands with volume"
    @property
    def default_params(self) -> dict: return {"band_period": 20, "band_std": 2.0, "atr_multiplier_sl": 2.0, "atr_multiplier_tp": 3.0}

    def analyze(self, symbol: str, ohlcv: list, params: dict = None) -> StrategyResult:
        p = {**self.default_params, **(params or {})}
        closes = [c["close"] for c in ohlcv]
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        if len(closes) < p["band_period"] + 5:
            return StrategyResult(reasoning="Insufficient data")

        recent = closes[-p["band_period"]:]
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        std = variance ** 0.5

        upper = mean + p["band_std"] * std
        lower = mean - p["band_std"] * std
        current_price = closes[-1]
        prev_price = closes[-2] if len(closes) > 1 else current_price
        atr = calculate_atr(highs, lows, closes)

        # Check volume surge (using range as volume proxy)
        current_range = highs[-1] - lows[-1]
        avg_range = sum(highs[i] - lows[i] for i in range(-p["band_period"], 0)) / p["band_period"]
        volume_surge = current_range > avg_range * 1.3

        if current_price > upper and prev_price <= upper and volume_surge:
            entry = current_price
            sl = entry - atr * p["atr_multiplier_sl"]
            tp1 = entry + atr * p["atr_multiplier_tp"]
            tp2 = entry + atr * p["atr_multiplier_tp"] * 2
            return StrategyResult(bias="BULL", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning="Breakout: price broke above upper Bollinger Band with volume.", signals=["Upper band breakout", "Volume surge detected"])
        elif current_price < lower and prev_price >= lower and volume_surge:
            entry = current_price
            sl = entry + atr * p["atr_multiplier_sl"]
            tp1 = entry - atr * p["atr_multiplier_tp"]
            tp2 = entry - atr * p["atr_multiplier_tp"] * 2
            return StrategyResult(bias="BEAR", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning="Breakout: price broke below lower Bollinger Band with volume.", signals=["Lower band breakdown", "Volume surge detected"])
        elif current_price > upper:
            return StrategyResult(bias="BULL", tier="MOD", signals=["Price above upper band (no volume confirmation)"], reasoning="Breakout: above upper band but no volume confirmation.")
        elif current_price < lower:
            return StrategyResult(bias="BEAR", tier="MOD", signals=["Price below lower band (no volume confirmation)"], reasoning="Breakout: below lower band but no volume confirmation.")

        return StrategyResult(reasoning=f"Breakout: price within bands (upper: ${upper:.0f}, lower: ${lower:.0f}).", signals=[f"Upper: ${upper:.0f}, Lower: ${lower:.0f}"])
