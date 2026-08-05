"""
AI Investigation Assistant: orchestrates retrieval (RAG) + prompt
construction + the local LLM call, and logs every query/answer for audit
purposes.

Architecture Rule: the AI Investigation Assistant never decides fraud; it
only explains monitoring results. This is enforced in the system prompt
and reinforced by the fact that this service never writes to
`fraud_alerts.status` - only a human admin can do that (see
app/api/v1/endpoints/fraud_alerts.py).
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_assistant_log import AiAssistantLog
from app.models.transaction import Transaction
from app.models.user import User
from app.services import retrieval_service
from app.services.ollama_client import chat

SYSTEM_PROMPT = """You are the Sentinel AI Investigation Assistant, a tool for human fraud \
analysts at a real-time transaction monitoring platform.

Your role:
- Explain WHY a transaction or account was flagged, using only the monitoring data provided.
- Summarize a user's recent behavior when asked.
- Explain reconciliation discrepancies when relevant.

Strict rules:
- You NEVER decide whether something is fraud. You only explain the monitoring engine's \
existing rule triggers, ML anomaly scores, and reconciliation findings.
- You NEVER invent data. If the provided context doesn't contain an answer, say so plainly.
- Be concise, factual, and reference specific numbers (risk scores, amounts, rule names) from \
the context.
- The final fraud/no-fraud call is always a human decision, not yours.
"""


class NoContextTargetError(Exception):
    pass


def ask(
    db: Session,
    admin_user: User,
    question: str,
    transaction_public_id: str | None,
    account_number: str | None,
) -> AiAssistantLog:
    if transaction_public_id:
        transaction = db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_public_id)
        ).scalar_one_or_none()
        if transaction is None:
            raise NoContextTargetError(f"No transaction found with id {transaction_public_id}")
        context = retrieval_service.build_context_for_transaction(db, transaction)
        db_transaction_id = transaction.id
    elif account_number:
        context = retrieval_service.build_context_for_account(db, account_number)
        db_transaction_id = None
    else:
        raise NoContextTargetError("Either transaction_id or account_number is required")

    user_prompt = (
        f"Context (JSON):\n{json.dumps(context, indent=2, default=str)}\n\nQuestion: {question}"
    )
    answer = chat(SYSTEM_PROMPT, user_prompt)

    log = AiAssistantLog(
        admin_user_id=admin_user.id,
        transaction_id=db_transaction_id,
        target_account_number=account_number,
        question=question,
        answer=answer,
        context_used=context,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
