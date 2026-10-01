# Sentinel — Implementation

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Cache and live feed | Redis (login rate limit, transaction pub/sub) |
| Frontend | React, Vite, TypeScript, Tailwind CSS, React Router |
| Real-time | WebSocket at `/ws/admin/live`, fed by Redis |
| Risk model | scikit-learn Isolation Forest, pandas, joblib (optional artifact) |
| Investigation assistant | Local Ollama model (`llama3.2:1b` by default) |
| Jobs | APScheduler for reconciliation and risk forecasts |
| Tests | pytest, Vitest |

Business logic lives in `backend/app/services`. Route handlers only map HTTP to those services. The frontend does not decide fraud.

## Architecture

A transfer is validated, written provisionally with its debit and credit, then scored. Allow and monitor commit that write. Step-up and hold roll it back. A completed transfer publishes `Transaction Completed`. The monitoring engine and the admin live feed consume that event. Reconciliation does not. It reads the ledger on a schedule or when an administrator runs it.

The assistant is on demand. It retrieves rows and calls Ollama. It never writes `fraud_alerts.status`.

## Authentication

Signup and login are email and password. Passwords are bcrypt hashes. A successful login returns a JWT (`HS256`, 24 hours by default). There is no public admin signup. Admin accounts are seeded.

Login attempts are counted in Redis (`LOGIN_MAX_ATTEMPTS` per window).

A transaction PIN is a second bcrypt secret, 4–6 digits, stored in `pin_credentials`. Five failed PIN attempts lock the PIN for 15 minutes. `RequireAuth` sends a signed-in user with no PIN to `/pin-setup` before the rest of the app.

`GET /api/v1/holds/flags` tells the client whether outgoing payments are restricted. It does not list held amounts.

## Frontend

`frontend/src/pages` is split into `marketing`, `auth`, `user`, and `admin`.

| Route | Who | What |
|---|---|---|
| `/` | public | Landing |
| `/login`, `/signup` | public | Session |
| `/pin-setup` | signed in, no PIN | Create the transaction PIN |
| `/dashboard` | user | Balance, activity, inbound notice |
| `/send` | user | Account number, amount, PIN, and the high-risk code when required |
| `/activity`, `/activity/:transactionId` | user | History and receipt |
| `/profile` | user | Identity, account number, PIN state, logout |
| `/admin` | admin | Five tabs: Overview, Live feed, Fraud alerts, Reconciliation, Predictions |

Shared UI lives in `frontend/src/components/ui`. `OTPInput` is the digit field for both the send PIN (4 digits, masked) and the high-risk code (6 digits). The PIN setup page is still a 4–6 digit form, not that component. API calls go through `frontend/src/lib/api.ts`.

## Backend

Routers are mounted in `backend/app/api/v1/router.py` under `/api/v1`.

| Area | Routes |
|---|---|
| Session | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| PIN | `GET /pin/status`, `POST /pin/setup` |
| Payments | `POST /transactions/transfer`, `POST /transactions/transfer/confirm`, history and receipt |
| Warnings | `GET /inbound-warnings/me`, acknowledge; admin list and review |
| Alerts | list, case, status, release, confirm, quarantine release, restriction lift |
| Books | `POST /reconciliation/run`, `GET /reconciliation/reports` |
| Forecast | `POST /predictions/run`, `GET /predictions` |
| Assistant | `POST /assistant/ask` |
| Admin | stats, all transactions, demo scenarios |
| Health | `GET /health`, `GET /health/db` |

## Transaction system

`execute_transfer` checks the recipient, rejects a self-transfer, checks the PIN, checks the available balance, and refuses the send when an account restriction blocks outgoing money. Available balance is the wallet minus active amount holds.

The debit and credit are flushed, then `risk.engine.evaluate` runs. Only completed history is scored.

| Action | What is stored |
|---|---|
| `allow`, `allow_monitor` | The transfer and both ledger lines commit. HTTP 201. |
| `step_up` | Those rows roll back. A `step_up_challenges` row is stored. HTTP 428. |
| `hold_transaction` | Those rows roll back. A `HELD` transaction and a fraud alert are stored. No ledger movement. HTTP 202, detail “This transfer was not completed.” |

`confirm_step_up` does not score again. A matching code commits the original transfer. The code is single-use, expires in five minutes, and is stored as a SHA-256 hash. Idempotency keys stop a double submit.

Signup writes a genesis ledger credit of `INITIAL_BALANCE` (1000 ST Coins) through the ledger service. Wallet balances change only there, paired with a ledger line.

## Fraud and risk detection

Rules R01–R12 live in `backend/app/services/risk/rules.py`. A firing rule is a signal. Families are velocity, fan-in and fan-out, amount, flow, and counterparty. Points in the same family are not all counted in full. Context can reduce points that did not come from a strong rule. Strong rules (including circular flow R09 and mule chain R10) keep their points.

Tiers: up to 29 normal, 49 low, 69 suspicious, 84 high. Above that is critical only when a strong rule contributed points. Otherwise the tier stays high.

`select_action`: critical with a strong rule holds the transfer; high asks for a code; suspicious allows and monitors; otherwise allow.

