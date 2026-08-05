"""
Auth business logic: user registration and authentication.

Architecture Rule: business logic lives only in backend services.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.auth import SignupRequest
from app.services.account_service import generate_unique_account_number
from app.services.ledger_service import record_genesis_credit


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def signup_user(db: Session, payload: SignupRequest, role: UserRole = UserRole.USER) -> User:
    if get_user_by_email(db, payload.email) is not None:
        raise EmailAlreadyRegisteredError(f"Email already registered: {payload.email}")

    account_number = generate_unique_account_number(db)

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        account_number=account_number,
        role=role,
    )
    db.add(user)
    db.flush()  # populate user.id before creating the wallet

    wallet = Wallet(user_id=user.id, balance=settings.INITIAL_BALANCE)
    db.add(wallet)
    db.flush()  # populate wallet defaults before recording the genesis ledger entry

    record_genesis_credit(db, wallet)

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Incorrect email or password")
    if not user.is_active:
        raise InvalidCredentialsError("Account is inactive")
    return user
