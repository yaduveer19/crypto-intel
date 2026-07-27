from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, calculate_atr


@register_strategy
class GridLevelsStrategy(BaseStrategy):
    @property
    def key(self) -> str: return "grid_levels"
    @property
    def name(self) -> str: return "Grid Levels"
    @property
    def description(self) -> str: return "Support/resistance grid — identifies key levels for range trading"
    @property
    def default_params(self) -> dict: return {"lookback": 50, "grid_levels": 5, "atr_multiplier_sl": 1.5, "atr_multiplier_tp": 2.0}

    def analyze(self, symbol: str, ohlcv: list, params: dict = None) -> StrategyResult:
        p = {**self.default_params, **(params or {})}
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        closes = [c["close"] for c in ohlcv]
        if len(closes) < p["lookback"]:
            return StrategyResult(reasoning="Insufficient data")

        recent_highs = highs[-p["lookback"]:]
        recent_lows = lows[-p["lookback"]:]
        current_price = closes[-1]
        atr = calculate_atr(highs, lows, closes)

        resistance = sum(sorted(recent_highs, reverse=True)[:3]) / 3
        support = sum(sorted(recent_lows)[:3]) / 3
        mid = (resistance + support) / 2

        grid_step = (resistance - support) / (p["grid_levels"] + 1)
        levels = [round(support + i * grid_step, 2) for i in range(p["grid_levels"] + 2)]

        signals = [f"Support: ${support:.0f}", f"Resistance: ${resistance:.0f}", f"Grid: {len(levels)} levels"]

        if current_price <= support * 1.01:
            entry = current_price
            sl = entry - atr * p["atr_multiplier_sl"]
            tp1 = entry + atr * p["atr_multiplier_tp"]
            tp2 = resistance
            return StrategyResult(bias="BULL", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning=f"Grid Levels: price near support ${support:.0f}. Bounce play active.", signals=signals)
        elif current_price >= resistance * 0.99:
            entry = current_price
            sl = entry + atr * p["atr_multiplier_sl"]
            tp1 = entry - atr * p["atr_multiplier_tp"]
            tp2 = support
            return StrategyResult(bias="BEAR", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning=f"Grid Levels: price near resistance ${resistance:.0f}. Reversal play active.", signals=signals)
        elif current_price < mid:
            return StrategyResult(bias="BULL", tier="MOD", signals=signals, reasoning=f"Grid Levels: price below midpoint. Bias bullish.")
        else:
            return StrategyResult(bias="BEAR", tier="MOD", signals=signals, reasoning=f"Grid Levels: price above midpoint. Bias bearish.")
