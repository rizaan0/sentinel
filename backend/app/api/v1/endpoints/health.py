"""
Basic liveness/readiness endpoints used by docker-compose healthchecks and
manual verification that Phase 0's foundation is working end to end.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health() -> dict:
    """Liveness probe: process is up."""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    """Readiness probe: PostgreSQL connection is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
