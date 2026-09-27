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
from app.services.ollama_client import OllamaUnavailableError, chat

_REFUSAL_MARKERS = (
    "cannot provide",
    "can't provide",
    "cannot assist",
    "can't assist",
    "cannot help",
    "can't help",
    "i'm sorry",
    "i am sorry",
    "as an ai",
    "how to commit",
)

SYSTEM_PROMPT = """You are Sentinel AI Investigation Assistant, a tool for human fraud analysts working on a real time transaction monitoring platform.

Tone: calm, direct, unhurried. No filler, no enthusiasm, no emoji. Write like a sharp colleague who knows their stuff and does not need to prove it. Keep responses short unless more is clearly needed. Do not use bullet points unless the user asks for a list. Do not use unnecessary headings, repeated explanations, generic AI language, or fixed response templates. Do not use dashes for formatting.

Your job is to help an analyst investigate transactions, accounts, monitoring alerts, reconciliation issues, risk scores, rule triggers, ML anomaly results, and behavioural patterns.

You have access only to the investigation data provided in the current context. Treat that data as the source of truth. Never invent, assume, estimate, or fill in missing information.

The most important rule is to answer the analyst's actual question. Do not give the same investigation structure for every question. Understand what the analyst is asking and use only the information relevant to that question.

If the analyst asks why a transaction was flagged, explain the specific behaviour, rule or ML signal that caused the alert and the evidence behind it.

If the analyst asks what a particular rule means, explain that rule in plain language and relate it to the available transaction evidence.

If the analyst asks about an ML anomaly, explain what the anomaly detector found, including the anomaly score and relevant behavioural context when available.

If the analyst asks about the risk score, explain what contributed to the existing score and which signals increased or reduced it. Do not recalculate or change the score unless the provided data explicitly requires it.

If the analyst asks whether they should block an account or take an action, do not make the fraud decision for them. Explain the evidence available to support that decision, including relevant risk signals, contextual checks, previous activity, and the existing monitoring classification. Do not repeat unrelated information simply because it exists in the investigation context.

If the analyst asks about recent account behaviour, summarize the relevant changes in activity rather than describing every available signal.

If the analyst asks about a specific transaction, focus on that transaction rather than automatically summarizing the entire account.

If the analyst asks a follow up question, use the previous investigation context and answer the new question directly. Do not repeat the previous answer unless it is necessary to answer the follow up.

If the analyst asks a question that requires information not present in the investigation context, say clearly that the available monitoring data does not contain that information. Never guess.

Rule IDs such as R03 or R08 are internal technical references. When mentioning them, always explain what the rule actually detected in plain language. For example, say "Six different accounts sent similar amounts to the same recipient within 90 seconds, triggering the Fan In Burst rule (R03)" rather than simply saying "R03 triggered."

A triggered rule is a risk signal, not proof of fraud. The monitoring engine's risk score and classification are existing system outputs. You may explain them, but you must not independently declare an activity fraudulent or override the monitoring engine's decision.

When multiple signals are relevant to the question, connect them naturally. Do not automatically mention every triggered rule. Only discuss signals that help answer the analyst's question.

Context checks are important when they materially change the interpretation of an alert. For example, an unusual fan in pattern may be less significant when the counterparties are established and there is no rapid outbound movement. Mention such context when it is relevant to the question being asked.

The AI Investigation Assistant is an explanation and investigation layer. It does not create fraud decisions, modify risk scores, invent evidence, or replace the monitoring engine.

For reconciliation questions, explain the actual discrepancy using the provided transaction, ledger, wallet, and reconciliation data. State the relevant expected and observed values when available, but do not assume the cause of a discrepancy without evidence.

For behavioural or predictive questions, explain the relevant historical patterns and existing prediction results using only the provided data. Do not present a prediction as a confirmed future event.

Use natural paragraph style for normal answers. A short descriptive title may be used when it genuinely improves clarity, but do not force every response into a title followed by the same explanation pattern.

Do not repeatedly say that you are an AI, that the final decision belongs to a human, or that the evidence is only based on provided data unless that information is directly relevant to the question.

The goal is to behave like an investigation assistant that understands the analyst's question and responds specifically to it, rather than generating the same fraud explanation template for every interaction.

"""


class NoContextTargetError(Exception):
    pass


def _refused(answer: str) -> bool:
    text = answer.lower()
    return any(marker in text for marker in _REFUSAL_MARKERS)


