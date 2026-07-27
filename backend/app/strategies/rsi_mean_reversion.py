from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, rsi, calculate_atr


@register_strategy
class RSIMeanReversionStrategy(BaseStrategy):
    @property
    def key(self) -> str: return "rsi_mean_reversion"
    @property
    def name(self) -> str: return "RSI Mean Reversion"
    @property
    def description(self) -> str: return "Buy oversold, sell overbought — RSI-based mean reversion"
    @property
    def default_params(self) -> dict: return {"rsi_period": 14, "oversold": 30, "overbought": 70, "atr_multiplier_sl": 1.5, "atr_multiplier_tp": 2.5}

    def analyze(self, symbol: str, ohlcv: list, params: dict = None) -> StrategyResult:
        p = {**self.default_params, **(params or {})}
        closes = [c["close"] for c in ohlcv]
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        if len(closes) < p["rsi_period"] + 5:
            return StrategyResult(reasoning="Insufficient data")

        rsi_val = rsi(closes, p["rsi_period"])
        current_price = closes[-1]
        atr = calculate_atr(highs, lows, closes)

        if rsi_val < p["oversold"]:
            entry = current_price
            sl = entry - atr * p["atr_multiplier_sl"]
            tp1 = entry + atr * p["atr_multiplier_tp"]
            tp2 = entry + atr * p["atr_multiplier_tp"] * 2
            return StrategyResult(bias="BULL", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning=f"RSI Mean Reversion: RSI {rsi_val:.1f} — oversold bounce expected.", signals=[f"RSI {rsi_val:.1f} < {p['oversold']}"])
        elif rsi_val > p["overbought"]:
            entry = current_price
            sl = entry + atr * p["atr_multiplier_sl"]
            tp1 = entry - atr * p["atr_multiplier_tp"]
            tp2 = entry - atr * p["atr_multiplier_tp"] * 2
            return StrategyResult(bias="BEAR", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning=f"RSI Mean Reversion: RSI {rsi_val:.1f} — overbought pullback expected.", signals=[f"RSI {rsi_val:.1f} > {p['overbought']}"])
        elif rsi_val < 40:
            return StrategyResult(bias="BULL", tier="MOD", entry_price=current_price, signals=[f"RSI {rsi_val:.1f} — nearing oversold"],
                                  reasoning=f"RSI Mean Reversion: RSI {rsi_val:.1f} — leaning bullish.")
        elif rsi_val > 60:
            return StrategyResult(bias="BEAR", tier="MOD", entry_price=current_price, signals=[f"RSI {rsi_val:.1f} — nearing overbought"],
                                  reasoning=f"RSI Mean Reversion: RSI {rsi_val:.1f} — leaning bearish.")
        return StrategyResult(reasoning=f"RSI {rsi_val:.1f} — neutral range.", signals=[f"RSI {rsi_val:.1f}"])
