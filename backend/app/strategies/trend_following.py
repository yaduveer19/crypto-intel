from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, ema, calculate_atr


@register_strategy
class TrendFollowingStrategy(BaseStrategy):
    @property
    def key(self) -> str: return "trend_following"
    @property
    def name(self) -> str: return "Trend Following"
    @property
    def description(self) -> str: return "EMA crossover trend strategy — buy when fast EMA crosses above slow EMA"
    @property
    def default_params(self) -> dict: return {"fast_period": 9, "slow_period": 21, "atr_multiplier_sl": 2.0, "atr_multiplier_tp": 3.0}

    def analyze(self, symbol: str, ohlcv: list, params: dict = None) -> StrategyResult:
        p = {**self.default_params, **(params or {})}
        closes = [c["close"] for c in ohlcv]
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        if len(closes) < p["slow_period"] + 5:
            return StrategyResult(reasoning="Insufficient data")

        fast_ema = ema(closes, p["fast_period"])
        slow_ema = ema(closes, p["slow_period"])
        current_price = closes[-1]
        atr = calculate_atr(highs, lows, closes)

        prev_fast = ema(closes[:-1], p["fast_period"])
        prev_slow = ema(closes[:-1], p["slow_period"])

        signals = []

        if prev_fast <= prev_slow and fast_ema > slow_ema:
            entry = current_price
            sl = entry - atr * p["atr_multiplier_sl"]
            tp1 = entry + atr * p["atr_multiplier_tp"]
            tp2 = entry + atr * p["atr_multiplier_tp"] * 2
            signals.append(f"Bullish crossover: EMA{p['fast_period']} crossed above EMA{p['slow_period']}")
            return StrategyResult(bias="BULL", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning=f"Trend Following: bullish crossover detected. Price trending up.", signals=signals)
        elif prev_fast >= prev_slow and fast_ema < slow_ema:
            entry = current_price
            sl = entry + atr * p["atr_multiplier_sl"]
            tp1 = entry - atr * p["atr_multiplier_tp"]
            tp2 = entry - atr * p["atr_multiplier_tp"] * 2
            signals.append(f"Bearish crossover: EMA{p['fast_period']} crossed below EMA{p['slow_period']}")
            return StrategyResult(bias="BEAR", tier="HIGH", entry_price=entry, stop_loss=round(sl, 2), tp1=round(tp1, 2), tp2=round(tp2, 2),
                                  reasoning=f"Trend Following: bearish crossover detected. Price trending down.", signals=signals)

        if fast_ema > slow_ema:
            tier = "MOD"
            signals.append(f"EMA{p['fast_period']} above EMA{p['slow_period']} — uptrend intact")
        else:
            tier = "MOD"
            signals.append(f"EMA{p['fast_period']} below EMA{p['slow_period']} — downtrend intact")

        return StrategyResult(bias="NEUTRAL", tier=tier, reasoning="Trend Following: no crossover signal.", signals=signals)