After commit, `monitoring_engine` can still open a fraud alert from rules, statistics, and the Isolation Forest. If `backend/app/ml_artifacts/anomaly_model.joblib` is missing, ML scoring is skipped and the rules still run. A monitoring hold (`amount_holds`, kind `risk`) can reserve part of a balance. A later send is limited to what remains free. The sender can still receive. Quarantine holds are created when an administrator confirms fraud.

An early inbound warning fires before the full fan-in rule: at least three similar inbound amounts, and still two senders short of R03. It does not add score points and does not open a fraud alert. If the pattern later becomes a full alert, the warning is linked. An administrator review that overlaps the same senders by at least 60 percent is recorded and not shown to the user again.

## AI investigation system

`POST /assistant/ask` is admin-only. `retrieval_service` loads the transaction, rules, ML score, recent history, and reconciliation context from PostgreSQL. `ollama_client` calls the local model. The question and answer are stored in `ai_assistant_logs`. If Ollama is down, the rest of Sentinel still transfers, scores, and reconciles.

## Database schema

```sql
users (id, full_name, email, password_hash, account_number, role, is_active)
wallets (user_id, balance)
pin_credentials (user_id, pin_hash, failed_attempts, locked_until)
transactions (sender_id, receiver_id, amount, status, idempotency_key, ...)
ledger_entries (user_id, transaction_id, entry_type, amount, reference_type)
step_up_challenges (public_id, sender_id, code_hash, expires_at, used, evaluation)
risk_evaluations (transaction_id, score, tier, action, signals)
fraud_alerts (transaction_id, status, risk_score, ...)
case_events (kind, subject, inbound_warning_id, ...)
inbound_warnings (recipient_id, sender_ids, status, shown_to_user)
amount_holds (user_id, amount, kind, status, expires_at)  -- risk or quarantine
account_restrictions (user_id, ...)  -- blocks outgoing only
reconciliation_reports (status, accounts_checked, discrepancy_count, ...)
risk_predictions (user_id, score, level, horizon)
ai_assistant_logs (question, answer, context)
```

`transactions.status` is `completed`, `failed`, `held`, or `rejected`. Alert status moves only through the admin alert routes: open, investigating, resolved, false positive, confirmed fraud.

## Admin dashboard

One WebSocket stays open across tabs. Overview shows platform counts. Live feed shows transfers and new alerts. Fraud alerts shows the case timeline, early warnings, and the actions to confirm, reject, release a hold, or lift a restriction. The investigation assistant is a panel on that case. Reconciliation lists reports. Predictions lists the latest forecast. Demo scenarios under `/admin/scenarios` replay scripted histories (normal payments, a large outlier, pass-through, a mule chain, small structured payments, a circle, a ledger mismatch, and the group-payment warning). They create real users and transfers. They do not insert a finished fraud row by hand.

## Reconciliation

`run_reconciliation` sums each user’s ledger credits and debits and compares that total with `wallets.balance`. A report is `clean` or `discrepancies_found`, with the account number, expected balance, actual balance, and difference. APScheduler runs it every `RECONCILIATION_INTERVAL_MINUTES` (15). An administrator can run it immediately. It does not use the risk score.

## OTP and verification flow

This is not SMS. The server generates a 6-digit code per challenge and returns the plaintext once in the HTTP 428 body, for the classroom demo. The React client puts that code in a top notice for a few seconds and leaves the verification field empty. The sender types it. `POST /transactions/transfer/confirm` checks the hash, expiry, and single use, then commits.

The transaction PIN is separate. On Send it is four masked digits. The server still accepts 4–6 digits.

## Environment variables

```
ENVIRONMENT
DEBUG
JWT_SECRET_KEY
JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
PIN_MAX_ATTEMPTS
PIN_LOCKOUT_MINUTES
DATABASE_URL
REDIS_URL
REDIS_TRANSACTION_CHANNEL
CORS_ORIGINS
OLLAMA_BASE_URL
OLLAMA_MODEL
INITIAL_BALANCE
ACCOUNT_NUMBER_LENGTH
RECONCILIATION_INTERVAL_MINUTES
PREDICTION_INTERVAL_MINUTES
VITE_API_BASE_URL
VITE_WS_BASE_URL
```

Rule windows and weights (`R01_*` through `R12_*`, `EARLY_INBOUND_*`) have defaults in `backend/app/core/config.py` and can be overridden from the environment. Copy `.env.example` to `.env` before `docker compose`.

## Current status

Implemented and covered by pytest and Vitest:

- Signup, login, PIN, ST Coin transfers, double-entry ledger, idempotency
- Pre-commit risk score, high-risk code, critical transfer that does not complete
- Monitoring alerts, risk holds, quarantine, outgoing restriction
- Early inbound warning and administrator review of a group payment
- Reconciliation, 7-day risk forecast, admin live feed
- Investigation assistant when Ollama is running
- Optional Isolation Forest when the joblib artifact exists

The sender is not asked to explain a payment that was not completed. There is no user reservation card.

## What's left

- [ ] Deliver the one-time code outside the API response (the demo returns it in HTTP 428)
- [ ] Train and ship an Isolation Forest artifact as part of normal setup (the platform runs on rules alone until that file exists)
- [ ] Replace the classroom ST Coin ledger with a real payment network (out of scope for this build)
