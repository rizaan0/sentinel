"""
Reconciliation endpoints (admin-only): on-demand run + report history.
A scheduled run also happens automatically (see app/workers/scheduler.py).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.reconciliation_report import ReconciliationReport
from app.models.user import User
from app.schemas.reconciliation import ReconciliationReportResponse
from app.services.reconciliation_service import run_reconciliation

router = APIRouter()


@router.post(
    "/run", response_model=ReconciliationReportResponse, status_code=status.HTTP_201_CREATED
)
def run(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ReconciliationReportResponse:
    report = run_reconciliation(db, triggered_by="manual")
    return ReconciliationReportResponse.model_validate(report)


@router.get("/reports", response_model=list[ReconciliationReportResponse])
def list_reports(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ReconciliationReportResponse]:
    reports = (
        db.execute(
            select(ReconciliationReport).order_by(ReconciliationReport.created_at.desc()).limit(50)
        )
        .scalars()
        .all()
    )
    return [ReconciliationReportResponse.model_validate(r) for r in reports]
