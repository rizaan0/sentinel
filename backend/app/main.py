"""
Sentinel FastAPI application entrypoint.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ws
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.events import TRANSACTION_COMPLETED, event_bus
from app.services.monitoring_engine import evaluate_transaction_event
from app.services.realtime import start_redis_listener, stop_redis_listener
from app.workers.scheduler import start_scheduler, stop_scheduler

# Wire the Monitoring Engine as a subscriber of the canonical domain event.
# Per Architecture Rule: all asynchronous processing subscribes to
# `Transaction Completed Event` rather than being invoked directly by the
# Transaction Service.
event_bus.subscribe(TRANSACTION_COMPLETED, evaluate_transaction_event)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Background jobs (scheduled reconciliation, the Redis listener feeding
    # the WebSocket gateway) are skipped in the test environment: tests
    # exercise the business logic/API responses directly, and starting a
    # real asyncio Redis connection + scheduler on every TestClient-driven
    # lifespan cycle adds heavy, unnecessary overhead.
    if settings.ENVIRONMENT != "test":
        start_scheduler()
        start_redis_listener()
    yield
    if settings.ENVIRONMENT != "test":
        await stop_redis_listener()
        stop_scheduler()


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router)


@app.get("/")
def root() -> dict:
    return {"service": settings.APP_NAME, "status": "running"}
