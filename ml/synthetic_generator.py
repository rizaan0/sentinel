"""
Synthetic Transaction Generator.

Simulates normal users transacting ordinarily, plus a smaller set of
"suspicious personas" enacting the four behavioral patterns idea.md
describes (rapid repeated transfers, circular fund flow, unusually large
transfers, bursts of small transactions) - run against the *real* backend
transaction pipeline (signup -> PIN -> transfer), so the Monitoring Engine
evaluates them exactly as it would real user behavior.

Persona labels are written to a CSV for offline ML evaluation only; they
are never stored in the production schema (fraud emerges from behavior,
never from labels, per idea.md and the Architecture Rules).

Usage (from backend/, so `app` is importable with the right DATABASE_URL):
    ..\\.venv\\Scripts\\python.exe ..\\ml\\synthetic_generator.py
"""
import argparse
import csv
import random
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

import app.main  # noqa: F401  (registers the Monitoring Engine as an event subscriber)
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.fraud_alert import FraudAlert
from app.models.ledger_entry import LedgerEntry
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.auth import SignupRequest
from app.schemas.transaction import TransferRequest
from app.services.auth_service import signup_user
from app.services.pin_service import set_pin
from app.services.transfer_service import execute_transfer
from sqlalchemy import select

DEFAULT_PIN = "1234"


@dataclass
class SyntheticUser:
    user: User
    persona: str


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@synthetic.sentinel.app"


def _create_user(db, persona: str, full_name: str) -> SyntheticUser:
    user = signup_user(
        db,
        SignupRequest(full_name=full_name, email=_unique_email(persona), password="Synthetic123!"),
        role=UserRole.USER,
    )
    set_pin(db, user, DEFAULT_PIN)
    return SyntheticUser(user=user, persona=persona)


def _backdate_transaction(db, transaction_id: str, when: datetime) -> None:
    """
    Rewrites the timestamp of a transaction (and its ledger entries/fraud
    alert) after the fact, so the synthetic dataset spans a realistic
    historical window. Rule evaluation already happened in real time during
    generation - this only changes how the record *looks* historically for
    feature engineering / training.
    """
    tx = db.execute(select(Transaction).where(Transaction.transaction_id == transaction_id)).scalar_one()
    tx.created_at = when
    db.add(tx)

    for entry in db.execute(select(LedgerEntry).where(LedgerEntry.transaction_id == tx.id)).scalars():
        entry.created_at = when
        db.add(entry)

    for alert in db.execute(select(FraudAlert).where(FraudAlert.transaction_id == tx.id)).scalars():
        alert.created_at = when
        db.add(alert)

    db.commit()


def _random_backdate(days_back: int) -> datetime:
    now = datetime.now(timezone.utc)
    offset = timedelta(
        days=random.uniform(0, days_back),
        hours=random.uniform(0, 24),
    )
    return now - offset


