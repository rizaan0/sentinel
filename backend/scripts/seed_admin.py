"""
Seeds a single admin user. There is no public admin signup endpoint by
design (idea.md describes admins as operators of the platform, not
self-registering users), so this script is the only way to create one.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\seed_admin.py \\
        --email admin@sentinel.local --password changeme123 --full-name "Sentinel Admin"
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.base import Base  # noqa: E402,F401  (registers all models with the ORM registry)
from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.schemas.auth import SignupRequest  # noqa: E402
from app.services.auth_service import EmailAlreadyRegisteredError, signup_user  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a Sentinel admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default="Sentinel Admin")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        payload = SignupRequest(full_name=args.full_name, email=args.email, password=args.password)
        user = signup_user(db, payload, role=UserRole.ADMIN)
        print(f"Created admin '{user.email}' with account number {user.account_number}")
    except EmailAlreadyRegisteredError as exc:
        print(f"Skipped: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
