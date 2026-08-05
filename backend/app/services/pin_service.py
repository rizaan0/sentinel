"""
Transaction PIN business logic: setup and PIN-based transfer authorization,
including brute-force lockout (Architecture Rule: business logic lives only
in backend services).
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_pin
from app.core.security import verify_pin as _verify_pin_hash
from app.models.pin_credential import PinCredential
from app.models.user import User


class PinAlreadySetError(Exception):
    pass


class PinNotSetError(Exception):
    pass


class PinLockedError(Exception):
    pass


class InvalidPinError(Exception):
    pass


def set_pin(db: Session, user: User, pin: str) -> PinCredential:
    if user.pin_credential is not None:
        raise PinAlreadySetError("Transaction PIN is already set for this account")

    credential = PinCredential(user_id=user.id, pin_hash=hash_pin(pin))
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def verify_transaction_pin(db: Session, user: User, pin: str) -> None:
    """
    Verifies the given PIN against the user's stored credential, enforcing
    a lockout window after too many failed attempts. Raises on any failure;
    callers should treat any exception here as "transaction not authorized".
    """
    credential = user.pin_credential
    if credential is None:
        raise PinNotSetError("Transaction PIN has not been set for this account")

    now = datetime.now(UTC)
    if credential.locked_until is not None and credential.locked_until > now:
        raise PinLockedError(
            "Too many incorrect PIN attempts. "
            f"Try again after {credential.locked_until.isoformat()}"
        )

    if not _verify_pin_hash(pin, credential.pin_hash):
        credential.failed_attempts += 1
        if credential.failed_attempts >= settings.PIN_MAX_ATTEMPTS:
            credential.locked_until = now + timedelta(minutes=settings.PIN_LOCKOUT_MINUTES)
            credential.failed_attempts = 0
        db.add(credential)
        db.commit()
        raise InvalidPinError("Incorrect transaction PIN")

    # Success: reset attempt counter.
    credential.failed_attempts = 0
    credential.locked_until = None
    db.add(credential)
    db.commit()