def _clean_answer(answer: str) -> str:
    lines = answer.strip().splitlines()
    leaked = ("recorded result", "record for analyst", "recorded for analyst", "analyst question")
    while lines and lines[0].strip().lower().rstrip(":") in leaked:
        lines.pop(0)
        if lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def _prior_messages(db: Session, admin_user_id: int, transaction_db_id: int | None, account_number: str | None) -> list[dict]:
    query = select(AiAssistantLog).where(AiAssistantLog.admin_user_id == admin_user_id)
    if transaction_db_id is not None:
        query = query.where(AiAssistantLog.transaction_id == transaction_db_id)
    elif account_number:
        query = query.where(AiAssistantLog.target_account_number == account_number)
    else:
        return []
    rows = list(
        db.execute(query.order_by(AiAssistantLog.created_at.desc()).limit(6)).scalars().all()
    )
    messages = []
    for row in reversed(rows):
        messages.append({"role": "user", "content": row.question})
        messages.append({"role": "assistant", "content": row.answer})
    return messages


def _sentences(text: str) -> set[str]:
    return {part.strip() for part in text.replace("\n", " ").split(".") if len(part.strip()) > 40}


def _misses_question(question: str, answer: str) -> bool:
    asked = question.lower()
    text = answer.lower()
    if any(word in asked for word in ("block", "freeze", "keep it open", "keep open", "restrict")):
        return not any(word in text for word in ("block", "hold", "open", "restrict", "freeze"))
    return False


def _repeats_previous(answer: str, history: list[dict]) -> bool:
    previous = [message["content"] for message in history if message["role"] == "assistant"]
    if not previous:
        return False
    last = previous[-1]
    shared = _sentences(answer) & _sentences(last)
    if shared:
        return True
    current_words = set(answer.lower().split())
    last_words = set(last.lower().split())
    if not current_words or not last_words:
        return False
    overlap = len(current_words & last_words) / len(current_words)
    return overlap >= 0.72


def _brief(context: dict) -> str:
    alerts = context.get("fraud_alerts") or context.get("recent_fraud_alerts") or []
    if not alerts:
        forecast = context.get("risk_forecast") or {}
        return forecast.get("explanation") or "No monitoring result is stored."
    alert = alerts[0]
    names = []
    for signal in alert.get("signals") or alert.get("triggered_rules") or []:
        raw = signal.get("rule_name") or signal.get("rule_id") or ""
        names.append(raw.replace("_", " "))
    tier = (alert.get("tier") or "not set").replace("_", " ")
    hold = alert.get("hold") or {}
    hold_text = (
        f"amount hold of {hold.get('amount')} ST is active"
        if hold.get("status") == "active"
        else "no hold is active"
    )
    return (
        f"Risk {alert.get('risk_score')}/100, tier {tier}. "
        f"Signals: {', '.join(names) or 'none recorded'}. {hold_text.capitalize()}."
    )


FOLLOW_UP_PROMPT = """You are Sentinel's investigation assistant talking with an analyst.
Answer only their latest question in two to four plain sentences.
Do not repeat the previous explanation. Do not decide that fraud occurred.
Do not use underscored identifiers."""


def _answer_without_model(question: str, context: dict, recorded: str | None) -> str | None:
    """Used only when the model refuses or is offline. Still answers the question asked."""
    alerts = context.get("fraud_alerts") or context.get("recent_fraud_alerts") or []
    alert = alerts[0] if alerts else None
    asked = question.lower()
    if alert and any(word in asked for word in ("block", "freeze", "hold", "restrict", "close", "keep it open", "keep open")):
        score = alert.get("risk_score")
        tier = (alert.get("tier") or "recorded").replace("_", " ")
        hold = alert.get("hold") or {}
        if hold.get("status") == "active":
            restriction = (
                f"An amount hold of {hold.get('amount')} ST is already on the flagged funds. "
                "The rest of the account is not frozen."
            )
        else:
            restriction = "This result did not place a hold, and it does not freeze the account."
        return (
            f"Keep the case open, and do not block the whole account on this result alone. "
            f"The recorded risk is {score}/100, tier {tier}. {restriction} "
            "That is a signal for you to review, not proof of fraud. "
            "Leave it open while you look, or mark it a false positive if the pattern is benign."
        )
    if recorded and any(word in asked for word in ("why", "what went wrong", "flag", "wrong", "section")):
        return recorded
    if recorded:
        return recorded
    forecast = context.get("risk_forecast") or {}
    if forecast.get("explanation"):
        return forecast["explanation"]
    return None


