import json
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import text
from app.database import SessionLocal
from app.config import settings
from app.models.signals import Verdict, LaneAccuracy
from app.ingestion.binance_client import BinanceClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior crypto trading strategist. Your job is to synthesize outputs from 4 independent analysis lanes into a single actionable trading verdict.

For each lane you are given:
- lane name
- bias (BULL/BEAR/NEUTRAL)
- confidence tier (HIGH/MOD/LOW)
- signals (array of text descriptions)
- lane's historical win rate (0.0 to 1.0)

Rules:
1. Evaluate each lane's signal weighted by its historical accuracy
2. Consider the current price and ATR for stop-loss placement
3. Entry price should be within 0.5% of current price
4. SL should be ~1.5-2x ATR from entry (opposite direction)
5. TP1 should be 1:1.5 risk:reward from entry, TP2 should be 1:3
6. If bias inconsistency across lanes, reduce confidence tier
7. If 3+ lanes agree with HIGH confidence, output HIGH tier
8. NEVER invent data — use only what's provided

Output STRICT JSON only, no markdown, no explanations:
{
  "bias": "BULL|BEAR|NEUTRAL",
  "tier": "HIGH|MOD|LOW",
  "entry_price": float,
  "stop_loss": float,
  "tp1": float,
  "tp2": float,
  "reasoning": "1-2 sentence synthesis",
  "weighted_score": float
}"""


class Synthesizer:
    def get_lane_outputs(self, symbol: str) -> list:
        db = SessionLocal()
        try:
            rows = db.query(LaneOutput).filter(
                LaneOutput.symbol.in_([symbol, "GLOBAL"]),
            ).order_by(LaneOutput.time.desc()).limit(20).all()
            return rows
        finally:
            db.close()

    def get_accuracy_weights(self) -> dict:
        db = SessionLocal()
        try:
            rows = db.query(LaneAccuracy).all()
            return {r.lane: r.win_rate for r in rows}
        finally:
            db.close()

    def generate_verdict(self, symbol: str) -> dict:
        binance = BinanceClient()
        current_price = binance.get_current_price(symbol)

        klines = binance.get_klines(symbol, "1h", 20)
        atr = 0
        if len(klines) > 14:
            try:
                import pandas as pd
                import pandas_ta as ta
                df = pd.DataFrame(klines)
                atr_series = ta.atr(df["high"].astype(float), df["low"].astype(float), df["close"].astype(float), length=14)
                atr = float(atr_series.iloc[-1]) if atr_series is not None and not pd.isna(atr_series.iloc[-1]) else current_price * 0.02
            except:
                atr = current_price * 0.02

        atr = atr or current_price * 0.02

        lane_outputs = self.get_lane_outputs(f"{symbol.split('USDT')[0]}USDT")
        lane_outputs += self.get_lane_outputs("GLOBAL")

        weights = self.get_accuracy_weights()

        lanes_data = {}
        for lo in lane_outputs:
            if lo.lane not in lanes_data:
                lanes_data[lo.lane] = {
                    "lane": lo.lane,
                    "bias": lo.bias,
                    "tier": lo.tier,
                    "signals": lo.signals if lo.signals else [],
                    "win_rate": weights.get(lo.lane, 0.5),
                }

        if not lanes_data:
            return self._fallback_verdict(symbol, current_price, atr, "No lane data available")

        llm_input = {
            "symbol": symbol,
            "current_price": current_price,
            "atr": round(atr, 2),
            "lanes": list(lanes_data.values()),
        }

        try:
            response = httpx.post(
                f"{settings.llm_api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(llm_input, indent=2)},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                timeout=30,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                content = content.strip().replace("```json", "").replace("```", "").strip()
                result = json.loads(content)
                return {
                    "symbol": symbol,
                    "bias": result.get("bias", "NEUTRAL"),
                    "tier": result.get("tier", "LOW"),
                    "entry_price": result.get("entry_price", current_price),
                    "stop_loss": result.get("stop_loss", current_price - atr * 2),
                    "tp1": result.get("tp1", current_price + atr * 3),
                    "tp2": result.get("tp2", current_price + atr * 6),
                    "reasoning": result.get("reasoning", ""),
                    "lane_breakdown": lanes_data,
                    "atr": round(atr, 2),
                    "current_price": current_price,
                }
            else:
                logger.warning(f"[synthesizer] LLM error: {response.status_code} {response.text[:200]}")
        except Exception as e:
            logger.error(f"[synthesizer] LLM call failed: {e}")

        return self._fallback_verdict(symbol, current_price, atr, "LLM unavailable — rule-based fallback")

    def _fallback_verdict(self, symbol: str, price: float, atr: float, reason: str) -> dict:
        lane_outputs = self.get_lane_outputs(f"{symbol.split('USDT')[0]}USDT")
        lane_outputs += self.get_lane_outputs("GLOBAL")

        bull_count = sum(1 for lo in lane_outputs if lo.bias == "BULL")
        bear_count = sum(1 for lo in lane_outputs if lo.bias == "BEAR")

        if bull_count > bear_count:
            bias = "BULL"
            sl = price - atr * 2
            tp1 = price + atr * 3
            tp2 = price + atr * 6
        elif bear_count > bull_count:
            bias = "BEAR"
            sl = price + atr * 2
            tp1 = price - atr * 3
            tp2 = price - atr * 6
        else:
            bias = "NEUTRAL"
            sl = price - atr * 1.5
            tp1 = price + atr * 2
            tp2 = price + atr * 4

        high_count = sum(1 for lo in lane_outputs if lo.bias == bias and lo.tier == "HIGH")
        tier = "HIGH" if high_count >= 2 else ("MOD" if bias != "NEUTRAL" else "LOW")

        return {
            "symbol": symbol,
            "bias": bias,
            "tier": tier,
            "entry_price": price,
            "stop_loss": round(sl, 2),
            "tp1": round(tp1, 2),
            "tp2": round(tp2, 2),
            "reasoning": reason,
            "lane_breakdown": [{"lane": lo.lane, "bias": lo.bias, "tier": lo.tier} for lo in lane_outputs[:8]],
            "atr": round(atr, 2),
            "current_price": price,
        }

    def save_verdict(self, db, verdict: dict):
        entry = Verdict(
            time=datetime.now(timezone.utc),
            symbol=verdict["symbol"],
            bias=verdict["bias"],
            tier=verdict["tier"],
            entry_price=verdict.get("entry_price"),
            stop_loss=verdict.get("stop_loss"),
            tp1=verdict.get("tp1"),
            tp2=verdict.get("tp2"),
            reasoning=verdict.get("reasoning", ""),
            lane_breakdown=verdict.get("lane_breakdown", {}),
        )
        db.add(entry)
        db.commit()
