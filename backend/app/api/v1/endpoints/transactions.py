"""
Recipient search, transfer execution, transaction history, and receipts.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    PaginatedTransactions,
    TransactionReceipt,
    TransactionSummary,
    TransferRequest,
)
from app.schemas.user import UserSearchResult
from app.services.pin_service import InvalidPinError, PinLockedError, PinNotSetError
from app.services.transfer_service import (
    FundsOnHoldError,
    InsufficientBalanceError,
    RecipientNotFoundError,
    SelfTransferError,
    execute_transfer,
    get_transaction_for_user,
    list_transactions_for_user,
    search_recipient,
    search_recipients,
)

router = APIRouter()


@router.get("/search", response_model=UserSearchResult | list[UserSearchResult])
def search(
    account_number: str | None = Query(default=None, min_length=1, max_length=20),
    q: str | None = Query(default=None, min_length=1, max_length=120),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSearchResult | list[UserSearchResult]:
    """
    Backward compatible: `account_number` returns a single match (404 if none).
    Prefer `q` for discovery — returns a capped list (exact/prefix account or name).
    """
    if q is not None:
        matches = search_recipients(db, q, exclude_user_id=current_user.id)
        return [UserSearchResult.model_validate(user) for user in matches]

    if account_number is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide account_number or q",
        )

    recipient = search_recipient(db, account_number, exclude_user_id=current_user.id)
    if recipient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No account found with that number"
        )
    return UserSearchResult.model_validate(recipient)


def _to_receipt(transaction: Transaction, viewer: User) -> TransactionReceipt:
    direction = "sent" if transaction.sender_id == viewer.id else "received"
    balance_after = (
        transaction.sender.wallet.balance
        if direction == "sent"
        else transaction.receiver.wallet.balance
    )
    return TransactionReceipt(
        transaction_id=transaction.transaction_id,
        sender_account_number=transaction.sender.account_number,
        sender_name=transaction.sender.full_name,
        receiver_account_number=transaction.receiver.account_number,
        receiver_name=transaction.receiver.full_name,
        amount=transaction.amount,
        remark=transaction.remark,
        status=transaction.status,
        created_at=transaction.created_at,
        direction=direction,
        balance_after=balance_after,
    )


@router.post("/transfer", response_model=TransactionReceipt, status_code=status.HTTP_201_CREATED)
def transfer(
    payload: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionReceipt:
    try:
        transaction = execute_transfer(db, current_user, payload)
    except RecipientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SelfTransferError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (PinNotSetError, InvalidPinError, PinLockedError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except InsufficientBalanceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except FundsOnHoldError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    db.refresh(current_user)
    return _to_receipt(transaction, current_user)


@router.get("/history", response_model=PaginatedTransactions)
def history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedTransactions:
    items, total = list_transactions_for_user(db, current_user, limit, offset)

    summaries = []
    for tx in items:
        is_sent = tx.sender_id == current_user.id
        counterparty = tx.receiver if is_sent else tx.sender
        summaries.append(
            TransactionSummary(
                transaction_id=tx.transaction_id,
                counterparty_account_number=counterparty.account_number,
                counterparty_name=counterparty.full_name,
                amount=tx.amount,
                remark=tx.remark,
                status=tx.status,
                created_at=tx.created_at,
                direction="sent" if is_sent else "received",
            )
        )

    return PaginatedTransactions(items=summaries, total=total, limit=limit, offset=offset)


@router.get("/{transaction_id}", response_model=TransactionReceipt)
def get_receipt(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionReceipt:
    transaction = get_transaction_for_user(db, current_user, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return _to_receipt(transaction, current_user)
