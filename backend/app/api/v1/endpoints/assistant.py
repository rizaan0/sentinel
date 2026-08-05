"""
AI Investigation Assistant endpoint (admin-only).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.user import User
from app.schemas.assistant import AskAssistantRequest, AssistantLogResponse
from app.services.ai_assistant_service import NoContextTargetError, ask
from app.services.ollama_client import OllamaUnavailableError

router = APIRouter()


@router.post("/ask", response_model=AssistantLogResponse)
def ask_assistant(
    payload: AskAssistantRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AssistantLogResponse:
    try:
        log = ask(db, admin, payload.question, payload.transaction_id, payload.account_number)
    except NoContextTargetError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OllamaUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return AssistantLogResponse.model_validate(log)
