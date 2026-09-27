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
    RULES_VERSION: str = "1"

    R01_WINDOW_SECONDS: int = 60
    R01_MIN_COUNT: int = 3

    R02_WINDOW_MINUTES: int = 10
    R02_FALLBACK_COUNT: int = 10
    R02_BASELINE_MULTIPLIER: float = 3.0

    R03_WINDOW_MINUTES: int = 2
    R03_FALLBACK_SENDERS: int = 5
    R03_AMOUNT_SIMILARITY: float = 0.98
    R03_NEW_SENDER_SHARE: float = 0.6

    R04_WINDOW_MINUTES: int = 10
    R04_FALLBACK_RECIPIENTS: int = 5

    R05_MIN_HISTORY: int = 5
    R05_ROBUST_Z: float = 5.0
    R05_MEDIAN_MULTIPLIER: float = 3.0

    R06_WINDOW_MINUTES: int = 5
    R06_MIN_COUNT: int = 8
    R06_MAX_AMOUNT: float = 100.0
    R06_DAILY_MULTIPLIER: float = 3.0

    R07_DORMANT_DAYS: int = 30
    R07_MIN_COUNT: int = 3
    R07_MEDIAN_MULTIPLIER: float = 5.0

    R08_WINDOW_MINUTES: int = 30
    R08_FORWARD_RATIO: float = 0.8
    R08_RETAINED_RATIO: float = 0.1

    R09_WINDOW_MINUTES: int = 15
    R09_MAX_HOPS: int = 4

    R10_WINDOW_MINUTES: int = 30
    R10_MIN_HOPS: int = 3
    R10_FORWARD_RATIO: float = 0.8

    R11_WINDOW_MINUTES: int = 10
    R11_FALLBACK_COUNT: int = 5

    R12_WINDOW_HOURS: int = 24
    R12_CONCENTRATION: float = 0.7
    R12_MIN_COUNT: int = 4

    BASELINE_DAYS: int = 30
    BASELINE_MIN_HISTORY: int = 5
    NEW_ACCOUNT_DAYS: int = 7
    MATURE_ACCOUNT_DAYS: int = 30
    CONTEXT_REDUCTION: int = 10
    CONTEXT_REDUCTION_CAP: int = 30
    FAMILY_BONUS_TWO: int = 10
    FAMILY_BONUS_THREE: int = 20
    FALSE_POSITIVE_LOOKBACK_DAYS: int = 90
    ALERT_DEDUP_MINUTES: int = 30
    HOLD_MAX_DAYS: int = 60
    HOLD_EXPLANATION_DAYS: int = 20
    ML_SIGNAL_CAP: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
