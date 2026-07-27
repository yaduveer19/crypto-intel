import logging
from datetime import datetime, timezone
from app.ingestion.macro_client import MacroClient
from app.models.signals import LaneOutput

logger = logging.getLogger(__name__)


class MacroLane:
    def __init__(self):
        self.client = MacroClient()

    def analyze(self) -> dict:
        dxy = self.client.get_dxy()
        gold = self.client.get_gold()
        fng = self.client.get_fear_greed()

        signals = []
        bias_votes = []

        # DXY analysis
        if dxy is not None:
            if dxy > 105:
                signals.append(f"DXY {dxy:.2f} — strong USD, risk-off")
                bias_votes.append(("BEAR", "HIGH"))
            elif dxy > 103:
                signals.append(f"DXY {dxy:.2f} — moderate USD")
                bias_votes.append(("BEAR", "LOW"))
            elif dxy < 100:
                signals.append(f"DXY {dxy:.2f} — weak USD, risk-on")
                bias_votes.append(("BULL", "HIGH"))
            elif dxy < 102:
                signals.append(f"DXY {dxy:.2f} — leaning weak")
                bias_votes.append(("BULL", "LOW"))
            else:
                signals.append(f"DXY {dxy:.2f} — neutral")
                bias_votes.append(("NEUTRAL", "MOD"))
        else:
            bias_votes.append(("NEUTRAL", "LOW"))

        # Gold analysis
        if gold is not None:
            if gold > 2400:
                signals.append(f"Gold ${gold:.0f} — elevated, risk hedging")
                bias_votes.append(("BULL", "MOD"))
            elif gold > 2200:
                signals.append(f"Gold ${gold:.0f} — moderate")
                bias_votes.append(("NEUTRAL", "LOW"))
            elif gold < 2000:
                signals.append(f"Gold ${gold:.0f} — low, risk-on appetite")
                bias_votes.append(("BULL", "LOW"))
            else:
                signals.append(f"Gold ${gold:.0f} — neutral")
                bias_votes.append(("NEUTRAL", "LOW"))

        # Fear & Greed
        if fng is not None:
            if fng["value"] > 80:
                signals.append(f"F&G {fng['value']} — extreme greed, caution")
                bias_votes.append(("BEAR", "HIGH"))
            elif fng["value"] > 60:
                signals.append(f"F&G {fng['value']} — greedy")
                bias_votes.append(("NEUTRAL", "LOW"))
            elif fng["value"] < 20:
                signals.append(f"F&G {fng['value']} — extreme fear, buying opp")
                bias_votes.append(("BULL", "HIGH"))
            elif fng["value"] < 40:
                signals.append(f"F&G {fng['value']} — fearful")
                bias_votes.append(("BULL", "LOW"))
            else:
                signals.append(f"F&G {fng['value']} — neutral")
                bias_votes.append(("NEUTRAL", "MOD"))

        # Aggregate
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
            "lane": "macro",
            "symbol": "GLOBAL",
            "bias": final_bias,
            "tier": final_tier,
            "signals": signals,
            "dxy": dxy,
            "gold": gold,
            "fear_greed": fng,
        }

    def save_output(self, db, result: dict):
        entry = LaneOutput(
            time=datetime.now(timezone.utc),
            symbol="GLOBAL",
            lane="macro",
            bias=result["bias"],
            tier=result["tier"],
            signals=result.get("signals", []),
            raw_data=result,
        )
        db.add(entry)
        db.commit()
