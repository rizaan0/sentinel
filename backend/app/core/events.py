"""
Domain event bus.

Architecture Rule: `Transaction Completed Event` is the canonical domain
event in Sentinel. All asynchronous processing (monitoring, live dashboard
updates, future analytics, notifications, etc.) subscribes to this event
rather than being invoked directly by the Transaction Service.

This starts as a simple in-process synchronous dispatcher; the interface is
intentionally small so it can be swapped for a real broker later without
touching any publisher/subscriber code.
"""
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger("sentinel.events")

TRANSACTION_COMPLETED = "transaction.completed"


@dataclass(frozen=True)
class TransactionCompletedEvent:
    transaction_id: str
    sender_id: int
    receiver_id: int
    amount: Decimal
    result: dict | None = None


EventHandler = Callable[[TransactionCompletedEvent], None]


@dataclass
class EventBus:
    _subscribers: dict[str, list[EventHandler]] = field(default_factory=lambda: defaultdict(list))

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)

    def publish(self, event_name: str, event: TransactionCompletedEvent) -> None:
        for handler in self._subscribers.get(event_name, []):
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                # A subscriber failing (e.g. the Monitoring Engine) must never
                # break the payment flow, which has already committed.
                logger.exception(
                    "Event handler %r failed for %s (transaction_id=%s)",
                    handler,
                    event_name,
                    event.transaction_id,
                )


event_bus = EventBus()
