"""One scenario at a time. Each step is a real transfer."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.risk_evaluation import RiskEvaluation
from app.models.transaction import Transaction
from app.services.prediction_service import compute_predictions
from app.services.reconciliation_service import run_reconciliation
from app.services.scenarios.cast import ensure_cast
from app.services.scenarios.scripts import SCENARIOS, _pay
from app.services.transfer_service import FundsOnHoldError, InsufficientBalanceError

ALERT_TIERS = {"suspicious", "high", "critical"}

STEP_DELAY_SECONDS = 1.5


class ScenarioBusyError(Exception):
    pass


class UnknownScenarioError(Exception):
    pass


@dataclass
class ScenarioStatus:
    state: str = "idle"
    scenario_id: str | None = None
    title: str | None = None
    step: int = 0
    total: int = 0
    last_transaction_id: str | None = None
    detail: str | None = None


_lock = threading.Lock()
_status = ScenarioStatus()
_stop = threading.Event()
_thread: threading.Thread | None = None


def list_scenarios() -> list[dict]:
    return [
        {"id": key, "title": item["title"], "summary": item["summary"]}
        for key, item in SCENARIOS.items()
    ]


def current_status() -> ScenarioStatus:
    return _status


def stop_scenario() -> ScenarioStatus:
    _stop.set()
    if _status.state == "running":
        _status.detail = "Stopping after the current transfer"
    return _status


def start_scenario(scenario_id: str, delay_seconds: float = STEP_DELAY_SECONDS) -> ScenarioStatus:
    global _thread
    if scenario_id not in SCENARIOS:
        raise UnknownScenarioError(scenario_id)
    with _lock:
        if _status.state == "running":
            raise ScenarioBusyError("A scenario is already running")
        _stop.clear()
        spec = SCENARIOS[scenario_id]
        _status.state = "running"
        _status.scenario_id = scenario_id
        _status.title = spec["title"]
        _status.step = 0
        _status.total = 0
        _status.last_transaction_id = None
        _status.detail = "Starting"
        _thread = threading.Thread(
            target=_run,
            args=(scenario_id, delay_seconds),
            daemon=True,
            name=f"scenario-{scenario_id}",
        )
        _thread.start()
    return _status


def _outcome_detail(transaction_id: str | None) -> str:
    if not transaction_id:
        return "Scenario finished"
    db = SessionLocal()
    try:
        transaction = db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        ).scalar_one_or_none()
        if transaction is None:
            return "Scenario finished"
        evaluation = db.execute(
            select(RiskEvaluation)
            .where(RiskEvaluation.transaction_id == transaction.id)
            .order_by(RiskEvaluation.id.desc())
        ).scalars().first()
        if evaluation is None or evaluation.tier not in ALERT_TIERS:
            score = evaluation.risk_score if evaluation is not None else 0
            return (
                f"Recorded as monitoring evidence. The score stayed under the alert line ({score})."
            )
        return f"Scenario finished. Risk {evaluation.risk_score}, tier {evaluation.tier}."
    finally:
        db.close()


def _wrap_up() -> None:
    db = SessionLocal()
    try:
        compute_predictions(db)
        run_reconciliation(db, triggered_by="scenario")
    finally:
        db.close()


def _run(scenario_id: str, delay_seconds: float) -> None:
    spec = SCENARIOS[scenario_id]
    if "play" in spec:
        try:
            spec["play"](delay_seconds, _stop.is_set, _status)
        except Exception as exc:
            _status.state = "error"
            _status.detail = str(exc)
            return
        if _stop.is_set() and _status.state == "running":
            _status.state = "stopped"
            return
        if _status.state == "running":
            _status.state = "finished"
        return

    db = SessionLocal()
    try:
        steps = spec["build"](db)
        _status.total = len(steps)
        _status.detail = spec["summary"]
    except Exception as exc:
        _status.state = "error"
        _status.detail = str(exc)
        return
    finally:
        db.close()

    for index, (sender_key, receiver_key, amount, remark) in enumerate(steps, start=1):
        if _stop.is_set():
            _wrap_up()
            _status.state = "stopped"
            _status.detail = "Stopped before the remaining transfers"
            return
        db = SessionLocal()
        try:
            cast = ensure_cast(db)
            _status.step = index
            _status.last_transaction_id = _pay(
                db, cast[sender_key], cast[receiver_key], amount, remark
            )
        except (FundsOnHoldError, InsufficientBalanceError) as exc:
            _wrap_up()
            _status.state = "finished"
            _status.detail = str(exc)
            return
        except Exception as exc:
            _status.state = "error"
            _status.detail = str(exc)
            return
        finally:
            db.close()
        if index < len(steps) and delay_seconds > 0:
            time.sleep(delay_seconds)

    try:
        _wrap_up()
    except Exception as exc:
        _status.state = "error"
        _status.detail = str(exc)
        return
    if _stop.is_set():
        _status.state = "stopped"
        _status.detail = "Stopped after the last committed transfer"
        return
    _status.state = "finished"
    _status.detail = _outcome_detail(_status.last_transaction_id)
