"""
Transaction PIN setup and status endpoints.

Note: PIN *verification* for authorizing a transfer is exposed as part of
the transfer flow in Phase 2, not as a standalone endpoint here, so a PIN
can never be validated outside the context of an actual transaction.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.pin import PinSetupRequest, PinStatusResponse
from app.services.pin_service import PinAlreadySetError, set_pin

router = APIRouter()


@router.get("/status", response_model=PinStatusResponse)
def pin_status(current_user: User = Depends(get_current_user)) -> PinStatusResponse:
    return PinStatusResponse(pin_is_set=current_user.pin_is_set)


@router.post("/setup", response_model=PinStatusResponse, status_code=status.HTTP_201_CREATED)
def setup_pin(
    payload: PinSetupRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PinStatusResponse:
    try:
        set_pin(db, current_user, payload.pin)
    except PinAlreadySetError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PinStatusResponse(pin_is_set=True)
