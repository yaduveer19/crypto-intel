from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM
    llm_api_key: str = "sk-BP2U8RoftMRtikEphIw2d8QB0PtUYnYmlPhLylvMuVnJVNDf"
    llm_api_base: str = "https://apihub.agnes-ai.com/v1"
    llm_model: str = "agnes-2.0-flash"

    # Database
    database_url: str = "postgresql://cryptouser:cryptopass@postgres:5432/cryptodb"
    database_url_async: Optional[str] = None

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # APIs
    cryptopanic_api_key: Optional[str] = None
    newsapi_key: Optional[str] = None
    whalealert_api_key: Optional[str] = None
    fred_api_key: Optional[str] = None

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Symbols
    symbols: list = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    @property
    def async_database_url(self) -> str:
        if self.database_url_async:
            return self.database_url_async
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
