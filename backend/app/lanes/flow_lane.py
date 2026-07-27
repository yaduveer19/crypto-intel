import logging
from datetime import datetime, timezone
from app.ingestion.binance_client import BinanceClient
from app.models.signals import LaneOutput

logger = logging.getLogger(__name__)


class FlowLane:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.client = BinanceClient()

    def analyze(self) -> dict:
        current_price = self.client.get_current_price(self.symbol)

        funding_data = self.client.get_funding_rate(self.symbol, 5)
        avg_funding = sum(f["rate"] for f in funding_data) / len(funding_data) if funding_data else 0

        oi_data = self.client.get_open_interest(self.symbol)
        oi_value = oi_data["oi"]

        signals = []
        bias_votes = []

        # Funding rate analysis
        if avg_funding > 0.0005:
            funding_bias = "BEAR"
            funding_tier = "HIGH"
            signals.append(f"Funding high positive ({avg_funding:.6f}) — longs crowded")
        elif avg_funding > 0.0001:
            funding_bias = "BEAR"
            funding_tier = "LOW"
            signals.append(f"Funding slightly positive ({avg_funding:.6f})")
        elif avg_funding < -0.0005:
            funding_bias = "BULL"
            funding_tier = "HIGH"
            signals.append(f"Funding negative ({avg_funding:.6f}) — shorts paying premium")
        elif avg_funding < -0.0001:
            funding_bias = "BULL"
            funding_tier = "LOW"
            signals.append(f"Funding slightly negative ({avg_funding:.6f})")
        else:
            funding_bias = "NEUTRAL"
            funding_tier = "MOD"
            signals.append(f"Funding neutral ({avg_funding:.6f})")

        bias_votes.append((funding_bias, funding_tier))

        # Open Interest analysis
        if oi_value > 500_000:
            oi_bias = "BEAR"
            oi_tier = "LOW"
            signals.append(f"High OI ({oi_value:,.0f}) — elevated leverage")
        elif oi_value > 200_000:
            oi_bias = "NEUTRAL"
            oi_tier = "MOD"
            signals.append(f"Moderate OI ({oi_value:,.0f})")
        else:
            oi_bias = "BULL"
            oi_tier = "LOW"
            signals.append(f"Low OI ({oi_value:,.0f}) — room for inflows")

        bias_votes.append((oi_bias, oi_tier))

        # Aggregation
        bull = sum(1 for b, _ in bias_votes if b == "BULL")
        bear = sum(1 for b, _ in bias_votes if b == "BEAR")

        if bull > bear:
            final_bias = "BULL"
        elif bear > bull:
            final_bias = "BEAR"
        else:
            final_bias = "NEUTRAL"

        high_count = sum(1 for b, t in bias_votes if b == final_bias and t == "HIGH")
        final_tier = "HIGH" if high_count >= 1 else ("MOD" if final_bias != "NEUTRAL" else "LOW")

        return {
            "lane": "flow",
            "symbol": self.symbol,
            "bias": final_bias,
            "tier": final_tier,
            "signals": signals,
            "avg_funding": round(avg_funding, 8),
            "open_interest": oi_value,
            "current_price": current_price,
        }

    def save_output(self, db, result: dict):
        entry = LaneOutput(
            time=datetime.now(timezone.utc),
            symbol=self.symbol,
            lane="flow",
            bias=result["bias"],
            tier=result["tier"],
            signals=result.get("signals", []),
            raw_data=result,
        )
        db.add(entry)
        db.commit()
