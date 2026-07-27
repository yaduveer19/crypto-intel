import logging
from datetime import datetime, timezone
from app.ingestion.binance_client import BinanceClient

logger = logging.getLogger(__name__)

CORRELATION_MATRIX = {
    "BTCUSDT": {"ETHUSDT": 0.82, "SOLUSDT": 0.68, "gold": 0.15},
    "ETHUSDT": {"BTCUSDT": 0.82, "SOLUSDT": 0.74, "gold": 0.12},
    "SOLUSDT": {"BTCUSDT": 0.68, "ETHUSDT": 0.74, "gold": 0.08},
}


class ScenarioSimulator:
    def __init__(self):
        self.client = BinanceClient()

    def run(self, symbol: str, shock_pct: float = -5, portfolio_value: float = 10000) -> dict:
        current_price = self.client.get_current_price(symbol)
        shock_decimal = shock_pct / 100

        # Own impact
        impacted_price = current_price * (1 + shock_decimal)
        pnl_pct = shock_pct
        pnl_usd = portfolio_value * abs(shock_decimal) * (-1 if shock_decimal < 0 else 1)

        # Cross-asset impact
        correlations = CORRELATION_MATRIX.get(symbol, {})
        cross_impacts = []
        for other_sym, corr in correlations.items():
            if other_sym == "gold":
                continue
            try:
                other_price = self.client.get_current_price(other_sym)
                other_impact = shock_decimal * corr
                cross_impacts.append({
                    "symbol": other_sym,
                    "current_price": other_price,
                    "correlation": corr,
                    "estimated_move_pct": round(other_impact * 100, 2),
                    "estimated_price": round(other_price * (1 + other_impact), 2),
                })
            except Exception as e:
                logger.warning(f"[sim] cross-asset fetch error for {other_sym}: {e}")

        # Check stop levels
        from app.database import SessionLocal
        from app.models.signals import Position

        db = SessionLocal()
        triggered_stops = []
        try:
            positions = db.query(Position).filter(
                Position.symbol == symbol,
                Position.status == "open",
            ).all()
            for pos in positions:
                if pos.side == "LONG" and impacted_price <= pos.stop_loss:
                    triggered_stops.append({
                        "position_id": pos.id,
                        "side": pos.side,
                        "entry": pos.entry_price,
                        "stop": pos.stop_loss,
                        "impacted_price": round(impacted_price, 2),
                        "loss_pct": round((impacted_price - pos.entry_price) / pos.entry_price * 100, 2),
                    })
                elif pos.side == "SHORT" and impacted_price >= pos.stop_loss:
                    triggered_stops.append({
                        "position_id": pos.id,
                        "side": pos.side,
                        "entry": pos.entry_price,
                        "stop": pos.stop_loss,
                        "impacted_price": round(impacted_price, 2),
                        "loss_pct": round((pos.entry_price - impacted_price) / pos.entry_price * 100, 2),
                    })
        finally:
            db.close()

        return {
            "scenario": f"{shock_pct:+.1f}% shock on {symbol}",
            "current_price": current_price,
            "impacted_price": round(impacted_price, 2),
            "portfolio_impact_pct": round(pnl_pct, 2),
            "portfolio_impact_usd": round(pnl_usd, 2),
            "cross_asset_impact": cross_impacts,
            "stop_losses_triggered": triggered_stops,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "This is a simplified correlation-based simulation, not financial advice.",
        }
