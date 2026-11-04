"""Accept allowlisted frontend feature events for operational metrics.

The browser reports coarse product events (an upload finished, detection
failed) so frontend behavior is observable next to backend HTTP metrics.
Payloads carry only the event name and an optional coarse HTTP status;
never filenames, content, chat text, or user identifiers.
"""

import logging
from typing import Literal

from fastapi import APIRouter
from prometheus_client import Counter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["events"])
FRONTEND_EVENTS = Counter("pnid_frontend_events_total", "Frontend feature events", ["event_type"])
EventType = Literal[
    "upload_started",
    "upload_completed",
    "upload_failed",
    "detection_started",
    "detection_completed",
    "detection_failed",
    "chat_sent",
    "chat_failed",
]


class FrontendEvent(BaseModel):
    type: EventType
    status: int | None = Field(default=None, ge=100, le=599)


class EventBatch(BaseModel):
    events: list[FrontendEvent] = Field(min_length=1, max_length=20)


@router.post("/events", status_code=202)
async def record_events(batch: EventBatch) -> dict[str, int]:
    """Count allowlisted feature events; the response never echoes payload."""
    for event in batch.events:
        FRONTEND_EVENTS.labels(event.type).inc()
    logger.info("frontend_events", extra={"count": len(batch.events)})
    return {"accepted": len(batch.events)}
