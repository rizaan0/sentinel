"""
Account number generation.

Sentinel uses its own account-number identifier system instead of phone
numbers, so users can send/receive ST Coins without any real banking
information (per idea.md).
"""
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User


def _generate_candidate() -> str:
    length = settings.ACCOUNT_NUMBER_LENGTH
    low = 10 ** (length - 1)
    high = (10**length) - 1
    return str(random.randint(low, high))


def generate_unique_account_number(db: Session, max_attempts: int = 20) -> str:
    for _ in range(max_attempts):
        candidate = _generate_candidate()
        exists = db.execute(
            select(User.id).where(User.account_number == candidate)
        ).scalar_one_or_none()
        if exists is None:
            return candidate
    raise RuntimeError("Could not generate a unique account number; account space exhausted")
