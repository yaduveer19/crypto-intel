"""Shared LLM helper — tries current models in order, returns reply text or None.
The AGNES model list rotates; never hardcode a single model."""
import httpx

LLM_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
LLM_KEY = "sk-BP2U8RoftMRtikEphIw2d8QB0PtUYnYmlPhLylvMuVnJVNDf"
MODELS = ["agnes-3.0-flash", "agnes-2.5-flash", "agnes-2.5-pro-beta"]


def chat(messages: list, temperature: float = 0.4, max_tokens: int = 800,
         timeout: float = 45.0) -> str | None:
    """First working model wins. None when every model fails."""
    for model in MODELS:
        try:
            r = httpx.post(
                LLM_URL,
                headers={"Authorization": f"Bearer {LLM_KEY}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
                timeout=timeout,
            )
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"]
                if content:
                    return content
        except Exception:
            continue
    return None
