import json
import logging
import httpx
from datetime import datetime, timezone
from app.ingestion.news_client import NewsClient
from app.models.signals import LaneOutput
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a crypto narrative analyst. Analyze the following news headlines and determine the overall market narrative bias.

Rules:
1. Classify the overall sentiment as BULL, BEAR, or NEUTRAL
2. Rate confidence as HIGH, MOD, or LOW
3. Extract key themes (e.g., "regulation", "adoption", "hack", "ETF", "macro")
4. Return ONLY valid JSON with no markdown formatting

Output schema:
{"lane": "narrative", "bias": "BULL|BEAR|NEUTRAL", "tier": "HIGH|MOD|LOW", "themes": ["theme1", "theme2"], "reasoning": "1-sentence summary"}"""


class NarrativeLane:
    def __init__(self):
        self.news_client = NewsClient()

    def analyze(self) -> dict:
        headlines = self.news_client.get_headlines(20)

        if not headlines:
            return {
                "lane": "narrative",
                "symbol": "GLOBAL",
                "bias": "NEUTRAL",
                "tier": "LOW",
                "signals": ["No headlines available"],
                "themes": [],
                "reasoning": "No news data",
            }

        titles = [h["title"] for h in headlines[:15]]
        headlines_text = "\n".join(f"- {t}" for t in titles)

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
                        {"role": "user", "content": f"Analyze these crypto headlines:\n\n{headlines_text}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
                timeout=30,
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                content = content.strip().replace("```json", "").replace("```", "").strip()
                result = json.loads(content)
                result["signals"] = result.get("themes", [])
                result["symbol"] = "GLOBAL"
                logger.info(f"[narrative] LLM result: {result['bias']}/{result['tier']}")
                return result
            else:
                logger.warning(f"[narrative] LLM API error: {response.status_code} {response.text[:200]}")
        except Exception as e:
            logger.error(f"[narrative] LLM call failed: {e}")

        # Fallback: simple keyword-based
        keywords_bull = ["bull", "surge", "rally", "upgrade", "adoption", "inflow", "approval", "breakthrough"]
        keywords_bear = ["bear", "crash", "hack", "ban", "regulat", "scam", "dump", "fraud", "investigation"]

        bull_count = sum(1 for t in titles if any(k in t.lower() for k in keywords_bull))
        bear_count = sum(1 for t in titles if any(k in t.lower() for k in keywords_bear))

        if bull_count > bear_count + 2:
            bias = "BULL"
        elif bear_count > bull_count + 2:
            bias = "BEAR"
        else:
            bias = "NEUTRAL"

        return {
            "lane": "narrative",
            "symbol": "GLOBAL",
            "bias": bias,
            "tier": "LOW",
            "signals": [f"Bull keywords: {bull_count}", f"Bear keywords: {bear_count}"],
            "themes": [],
            "reasoning": "Keyword-based fallback",
        }

    def save_output(self, db, result: dict):
        entry = LaneOutput(
            time=datetime.now(timezone.utc),
            symbol="GLOBAL",
            lane="narrative",
            bias=result["bias"],
            tier=result["tier"],
            signals=result.get("signals", result.get("themes", [])),
            raw_data=result,
        )
        db.add(entry)
        db.commit()
