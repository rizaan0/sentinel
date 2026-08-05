# Sentinel Architecture

This document describes how Sentinel is put together and the invariants every feature is
expected to follow. It expands on the [README](../README.md)'s high-level diagram.

## Architecture Rules

These are load-bearing constraints, not suggestions - every phase of the implementation was
built to respect them:

1. **PostgreSQL is the single source of truth.**
2. **The Ledger Service is the source of financial truth.** Wallet balances are only ever
   mutated inside `app/services/ledger_service.py`, paired with a double-entry `ledger_entries`
   write and an Integrity Validator check.
3. **Monitoring never executes before a successful transaction commit.** The Monitoring Engine
   only runs off `Transaction Completed Event`, which fires strictly after PostgreSQL confirms
   the commit - a rolled-back transaction can never produce a fraud alert.
4. **Business logic lives only in backend services** (`app/services/*`). API endpoints
   (`app/api/v1/endpoints/*`) only translate HTTP <-> service calls and map exceptions to status
   codes.
5. **Frontend never contains business rules.** It calls the backend and renders what comes
   back; validation logic that matters (PIN correctness, balance sufficiency, fraud thresholds)
   lives entirely server-side.
6. **The AI Investigation Assistant never decides fraud; it only explains monitoring results.**
   It cannot write to `fraud_alerts.status` - only a human admin can, via
   `PATCH /fraud-alerts/{id}/status`.
7. **Every feature integrates into the existing architecture instead of introducing parallel
   implementations.** E.g. the ML Anomaly Detector participates in the *same* rule-triggered
   alert-creation path as the hand-coded rules (see `monitoring_engine.py`), rather than having
   its own separate alerting mechanism.

## The transaction pipeline, step by step

1. **Transaction Service** (`app/services/transfer_service.py`) receives a transfer request.
2. **Transaction Validation** runs three checks before anything is written: the recipient
   exists, the Transaction PIN is correct (`pin_service.py`, with brute-force lockout), and the
   sender's wallet balance is sufficient.
3. **Ledger Service** (`app/services/ledger_service.py`) applies the balance mutation and writes
   a matching debit/credit pair to `ledger_entries`, validated by
   `app/services/integrity_validator.py`.
4. The transaction and ledger writes are committed to **PostgreSQL** in one transaction.
5. Only now does **`Transaction Completed Event`** fire (`app/core/events.py`), fanning out in
   parallel, synchronously, to two independent consumers:
   - The **Monitoring Engine** (`app/services/monitoring_engine.py`)
   - **Redis Pub/Sub**, for the live admin feed (`app/services/realtime.py`)
6. The Monitoring Engine runs three independent evaluators against the transaction:
   - The **Rule Engine** (`app/services/fraud_rules.py`): rapid repeated transfers, circular
     fund flow, unusually large transfers, bursts of small transactions.
   - **Statistics** (baked into the rules' historical-comparison logic).
   - The **ML Anomaly Detector** (`app/services/ml_anomaly_service.py`): an Isolation Forest
     scoring the same transaction on a feature vector (`app/services/ml_features.py`).
   If **any** of these trigger, a `FraudAlert` is created with a combined risk score and
   published to Redis too - so admins see new alerts live, not just new transactions.
7. Separately, and independently of Monitoring, the **Reconciliation Engine**
   (`app/services/reconciliation_service.py`) reads directly from the ledger (scheduled every
   `RECONCILIATION_INTERVAL_MINUTES`, or on demand) and compares every wallet's balance against
   the sum of its ledger entries, producing `reconciliation_reports`.
8. **Predictive Analytics** (`app/services/prediction_service.py`) runs on its own schedule,
   ranking users whose fraud-alert frequency/severity is trending upward.
9. The **AI Investigation Assistant** (`app/services/ai_assistant_service.py`) is invoked
   on-demand by an admin. Its Retrieval Service (`app/services/retrieval_service.py`) reads
   transaction details, triggered rules, ML scores, recent history, and recent reconciliation
   reports from PostgreSQL, and its answer (from a local Ollama model) is logged in full for
   audit purposes (`ai_assistant_logs`).

## Why a synchronous, in-process event bus (for now)

`app/core/events.py` is intentionally minimal: a subscriber list plus a `publish()` that calls
each handler synchronously. This is documented as a starting point, not a permanent design - the
publish/subscribe *interface* is what matters and is what future phases (or a real message
broker) would build against, without changing any publisher code. A failing subscriber (e.g. the
Monitoring Engine throwing) is caught and logged so it can never break the payment flow that
already committed.

## Test isolation strategy

Backend tests run against a dedicated `sentinel_test` PostgreSQL database and Redis DB index 1
(never the dev database/DB 0). Tests use **real commits**, not rollback-based isolation, because
the Monitoring Engine opens its own database connection to react to committed data - a
connection-scoped savepoint-rollback strategy would hide that data from it. Isolation between
tests is instead achieved by truncating all tables after every test (see `tests/conftest.py`).

## Known Docker gotcha

`docker-compose.yml` mounts an anonymous volume over `frontend`'s `node_modules` so the
container's own `npm ci`-installed packages aren't shadowed by the host's `node_modules` (or
vice versa on different OSes). This means that after adding a new frontend dependency locally,
the running container's `node_modules` volume goes stale and must be refreshed with
`docker compose up -d --force-recreate --renew-anon-volumes frontend`.
