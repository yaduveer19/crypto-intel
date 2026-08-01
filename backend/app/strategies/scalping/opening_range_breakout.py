"""Opening Range Breakout — trade the first range of the session; break of range = momentum continues."""

from datetime import datetime, timezone
from app.strategies.engine import BaseStrategy, StrategyResult, register_strategy, calculate_atr


@register_strategy
class OpeningRangeBreakoutStrategy(BaseStrategy):
    @property
    def key(self): return "opening_range_breakout"

    @property
    def name(self): return "Opening Range Breakout"

    @property
    def description(self):
        return "Trade the opening range — enter on breakout with volume, exit on range target"

    @property
    def default_params(self):
        return {"range_minutes": 15, "range_lookback": 1, "atr_multiplier_sl": 1.5, "atr_multiplier_tp": 2.5}

    def _find_session(self, klines, range_minutes):
        """Group klines into sessions (UTC 00:00 boundaries), return first candles of current session."""
        if not klines:
            return []
        try:
            session_ts = []
            for k in klines:
                dt = datetime.fromtimestamp(k["time"], tz=timezone.utc)
                session_ts.append(dt)
            current_day = session_ts[-1].date()
            session_klines = [k for k, dt in zip(klines, session_ts) if dt.date() == current_day]
            if len(session_klines) < 2:
                return []
            step = max(int(range_minutes / (session_klines[1]["time"] - session_klines[0]["time"])), 1)
            return session_klines[:max(step, 1)]
        except Exception:
            return []

    def analyze(self, symbol, ohlcv, params=None, **kwargs):
        params = {**self.default_params, **(params or {})}
        if not ohlcv or len(ohlcv) < 10:
            return StrategyResult(bias="NEUTRAL", reasoning="Not enough data for ORB")
        orb = self._find_session(ohlcv, params["range_minutes"])
        if not orb or len(orb) < 2:
            return StrategyResult(bias="NEUTRAL", reasoning="Opening range not yet formed — waiting for session open")
        range_high = max(k["high"] for k in orb)
        range_low = min(k["low"] for k in orb)
        last = ohlcv[-1]
        price = last["close"]
        atr = calculate_atr([k["high"] for k in ohlcv], [k["low"] for k in ohlcv], [k["close"] for k in ohlcv], 14)
        avg_vol = sum((k.get("volume", 0) or 0) for k in ohlcv[-20:]) / 20
        vol_confirm = (last.get("volume", 0) or 0) > avg_vol * 1.2
        sl_mult, tp_mult = params["atr_multiplier_sl"], params["atr_multiplier_tp"]

        if price > range_high:
            tier = "HIGH" if vol_confirm else "MOD"
            return StrategyResult(bias="BULL", tier=tier, entry_price=price, stop_loss=round(range_high - atr * sl_mult, 2),
                                  tp1=round(price + atr * tp_mult, 2), tp2=round(price + atr * tp_mult * 1.8, 2),
                                  reasoning=f"Broke above opening range high {range_high:.2f}{' with volume' if vol_confirm else ''} — momentum long.")
        if price < range_low:
            tier = "HIGH" if vol_confirm else "MOD"
            return StrategyResult(bias="BEAR", tier=tier, entry_price=price, stop_loss=round(range_low + atr * sl_mult, 2),
                                  tp1=round(price - atr * tp_mult, 2), tp2=round(price - atr * tp_mult * 1.8, 2),
                                  reasoning=f"Broke below opening range low {range_low:.2f}{' with volume' if vol_confirm else ''} — momentum short.")
        return StrategyResult(bias="NEUTRAL", reasoning=f"Inside opening range ({range_low:.2f}–{range_high:.2f}) — wait for breakout.")
