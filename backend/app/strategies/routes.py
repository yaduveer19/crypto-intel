import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.auth.routes import get_current_user
from app.auth.models import User, UserStrategy, TradeSignal
from app.strategies.engine import get_all_strategies, get_strategy
from app.ingestion.binance_client import BinanceClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("/list")
def list_strategies():
    return get_all_strategies()


class StrategyConfig(BaseModel):
    strategy_key: str
    symbol: str
    is_enabled: bool = True
    params: Optional[dict] = None


@router.post("/configure")
def configure_strategy(body: StrategyConfig, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    strat = get_strategy(body.strategy_key)
    if not strat:
        raise HTTPException(404, "Strategy not found")

    existing = db.query(UserStrategy).filter(
        UserStrategy.user_id == user.id,
        UserStrategy.strategy_key == body.strategy_key,
        UserStrategy.symbol == body.symbol.upper(),
    ).first()

    if existing:
        existing.is_enabled = body.is_enabled
        if body.params:
            existing.params = {**strat.default_params, **body.params}
        existing.updated_at = None
    else:
        entry = UserStrategy(
            user_id=user.id,
            strategy_key=body.strategy_key,
            symbol=body.symbol.upper(),
            is_enabled=body.is_enabled,
            params={**strat.default_params, **(body.params or {})},
        )
        db.add(entry)

    db.commit()
    return {"status": "ok", "message": f"Strategy '{body.strategy_key}' configured for {body.symbol.upper()}"}


@router.get("/my")
def get_my_strategies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(UserStrategy).filter(UserStrategy.user_id == user.id).all()
    all_strats = {s["key"]: s for s in get_all_strategies()}
    result = []
    for r in rows:
        info = all_strats.get(r.strategy_key, {})
        result.append({
            "id": r.id,
            "strategy_key": r.strategy_key,
            "name": info.get("name", r.strategy_key),
            "description": info.get("description", ""),
            "symbol": r.symbol,
            "is_enabled": r.is_enabled,
            "params": r.params or info.get("default_params", {}),
        })
    return result


class ManualSignal(BaseModel):
    symbol: str
    bias: str
    tier: str = "MOD"
    entry_price: float
    stop_loss: float
    tp1: float
    tp2: float
    reasoning: str = ""


@router.post("/signal/manual")
def create_manual_signal(body: ManualSignal, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    signal = TradeSignal(
        user_id=user.id,
        strategy_key="manual",
        symbol=body.symbol.upper(),
        bias=body.bias.upper(),
        tier=body.tier.upper(),
        entry_price=int(body.entry_price),
        stop_loss=int(body.stop_loss),
        tp1=int(body.tp1),
        tp2=int(body.tp2),
        reasoning=body.reasoning,
    )
    db.add(signal)
    db.commit()

    # Deliver via Telegram if connected
    from app.telegram.delivery import deliver_signal
    try:
        deliver_signal(user.id, signal, db)
    except Exception as e:
        logger.warning(f"[signal] telegram delivery failed: {e}")

    return {"status": "ok", "signal_id": signal.id}


@router.get("/signals")
def get_my_signals(user: User = Depends(get_current_user), db: Session = Depends(get_db), limit: int = 50):
    signals = db.query(TradeSignal).filter(
        TradeSignal.user_id == user.id
    ).order_by(TradeSignal.created_at.desc()).limit(limit).all()

    return [
        {
            "id": s.id,
            "strategy": s.strategy_key,
            "symbol": s.symbol,
            "bias": s.bias,
            "tier": s.tier,
            "entry": s.entry_price,
            "sl": s.stop_loss,
            "tp1": s.tp1,
            "tp2": s.tp2,
            "reasoning": s.reasoning,
            "delivered_telegram": s.delivered_telegram,
            "time": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signals
    ]


@router.post("/run-all")
def run_all_strategies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Run all enabled strategies for the user and generate signals"""
    strat_configs = db.query(UserStrategy).filter(
        UserStrategy.user_id == user.id,
        UserStrategy.is_enabled == True,
    ).all()

    if not strat_configs:
        raise HTTPException(400, "No enabled strategies configured")

    client = BinanceClient()
    results = []

    for sc in strat_configs:
        strat = get_strategy(sc.strategy_key)
        if not strat:
            continue
        try:
            klines = client.get_klines(sc.symbol, "1h", 100)
            if len(klines) < 30:
                continue
            result = strat.analyze(sc.symbol, klines, sc.params)
            if result.bias != "NEUTRAL" and result.entry_price:
                signal = TradeSignal(
                    user_id=user.id,
                    strategy_key=sc.strategy_key,
                    symbol=sc.symbol,
                    bias=result.bias,
                    tier=result.tier,
                    entry_price=int(result.entry_price),
                    stop_loss=int(result.stop_loss) if result.stop_loss else None,
                    tp1=int(result.tp1) if result.tp1 else None,
                    tp2=int(result.tp2) if result.tp2 else None,
                    reasoning=result.reasoning,
                )
                db.add(signal)
                db.commit()

                from app.telegram.delivery import deliver_signal
                try:
                    deliver_signal(user.id, signal, db)
                except:
                    pass

                results.append({
                    "strategy": sc.strategy_key,
                    "symbol": sc.symbol,
                    "bias": result.bias,
                    "tier": result.tier,
                })
        except Exception as e:
            logger.error(f"[strategy] run error {sc.strategy_key}/{sc.symbol}: {e}")

    return {"status": "ok", "signals_generated": len(results), "results": results}
