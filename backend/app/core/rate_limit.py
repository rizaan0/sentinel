"""
Simple Redis-backed sliding-window-ish rate limiter (fixed window via
INCR + EXPIRE). Used to slow down credential-stuffing / brute-force
attempts against login, independent of the Transaction PIN's own lockout.
"""
import redis as redis_sync

from app.core.config import settings

_client: redis_sync.Redis | None = None


def _get_client() -> redis_sync.Redis:
    global _client
    if _client is None:
        _client = redis_sync.Redis.from_url(settings.REDIS_URL)
    return _client


class RateLimitExceededError(Exception):
    pass


def check_and_increment(key: str, max_attempts: int, window_seconds: int) -> None:
    """
    Raises RateLimitExceededError if `key` has been hit more than
    `max_attempts` times within `window_seconds`. Fails open (does not
    block the request) if Redis itself is unavailable - rate limiting is a
    defense-in-depth measure, not the primary auth guarantee.
    """
    try:
        client = _get_client()
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
        if count > max_attempts:
            raise RateLimitExceededError("Too many attempts. Please try again in a few minutes.")
    except redis_sync.RedisError:
        return
