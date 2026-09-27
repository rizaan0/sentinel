"""
Aggregates all v1 API routers. Each phase adds its own router include here.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    assistant,
    auth,
    fraud_alerts,
    health,
    holds,
    pin,
    predictions,
    reconciliation,
    transactions,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(pin.router, prefix="/pin", tags=["pin"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(
    reconciliation.router, prefix="/reconciliation", tags=["reconciliation"]
)
api_router.include_router(fraud_alerts.router, prefix="/fraud-alerts", tags=["fraud-alerts"])
api_router.include_router(holds.router, prefix="/holds", tags=["holds"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
