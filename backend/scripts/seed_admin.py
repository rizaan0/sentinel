"""
Seeds a single admin user. There is no public admin signup endpoint by
design (idea.md describes admins as operators of the platform, not
self-registering users), so this script is the only way to create one.

If the email already belongs to an admin, the password (and full name) are
updated so re-running the script always restores known credentials — the
previous "Skipped: already registered" behavior left admins unreachable
whenever the original password was forgotten or never matched the README.

Usage (from backend/):
    ..\\.venv\\Scripts\\python.exe scripts\\seed_admin.py \\
        --email admin@sentinel.app --password ChangeMe123 --full-name "Sentinel Admin"
"""
import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.base import Base  # noqa: E402,F401  (registers all models with the ORM registry)
from app.db.session import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.schemas.auth import SignupRequest  # noqa: E402
from app.services.auth_service import (  # noqa: E402
    get_user_by_email,
    normalize_email,
    set_user_password,
    signup_user,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a Sentinel admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", default="Sentinel Admin")
    args = parser.parse_args()

    email = normalize_email(args.email)
    db = SessionLocal()
    try:
        existing = get_user_by_email(db, email)
        if existing is not None:
            if existing.role != UserRole.ADMIN:
                print(f"Error: '{email}' exists but is not an admin (role={existing.role}).")
                sys.exit(1)
            existing.full_name = args.full_name.strip()
            set_user_password(db, existing, args.password)
            print(f"Updated admin '{existing.email}' password (account {existing.account_number})")
            return

        payload = SignupRequest(full_name=args.full_name, email=email, password=args.password)
        user = signup_user(db, payload, role=UserRole.ADMIN)
        print(f"Created admin '{user.email}' with account number {user.account_number}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