def explain_recorded(context: dict) -> str | None:
    """Title plus one paragraph from stored monitoring results. No model required."""
    alerts = context.get("fraud_alerts") or context.get("recent_fraud_alerts") or []
    forecast = context.get("risk_forecast") or None
    if not alerts:
        if forecast and forecast.get("explanation"):
            return f"Risk forecast\n\n{forecast['explanation']}"
        return None
    alert = alerts[0]
    signals = list(alert.get("signals") or [])
    scored = [signal for signal in signals if (signal.get("score_contribution") or 0) > 0]
    lead = scored or signals
    if not lead:
        narrative = alert.get("narrative")
        rules = alert.get("triggered_rules") or []
        if narrative:
            return narrative
        if not rules:
            return None
        rule = rules[0]
        title = f"{rule.get('rule_name', 'Monitoring')} rule triggered"
        body = rule.get("explanation") or "A monitoring rule was recorded on this transaction."
        return f"{title}\n\n{body} The recorded risk score is {alert.get('risk_score')}."

    primary = max(lead, key=lambda signal: signal.get("score_contribution") or 0)
    title = f"{primary.get('rule_name', 'Monitoring')} rule triggered"
    sentences = []
    for signal in lead:
        explanation = (signal.get("explanation") or "").strip()
        name = signal.get("rule_name") or "a monitoring rule"
        rule_id = signal.get("rule_id") or ""
        if explanation:
            sentences.append(f"{explanation} This is the {name} rule ({rule_id}).")
        else:
            sentences.append(f"The {name} rule ({rule_id}) was recorded.")
    checks = alert.get("context_checks") or []
    cleared = [check["check"].replace("_", " ") for check in checks if check.get("cleared")]
    failed = [check["check"].replace("_", " ") for check in checks if not check.get("cleared")]
    if cleared:
        sentences.append("Checks that reduced concern: " + ", ".join(cleared) + ".")
    if failed:
        sentences.append("Checks that did not clear: " + ", ".join(failed) + ".")
    score = alert.get("risk_score")
    tier = (alert.get("tier") or "").replace("_", " ")
    closing = f"The recorded risk score is {score}"
    if tier:
        closing += f", in the {tier} tier"
    closing += "."
    if alert.get("pattern"):
        closing += f" Pattern {alert['pattern']} was matched."
    hold = alert.get("hold") or {}
    if hold.get("status") == "active":
        closing += f" {hold.get('amount')} ST of the flagged amount is on hold."
    closing += " This explains the recorded monitoring result. It is not a fraud verdict."
    sentences.append(closing)
    return f"{title}\n\n{' '.join(sentences)}"


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

    recorded = explain_recorded(context)
    history = _prior_messages(db, admin_user.id, db_transaction_id, account_number)
    user_prompt = (
        "Evidence from Sentinel (facts only; answer from this, do not quote the field names):\n"
        f"{json.dumps(context, indent=2, default=str)}\n\n"
        "Answer the question below. Use the conversation so far. "
        "Do not repeat an explanation you already gave.\n\n"
        f"Question: {question}"
    )
    try:
        answer = _clean_answer(chat(SYSTEM_PROMPT, user_prompt, history=history))
    except OllamaUnavailableError:
        answer = ""
    if history and answer and not _refused(answer) and (
        _repeats_previous(answer, history) or _misses_question(question, answer)
    ):
        try:
            answer = _clean_answer(
                chat(
                    FOLLOW_UP_PROMPT,
                    (
                        f"Previous reply:\n{history[-1]['content']}\n\n"
                        f"Facts: {_brief(context)}\n\n"
                        f"New question: {question}\n\n"
                        "Answer the new question only."
                    ),
                )
            )
        except OllamaUnavailableError:
            answer = ""
        if not answer or _refused(answer) or _repeats_previous(answer, history) or _misses_question(question, answer):
            answer = ""
    if not answer or _refused(answer):
        fallback = _answer_without_model(question, context, recorded)
        if not fallback:
            if not answer:
                raise OllamaUnavailableError("The investigation assistant is unavailable.")
        else:
            answer = fallback

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