def generate_normal_activity(
    db, users: list[SyntheticUser], transfers_per_user: tuple[int, int], days_back: int, labels: list[dict]
) -> None:
    for su in users:
        count = random.randint(*transfers_per_user)
        for _ in range(count):
            recipient = random.choice([u for u in users if u.user.id != su.user.id])
            amount = Decimal(str(round(random.uniform(5, 200), 2)))
            try:
                tx = execute_transfer(
                    db,
                    su.user,
                    TransferRequest(
                        recipient_account_number=recipient.user.account_number,
                        amount=amount,
                        remark="synthetic normal activity",
                        pin=DEFAULT_PIN,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  skipped transfer (e.g. insufficient balance): {exc}")
                continue
            _backdate_transaction(db, tx.transaction_id, _random_backdate(days_back))
            labels.append(
                {"transaction_id": tx.transaction_id, "account_number": su.user.account_number, "persona": "normal"}
            )


def generate_rapid_repeat_persona(db, days_back: int, labels: list[dict]) -> None:
    attacker = _create_user(db, "rapid_repeat", "Rapid Repeat Attacker")
    counterparty = _create_user(db, "rapid_repeat", "Rapid Repeat Counterparty")
    window_anchor = _random_backdate(days_back)

    for _ in range(random.randint(4, 6)):
        amount = Decimal(str(round(random.uniform(20, 60), 2)))
        tx = execute_transfer(
            db,
            attacker.user,
            TransferRequest(
                recipient_account_number=counterparty.user.account_number,
                amount=amount,
                remark="synthetic rapid repeat",
                pin=DEFAULT_PIN,
            ),
        )
        _backdate_transaction(db, tx.transaction_id, window_anchor)
        labels.append(
            {"transaction_id": tx.transaction_id, "account_number": attacker.user.account_number, "persona": "rapid_repeat"}
        )


def generate_circular_flow_persona(db, days_back: int, labels: list[dict]) -> None:
    ring = [_create_user(db, "circular_flow", f"Circular Flow {i}") for i in range(3)]
    window_anchor = _random_backdate(days_back)

    for i in range(len(ring)):
        sender = ring[i]
        receiver = ring[(i + 1) % len(ring)]
        amount = Decimal(str(round(random.uniform(50, 150), 2)))
        tx = execute_transfer(
            db,
            sender.user,
            TransferRequest(
                recipient_account_number=receiver.user.account_number,
                amount=amount,
                remark="synthetic circular flow",
                pin=DEFAULT_PIN,
            ),
        )
        _backdate_transaction(db, tx.transaction_id, window_anchor)
        labels.append(
            {"transaction_id": tx.transaction_id, "account_number": sender.user.account_number, "persona": "circular_flow"}
        )


def generate_large_outlier_persona(db, days_back: int, labels: list[dict]) -> None:
    attacker = _create_user(db, "large_outlier", "Large Outlier Sender")
    recipient = _create_user(db, "large_outlier", "Large Outlier Recipient")
    window_anchor = _random_backdate(days_back)

    for _ in range(3):
        amount = Decimal(str(round(random.uniform(10, 30), 2)))
        tx = execute_transfer(
            db,
            attacker.user,
            TransferRequest(
                recipient_account_number=recipient.user.account_number,
                amount=amount,
                remark="synthetic baseline",
                pin=DEFAULT_PIN,
            ),
        )
        _backdate_transaction(db, tx.transaction_id, window_anchor - timedelta(days=random.uniform(1, 5)))

    outlier_amount = Decimal(str(round(random.uniform(600, 950), 2)))
    tx = execute_transfer(
        db,
        attacker.user,
        TransferRequest(
            recipient_account_number=recipient.user.account_number,
            amount=outlier_amount,
            remark="synthetic large outlier",
            pin=DEFAULT_PIN,
        ),
    )
    _backdate_transaction(db, tx.transaction_id, window_anchor)
    labels.append(
        {"transaction_id": tx.transaction_id, "account_number": attacker.user.account_number, "persona": "large_outlier"}
    )


def generate_burst_persona(db, days_back: int, labels: list[dict]) -> None:
    attacker = _create_user(db, "burst_small", "Burst Attacker")
    recipients = [_create_user(db, "burst_small", f"Burst Recipient {i}") for i in range(5)]
    window_anchor = _random_backdate(days_back)

    for recipient in recipients:
        amount = Decimal(str(round(random.uniform(5, 20), 2)))
        tx = execute_transfer(
            db,
            attacker.user,
            TransferRequest(
                recipient_account_number=recipient.user.account_number,
                amount=amount,
                remark="synthetic burst",
                pin=DEFAULT_PIN,
            ),
        )
        _backdate_transaction(db, tx.transaction_id, window_anchor)
        labels.append(
            {"transaction_id": tx.transaction_id, "account_number": attacker.user.account_number, "persona": "burst_small"}
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic Sentinel transaction data.")
    parser.add_argument("--normal-users", type=int, default=30)
    parser.add_argument("--transfers-min", type=int, default=3)
    parser.add_argument("--transfers-max", type=int, default=8)
    parser.add_argument("--suspicious-groups", type=int, default=5, help="how many of each suspicious persona group")
    parser.add_argument("--days-back", type=int, default=30)
    parser.add_argument(
        "--labels-out",
        type=str,
        default=str(Path(__file__).resolve().parent / "artifacts" / "persona_labels.csv"),
    )
    args = parser.parse_args()

    db = SessionLocal()
    labels: list[dict] = []
    try:
        print(f"Creating {args.normal_users} normal users...")
        normal_users = [
            _create_user(db, "normal", f"Normal User {i}") for i in range(args.normal_users)
        ]

        print("Generating normal activity...")
        generate_normal_activity(
            db, normal_users, (args.transfers_min, args.transfers_max), args.days_back, labels
        )

        print(f"Generating {args.suspicious_groups} groups per suspicious persona...")
        for _ in range(args.suspicious_groups):
            generate_rapid_repeat_persona(db, args.days_back, labels)
            generate_circular_flow_persona(db, args.days_back, labels)
            generate_large_outlier_persona(db, args.days_back, labels)
            generate_burst_persona(db, args.days_back, labels)

        labels_path = Path(args.labels_out)
        labels_path.parent.mkdir(parents=True, exist_ok=True)
        with labels_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["transaction_id", "account_number", "persona"])
            writer.writeheader()
            writer.writerows(labels)

        print(f"Done. {len(labels)} labeled transactions written to {labels_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
