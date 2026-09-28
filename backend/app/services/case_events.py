"""Append-only case history."""

from sqlalchemy.orm import Session

from app.models.case_event import CaseEvent


def record_case_event(db: Session, alert_id: int | None, kind: str, actor: str, detail: dict | None = None) -> None:
    db.add(CaseEvent(alert_id=alert_id, kind=kind, actor=actor, detail=detail or {}))
