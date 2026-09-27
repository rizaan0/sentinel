"""Eight named accounts reused by every scenario. Account numbers stay fixed."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import SignupRequest
from app.services.auth_service import signup_user
from app.services.pin_service import set_pin

DEMO_PASSWORD = "scenario-demo-pass"
DEMO_PIN = "1111"

# key, full name, email, permanent account number
MEMBERS: tuple[tuple[str, str, str, str], ...] = (
    ("meera", "Meera Shah", "meera.shah@sentinel.demo", "100000000001"),
    ("arjun", "Arjun Shah", "arjun.shah@sentinel.demo", "100000000002"),
    ("kabir", "Kabir Menon", "kabir.menon@sentinel.demo", "100000000003"),
    ("nia", "Nia D'Souza", "nia.dsouza@sentinel.demo", "100000000004"),
    ("rohan", "Rohan Iyer", "rohan.iyer@sentinel.demo", "100000000005"),
    ("sara", "Sara Qureshi", "sara.qureshi@sentinel.demo", "100000000006"),
    ("dev", "Dev Patel", "dev.patel@sentinel.demo", "100000000007"),
    ("leela", "Leela Nair", "leela.nair@sentinel.demo", "100000000008"),
)


def ensure_cast(db: Session) -> dict[str, User]:
    found: dict[str, User] = {}
    for key, name, email, number in MEMBERS:
        user = db.execute(select(User).where(User.account_number == number)).scalar_one_or_none()
        if user is None:
            user = signup_user(
                db,
                SignupRequest(full_name=name, email=email, password=DEMO_PASSWORD),
            )
            user.account_number = number
            user.created_at = datetime.now(UTC) - timedelta(days=60)
            db.commit()
            db.refresh(user)
            set_pin(db, user, DEMO_PIN)
        found[key] = user
    return found


def cast_size(db: Session) -> int:
    numbers = [number for _, _, _, number in MEMBERS]
    return db.execute(
        select(func.count()).select_from(User).where(User.account_number.in_(numbers))
    ).scalar_one()
