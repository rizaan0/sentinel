"""
Central application configuration.

Architecture Rule: PostgreSQL is the single source of truth. All services read
their connection details from here rather than hardcoding values.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "Sentinel"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_ENV"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    PIN_MAX_ATTEMPTS: int = 5
    PIN_LOCKOUT_MINUTES: int = 15
    LOGIN_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_MINUTES: int = 15

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://sentinel:sentinel@127.0.0.1:5433/sentinel"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TRANSACTION_CHANNEL: str = "sentinel:transaction_events"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Ollama (AI Investigation Assistant) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0

    # --- Business rules ---
    INITIAL_BALANCE: float = 1000.0
    ACCOUNT_NUMBER_LENGTH: int = 12

    # --- Scheduled jobs ---
    RECONCILIATION_INTERVAL_MINUTES: int = 15
    PREDICTION_INTERVAL_MINUTES: int = 30

    # --- Rule-based fraud detection (Monitoring Engine) ---
    RAPID_REPEAT_WINDOW_SECONDS: int = 60
    RAPID_REPEAT_MIN_COUNT: int = 3

    CIRCULAR_FLOW_WINDOW_MINUTES: int = 15
    CIRCULAR_FLOW_MAX_HOPS: int = 4

    LARGE_TRANSFER_STDDEV_MULTIPLIER: float = 3.0
    LARGE_TRANSFER_MIN_HISTORY: int = 3

    BURST_WINDOW_MINUTES: int = 5
    BURST_MIN_COUNT: int = 5
    BURST_MAX_AMOUNT: float = 100.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
