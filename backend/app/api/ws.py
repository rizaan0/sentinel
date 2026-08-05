"""
WebSocket Gateway for the Admin Dashboard's live feed: `/ws/admin/live`.
Fed by Redis Pub/Sub (see app/services/realtime.py). Registered directly on
the app (not under /api/v1) since it is not a REST resource.
"""
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.services.realtime import connection_manager

router = APIRouter()


def _is_admin_token(token: str) -> bool:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return False

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        return user is not None and user.is_active and user.role == UserRole.ADMIN
    finally:
        db.close()


@router.websocket("/ws/admin/live")
async def admin_live_feed(websocket: WebSocket, token: str = "") -> None:
    """
    Browsers cannot set Authorization headers on WebSocket handshakes, so
    the admin's JWT is passed as a query parameter instead.
    """
    if not token or not _is_admin_token(token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await connection_manager.connect(websocket)
    try:
        while True:
            # Admin clients don't need to send anything; this just keeps
            # the connection alive and detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
