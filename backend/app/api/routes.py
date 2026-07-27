import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.database import get_db
from app.models.signals import Verdict, LaneOutput, Position, OHLC
from app.synthesizer.synthesizer import Synthesizer
from app.ingestion.binance_client import BinanceClient
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


@router.get("/verdict/{symbol}")
def get_verdict(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    latest = db.query(Verdict).filter(
        Verdict.symbol == symbol
    ).order_by(desc(Verdict.time)).first()

    if not latest:
        raise HTTPException(404, f"No verdict for {symbol}")

    return {
        "symbol": symbol,
        "time": latest.time.isoformat(),
        "bias": latest.bias,
        "tier": latest.tier,
        "entry_price": latest.entry_price,
        "stop_loss": latest.stop_loss,
        "tp1": latest.tp1,
        "tp2": latest.tp2,
        "reasoning": latest.reasoning,
    }


@router.get("/lanes/{symbol}")
def get_lanes(symbol: str, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    lanes = db.query(LaneOutput).filter(
        LaneOutput.symbol.in_([symbol, "GLOBAL"]),
        LaneOutput.time > datetime.now(timezone.utc).timestamp() - 3600,
    ).order_by(desc(LaneOutput.time)).limit(20).all()

    result = {}
    for lane in lanes:
        key = lane.lane
        if key not in result or lane.time > result[key]["time"]:
            result[key] = {
                "lane": lane.lane,
                "symbol": lane.symbol,
                "bias": lane.bias,
                "tier": lane.tier,
                "signals": lane.signals if lane.signals else [],
                "time": lane.time.isoformat(),
            }

    return list(result.values())


@router.get("/price/{symbol}")
def get_price(symbol: str):
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    try:
        client = BinanceClient()
        price = client.get_current_price(symbol)
        return {"symbol": symbol, "price": price}
    except Exception as e:
        raise HTTPException(500, f"Price fetch failed: {e}")


@router.post("/copilot")
async def copilot_chat(body: dict):
    message = body.get("message", "")
    symbol = body.get("symbol", "BTCUSDT").upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    client = BinanceClient()
    try:
        current_price = client.get_current_price(symbol)
        price_context = f"Current {symbol} price is ${current_price:.2f}."
    except:
        current_price = None
        price_context = ""

    try:
        import httpx
        response = httpx.post(
            f"{settings.llm_api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are Crypto Intel AI — a elite crypto trading assistant and market analyst. "
                                   f"You have deep expertise in: technical analysis (RSI, MACD, EMA, Bollinger Bands, support/resistance), "
                                   f"on-chain metrics (whale moves, exchange flows, fee revenue), derivatives (funding rates, OI, liquidation levels), "
                                   f"macro (DXY, Fed policy, gold correlation), and crypto narratives (ETF flows, regulation, L1/L2 trends). "
                                   f"{price_context} "
                                   f"Today is {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}. "
                                   f"Current active strategies on platform: Trend Following (EMA crossover), RSI Mean Reversion, "
                                   f"MACD Momentum, Breakout (Bollinger Bands), Grid Levels (S/R zones). "
                                   f"Rules: Be confident, data-driven, and specific. Use real price levels and indicators. "
                                   f"Analyze markets like a professional trader — reference support/resistance, order flow, and market structure. "
                                   f"If user asks non-crypto questions, still answer helpfully but steer toward trading insights. "
                                   f"Always include: '⚠️ Not financial advice. DYOR.' at the end of trading analysis.",
                    },
                    {"role": "user", "content": message},
                ],
                "temperature": 0.5,
                "max_tokens": 800,
            },
            timeout=30,
        )

        if response.status_code == 200:
            reply = response.json()["choices"][0]["message"]["content"]
            return {"reply": reply, "context_price": current_price}
        else:
            return {"reply": f"LLM API error ({response.status_code}): {response.text[:200]}", "context_price": current_price}
    except Exception as e:
        return {"reply": f"Service unavailable: {str(e)}", "context_price": current_price}


@router.post("/simulate")
def run_simulation(body: dict):
    from app.lanes.scenario_simulator import ScenarioSimulator

    symbol = body.get("symbol", "BTCUSDT").upper()
    shock_pct = float(body.get("shock_pct", -5))
    portfolio_value = float(body.get("portfolio_value", 10000))

    sim = ScenarioSimulator()
    result = sim.run(symbol, shock_pct, portfolio_value)
    return result


@router.get("/signals/history")
def get_signal_history(symbol: str = "BTCUSDT", limit: int = 50, db: Session = Depends(get_db)):
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    verdicts = db.query(Verdict).filter(
        Verdict.symbol == symbol
    ).order_by(desc(Verdict.time)).limit(limit).all()

    return [
        {
            "time": v.time.isoformat(),
            "bias": v.bias,
            "tier": v.tier,
            "entry": v.entry_price,
            "sl": v.stop_loss,
            "tp1": v.tp1,
            "tp2": v.tp2,
        }
        for v in verdicts
    ]
