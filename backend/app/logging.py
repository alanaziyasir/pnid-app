"""JSON logs with an allowlist: never serialize request bodies or exception messages."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

request_id: ContextVar[str] = ContextVar("request_id", default="-")
SAFE_FIELDS = ("method", "route", "status", "duration_ms", "error_type")
SAFE_EVENTS = {
    "graph_unavailable",
    "graph_load_failed",
    "chat_provider_rejected",
    "invalid_provider_response",
    "request_failed",
    "http_request",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Messages are event identifiers, not interpolated user/provider data.
        event = record.msg if not record.args and record.msg in SAFE_EVENTS else "application_event"
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": event,
            "request_id": request_id.get(),
        }
        payload.update({key: record.__dict__[key] for key in SAFE_FIELDS if key in record.__dict__})
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("app")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
