from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class Settings(BaseModel):
    app_name: str = Field(default=os.getenv("APP_NAME", "GoldHelm AI API"))
    app_env: str = Field(default=os.getenv("APP_ENV", "development"))
    api_prefix: str = Field(default=os.getenv("API_PREFIX", ""))
    news_rss_url: str | None = Field(default=os.getenv("NEWS_RSS_URL"))
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:3000,http://localhost:5173",
            ).split(",")
            if origin.strip()
        ]
    )
    data_lookback_days: int = Field(default=int(os.getenv("DATA_LOOKBACK_DAYS", "180")))
    model_min_rows: int = Field(default=int(os.getenv("MODEL_MIN_ROWS", "45")))
    data_cache_ttl_seconds: int = Field(default=int(os.getenv("DATA_CACHE_TTL_SECONDS", "1800")))
    data_fetch_retry_cooldown_seconds: int = Field(
        default=int(os.getenv("DATA_FETCH_RETRY_COOLDOWN_SECONDS", "900"))
    )
    news_cache_ttl_seconds: int = Field(default=int(os.getenv("NEWS_CACHE_TTL_SECONDS", "1800")))
    news_article_limit: int = Field(default=int(os.getenv("NEWS_ARTICLE_LIMIT", "12")))
    gold_ticker: str = Field(default=os.getenv("GOLD_TICKER", "GC=F"))
    model_random_state: int = Field(default=int(os.getenv("MODEL_RANDOM_STATE", "42")))
    rl_training_episodes: int = Field(default=int(os.getenv("RL_TRAINING_EPISODES", "35")))
    rl_initial_cash: float = Field(default=float(os.getenv("RL_INITIAL_CASH", "10000")))
    rl_model_path: str = Field(
        default=os.getenv(
            "RL_MODEL_PATH",
            str((Path(__file__).resolve().parents[2] / "artifacts" / "q_agent.pkl")),
        )
    )
    database_url: str | None = Field(default=os.getenv("DATABASE_URL"))
    news_keywords: list[str] = Field(
        default_factory=lambda: [
            keyword.strip().lower()
            for keyword in os.getenv(
                "NEWS_KEYWORDS",
                "gold,inflation,federal reserve,interest rates,usd",
            ).split(",")
            if keyword.strip()
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
