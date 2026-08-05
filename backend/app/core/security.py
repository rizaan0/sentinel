"""
Security primitives: password hashing, PIN hashing, and JWT issuance/verification.

Architecture Rule: business logic lives only in backend services; this module
provides the low-level cryptographic primitives services build on.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Two independent hashing contexts: passwords and PINs are conceptually
# different credentials (login vs. transaction authorization) and are never
# mixed, even though they use the same bcrypt scheme under the hood.
_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_pin_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---- Passwords ----
def hash_password(password: str) -> str:
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_context.verify(password, password_hash)


# ---- Transaction PIN ----
def hash_pin(pin: str) -> str:
    return _pin_context.hash(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    return _pin_context.verify(pin, pin_hash)


# ---- JWT ----
def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError (or subclasses) on invalid/expired tokens."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
