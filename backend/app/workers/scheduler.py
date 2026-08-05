"""
Background scheduler for jobs that run independently of any HTTP request,
starting with the Reconciliation Engine's periodic run (Architecture:
Reconciliation runs "scheduled + on-demand").
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.prediction_service import compute_predictions
from app.services.reconciliation_service import run_reconciliation

logger = logging.getLogger("sentinel.scheduler")

scheduler = BackgroundScheduler()


def _run_scheduled_reconciliation() -> None:
    db = SessionLocal()
    try:
        report = run_reconciliation(db, triggered_by="scheduled")
        logger.info(
            "Scheduled reconciliation complete: status=%s accounts_checked=%d discrepancies=%d",
            report.status,
            report.accounts_checked,
            report.discrepancy_count,
        )
    finally:
        db.close()


def _run_scheduled_predictions() -> None:
    db = SessionLocal()
    try:
        predictions = compute_predictions(db)
        logger.info("Scheduled predictive analytics run: %d users scored", len(predictions))
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _run_scheduled_reconciliation,
        trigger="interval",
        minutes=settings.RECONCILIATION_INTERVAL_MINUTES,
        id="reconciliation",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_scheduled_predictions,
        trigger="interval",
        minutes=settings.PREDICTION_INTERVAL_MINUTES,
        id="predictions",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
