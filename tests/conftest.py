"""
Shared pytest fixtures for backend tests.

Tests run against a dedicated `sentinel_test` PostgreSQL database (never the
dev database). Each test's writes are REAL commits (not rollback-isolated),
because Phase 4 onward introduces independent consumers (Monitoring Engine)
that open their own DB session/connection to react to committed data - a
connection-scoped savepoint-rollback strategy would hide that data from
them. Isolation between tests is instead achieved by truncating all tables
after every test.
"""
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

# Point the app at the test database *before* importing anything from `app`,
# since settings are loaded once at import time.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://sentinel:sentinel@127.0.0.1:5433/sentinel_test",
)
# A separate Redis DB index (not the dev DB's index 0) so rate-limit
# counters etc. from test runs never bleed into dev, and can be flushed
# freely between test sessions.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ["ENVIRONMENT"] = "test"

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _flush_test_redis_db():
    import redis as redis_sync

    from app.core.config import settings

    redis_sync.Redis.from_url(settings.REDIS_URL).flushdb()


@pytest.fixture(autouse=True)
def _clean_tables_after_test():
    yield
    with engine.begin() as connection:
        table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
        if table_names:
            connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers(db_session):
    import uuid

    from app.core.security import create_access_token
    from app.models.enums import UserRole
    from app.schemas.auth import SignupRequest
    from app.services.auth_service import signup_user

    user = signup_user(
        db_session,
        SignupRequest(
            full_name="Admin",
            email=f"admin_{uuid.uuid4().hex[:8]}@sentinel.app",
            password="AdminPass123",
        ),
        role=UserRole.ADMIN,
    )
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}
