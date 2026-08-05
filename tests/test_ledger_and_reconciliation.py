"""
Phase 3 tests: ledger entries (genesis + transfer) and the Reconciliation
Engine, which operates directly on the ledger.
"""
from decimal import Decimal

from app.models.enums import LedgerEntryType, LedgerReferenceType, ReconciliationStatus
from app.models.ledger_entry import LedgerEntry
from app.models.user import User
from app.services.reconciliation_service import run_reconciliation


def _signup_with_pin(client, email, password="supersecret1", pin="1234"):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": email.split("@")[0], "email": email, "password": password},
    )
    body = signup.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/api/v1/pin/setup", json={"pin": pin}, headers=headers)
    return body["user"], headers


def _make_admin(db_session, email="admin_ledger@sentinel.app"):
    from app.schemas.auth import SignupRequest
    from app.services.auth_service import signup_user
    from app.models.enums import UserRole

    user = signup_user(
        db_session,
        SignupRequest(full_name="Admin", email=email, password="AdminPass123"),
        role=UserRole.ADMIN,
    )
    from app.core.security import create_access_token

    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_signup_creates_a_genesis_ledger_entry(client, db_session):
    user, _ = _signup_with_pin(client, "genesis@example.com")

    entries = (
        db_session.query(LedgerEntry)
        .filter(LedgerEntry.user_id == user["id"])
        .all()
    )
    assert len(entries) == 1
    assert entries[0].reference_type == LedgerReferenceType.GENESIS
    assert entries[0].entry_type == LedgerEntryType.CREDIT
    assert entries[0].amount == Decimal("1000.00")
    assert entries[0].balance_after == Decimal("1000.00")


def test_transfer_creates_matching_debit_and_credit_entries(client, db_session):
    alice, alice_headers = _signup_with_pin(client, "alice_ledger@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_ledger@example.com", pin="2222")

    client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "100.00",
            "pin": "1111",
        },
        headers=alice_headers,
    )

    alice_entries = (
        db_session.query(LedgerEntry).filter(LedgerEntry.user_id == alice["id"]).all()
    )
    bob_entries = db_session.query(LedgerEntry).filter(LedgerEntry.user_id == bob["id"]).all()

    # genesis + transfer debit for alice
    assert len(alice_entries) == 2
    debit = next(e for e in alice_entries if e.reference_type == LedgerReferenceType.TRANSFER)
    assert debit.entry_type == LedgerEntryType.DEBIT
    assert debit.amount == Decimal("100.00")
    assert debit.balance_after == Decimal("900.00")

    # genesis + transfer credit for bob
    assert len(bob_entries) == 2
    credit = next(e for e in bob_entries if e.reference_type == LedgerReferenceType.TRANSFER)
    assert credit.entry_type == LedgerEntryType.CREDIT
    assert credit.amount == Decimal("100.00")
    assert credit.balance_after == Decimal("1100.00")


def test_reconciliation_reports_clean_for_normal_activity(client, db_session):
    alice, alice_headers = _signup_with_pin(client, "alice_recon@example.com", pin="1111")
    bob, _ = _signup_with_pin(client, "bob_recon@example.com", pin="2222")
    client.post(
        "/api/v1/transactions/transfer",
        json={
            "recipient_account_number": bob["account_number"],
            "amount": "40.00",
            "pin": "1111",
        },
        headers=alice_headers,
    )

    report = run_reconciliation(db_session, triggered_by="test")
    assert report.status == ReconciliationStatus.CLEAN
    assert report.discrepancy_count == 0
    assert report.accounts_checked >= 2


def test_reconciliation_detects_a_manually_introduced_discrepancy(client, db_session):
    alice, _ = _signup_with_pin(client, "alice_corrupt@example.com")

    # Simulate a bug/corruption: mutate the wallet balance directly, bypassing
    # the Ledger Service, so the ledger and the wallet disagree.
    user = db_session.get(User, alice["id"])
    user.wallet.balance = Decimal("1234.56")
    db_session.add(user.wallet)
    db_session.commit()

    report = run_reconciliation(db_session, triggered_by="test")
    assert report.status == ReconciliationStatus.DISCREPANCIES_FOUND
    assert report.discrepancy_count == 1
    assert report.discrepancies[0]["account_number"] == alice["account_number"]
    assert report.discrepancies[0]["expected_balance"] == "1000.00"
    assert report.discrepancies[0]["actual_balance"] == "1234.56"


def test_reconciliation_endpoint_requires_admin(client):
    _, user_headers = _signup_with_pin(client, "notadmin@example.com")
    response = client.post("/api/v1/reconciliation/run", headers=user_headers)
    assert response.status_code == 403


def test_reconciliation_endpoint_works_for_admin(client, db_session):
    admin_headers = _make_admin(db_session)
    response = client.post("/api/v1/reconciliation/run", headers=admin_headers)
    assert response.status_code == 201
    assert response.json()["status"] in ("clean", "discrepancies_found")

    listing = client.get("/api/v1/reconciliation/reports", headers=admin_headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 1
