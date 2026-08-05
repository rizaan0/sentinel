# Development Guide

## Environment variables

All settings live in `backend/app/core/config.py` (`Settings`, loaded via `pydantic-settings`
from a `.env` file resolved relative to the current working directory). See
[.env.example](../.env.example) for the full list. Notable groups:

| Group | Variables |
|---|---|
| Security | `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `PIN_MAX_ATTEMPTS`, `PIN_LOCKOUT_MINUTES`, `LOGIN_MAX_ATTEMPTS`, `LOGIN_RATE_LIMIT_WINDOW_MINUTES` |
| Database | `DATABASE_URL` |
| Redis | `REDIS_URL`, `REDIS_TRANSACTION_CHANNEL` |
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS` |
| Business rules | `INITIAL_BALANCE`, `ACCOUNT_NUMBER_LENGTH` |
| Scheduled jobs | `RECONCILIATION_INTERVAL_MINUTES`, `PREDICTION_INTERVAL_MINUTES` |
| Fraud rule thresholds | `RAPID_REPEAT_WINDOW_SECONDS`, `RAPID_REPEAT_MIN_COUNT`, `CIRCULAR_FLOW_WINDOW_MINUTES`, `CIRCULAR_FLOW_MAX_HOPS`, `LARGE_TRANSFER_STDDEV_MULTIPLIER`, `LARGE_TRANSFER_MIN_HISTORY`, `BURST_WINDOW_MINUTES`, `BURST_MIN_COUNT`, `BURST_MAX_AMOUNT` |

There are two `.env` files in play locally: the repo-root `.env` (used by `docker-compose`, and
by any tool run with the repo root as its working directory) and `backend/.env` (used when
running backend tooling from inside `backend/`, e.g. `alembic`, `uvicorn`, the seed/ML scripts).
They intentionally differ only in `DATABASE_URL`/`REDIS_URL`/`OLLAMA_BASE_URL` hostnames -
`postgres`/`redis`/`ollama` (Docker service names) in the root `.env` vs `127.0.0.1`/`localhost`
in `backend/.env` (for processes running directly on the host).

## Database migrations

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Every model module must be imported in `app/db/base.py` or Alembic's autogenerate (and any
script that touches the ORM without importing `app.db.base`) will fail with `InvalidRequestError:
... failed to locate a name` due to unresolved relationship string references.

## Scripts

| Script | Purpose |
|---|---|
| `backend/scripts/seed_admin.py` | Creates an admin user (no public admin signup exists by design) |
| `ml/synthetic_generator.py` | Simulates normal + suspicious-persona users through the real transfer pipeline |
| `ml/train_model.py` | Trains the Isolation Forest anomaly model on whatever transactions exist in the DB |
| `ml/retrain_model.py` | Documented alias for `train_model.py`, for when retraining on real accumulated data |

## Testing philosophy

- Backend: pytest against a real, dedicated Postgres database (`sentinel_test`) and a separate
  Redis DB index, with table truncation between tests (see `tests/conftest.py`'s docstring for
  why rollback-based isolation doesn't work here). The Ollama LLM call itself is monkeypatched
  in AI Assistant tests so the suite stays fast/deterministic without a running local model.
- Frontend: Vitest + React Testing Library, with the `api` module mocked per test file so
  component tests don't require a running backend. Covers the signup -> PIN -> send-money ->
  receipt flow and the admin fraud-alert review flow (status update).

Run everything:

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
cd frontend; npm run test; npm run lint; npx tsc -b --noEmit
```

## Adding a new fraud rule

1. Add a function to `backend/app/services/fraud_rules.py` following the existing signature:
   `(db: Session, transaction: Transaction) -> RuleResult | None`.
2. Add it to `ALL_RULES` at the bottom of that file.
3. Add any new thresholds to `Settings` in `app/core/config.py`.
4. Write a test in `tests/test_fraud_detection.py` following the existing pattern (fire the
   transaction(s) via the HTTP client, then assert the resulting `FraudAlert`'s
   `triggered_rules` contains your rule name).

No other file needs to change - the Monitoring Engine iterates `ALL_RULES` generically.
