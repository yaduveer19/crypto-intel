import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime, timezone
from app.ingestion.binance_client import BinanceClient
from app.models.signals import LaneOutput

logger = logging.getLogger(__name__)


class TechnicalLane:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.client = BinanceClient()

    def _calc_rsi_bias(self, rsi_val: float) -> tuple:
        if rsi_val > 70:
            return ("BEAR", "HIGH", f"RSI {rsi_val:.1f} — overbought")
        elif rsi_val > 60:
            return ("BEAR", "LOW", f"RSI {rsi_val:.1f} — nearing overbought")
        elif rsi_val < 30:
            return ("BULL", "HIGH", f"RSI {rsi_val:.1f} — oversold")
        elif rsi_val < 40:
            return ("BULL", "LOW", f"RSI {rsi_val:.1f} — nearing oversold")
        else:
            return ("NEUTRAL", "MOD", f"RSI {rsi_val:.1f} — neutral range")

    def _calc_macd_bias(self, macd_line: float, signal: float, histogram: float) -> tuple:
        if macd_line > signal and histogram > 0:
            return ("BULL", "HIGH", "MACD bull cross + momentum up")
        elif macd_line > signal:
            return ("BULL", "LOW", "MACD above signal")
        elif macd_line < signal and histogram < 0:
            return ("BEAR", "HIGH", "MACD bear cross + momentum down")
        elif macd_line < signal:
            return ("BEAR", "LOW", "MACD below signal")
        return ("NEUTRAL", "MOD", "MACD flat")

    def _calc_ema_bias(self, price: float, ema200: float) -> tuple:
        if price > ema200 * 1.05:
            return ("BULL", "HIGH", f"Price ${price:.2f} > EMA200 ${ema200:.2f}")
        elif price > ema200:
            return ("BULL", "LOW", f"Price ${price:.2f} near EMA200 ${ema200:.2f}")
        elif price < ema200 * 0.95:
            return ("BEAR", "HIGH", f"Price ${price:.2f} < EMA200 ${ema200:.2f}")
        elif price < ema200:
            return ("BEAR", "LOW", f"Price ${price:.2f} below EMA200 ${ema200:.2f}")
        return ("NEUTRAL", "MOD", "Price at EMA200")

    def _calc_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        atr = ta.atr(df["high"], df["low"], df["close"], length=period)
        return float(atr.iloc[-1]) if not atr.empty and not pd.isna(atr.iloc[-1]) else df["close"].iloc[-1] * 0.02

    def analyze(self) -> dict:
        klines = self.client.get_klines(self.symbol, "1h", 200)
        if len(klines) < 50:
            logger.warning(f"[technical] {self.symbol}: insufficient data ({len(klines)} rows)")
            return {"lane": "technical", "symbol": self.symbol, "bias": "NEUTRAL", "tier": "LOW", "signals": ["insufficient data"], "atr": 0}

        df = pd.DataFrame(klines)
        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        rsi = ta.rsi(close, length=14)
        macd = ta.macd(close)
        ema200 = ta.ema(close, length=200)

        current_price = float(close.iloc[-1])
        rsi_val = float(rsi.iloc[-1]) if rsi is not None and not pd.isna(rsi.iloc[-1]) else 50
        ema200_val = float(ema200.iloc[-1]) if ema200 is not None and not pd.isna(ema200.iloc[-1]) else current_price
        atr = self._calc_atr(df)

        rsi_bias, rsi_tier, rsi_sig = self._calc_rsi_bias(rsi_val)
        ema_bias, ema_tier, ema_sig = self._calc_ema_bias(current_price, ema200_val)

        if macd is not None and "MACD_12_26_9" in macd.columns:
            macd_line = float(macd["MACD_12_26_9"].iloc[-1])
            macd_signal = float(macd["MACDs_12_26_9"].iloc[-1])
            macd_hist = float(macd["MACDh_12_26_9"].iloc[-1])
            macd_bias, macd_tier, macd_sig = self._calc_macd_bias(macd_line, macd_signal, macd_hist)
        else:
            macd_bias, macd_tier, macd_sig = "NEUTRAL", "LOW", "MACD unavailable"

        biases = [rsi_bias, ema_bias, macd_bias]
        bull_count = biases.count("BULL")
        bear_count = biases.count("BEAR")

        if bull_count >= 2:
            final_bias = "BULL"
            high_count = sum(1 for b, t in [(rsi_bias, rsi_tier), (ema_bias, ema_tier), (macd_bias, macd_tier)] if b == "BULL" and t == "HIGH")
            final_tier = "HIGH" if high_count >= 2 else "MOD"
        elif bear_count >= 2:
            final_bias = "BEAR"
            high_count = sum(1 for b, t in [(rsi_bias, rsi_tier), (ema_bias, ema_tier), (macd_bias, macd_tier)] if b == "BEAR" and t == "HIGH")
            final_tier = "HIGH" if high_count >= 2 else "MOD"
        else:
            final_bias = "NEUTRAL"
            final_tier = "MOD"

        return {
            "lane": "technical",
            "symbol": self.symbol,
            "bias": final_bias,
            "tier": final_tier,
            "signals": [rsi_sig, ema_sig, macd_sig],
            "atr": round(atr, 2),
            "current_price": current_price,
            "rsi": round(rsi_val, 1),
            "ema200": round(ema200_val, 2),
        }

    def save_output(self, db, result: dict):
        entry = LaneOutput(
            time=datetime.now(timezone.utc),
            symbol=self.symbol,
            lane="technical",
            bias=result["bias"],
            tier=result["tier"],
            signals=result.get("signals", []),
            raw_data=result,
        )
        db.add(entry)
        db.commit()
