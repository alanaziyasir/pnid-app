"""Request correlation and bounded-cardinality HTTP metrics."""

import logging
import re
import time
import uuid

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.logging import request_id

logger = logging.getLogger(__name__)
REQUESTS = Counter("pnid_http_requests_total", "HTTP responses", ["method", "route", "status"])
LATENCY = Histogram("pnid_http_request_duration_seconds", "Request latency", ["method", "route"])
VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
HTTP_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


class RequestTelemetry(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        candidate = request.headers.get("x-request-id", "")
        correlation = candidate if VALID_ID.fullmatch(candidate) else uuid.uuid4().hex
        token = request_id.set(correlation)
        started = time.monotonic()
        try:
            try:
                response = await call_next(request)
            except Exception as error:
                logger.error("request_failed", extra={"error_type": type(error).__name__})
                response = JSONResponse({"detail": "Internal server error"}, status_code=500)
            response.headers["X-Request-ID"] = correlation
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
            if request.url.path.startswith("/uploads/"):
                response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
            route = getattr(request.scope.get("route"), "path", "/unmatched")
            method = request.method if request.method in HTTP_METHODS else "OTHER"
            elapsed = time.monotonic() - started
            if route != "/metrics":
                REQUESTS.labels(method, route, str(response.status_code)).inc()
                LATENCY.labels(method, route).observe(elapsed)
                logger.info(
                    "http_request",
                    extra={
                        "method": method,
                        "route": route,
                        "status": response.status_code,
                        "duration_ms": round(elapsed * 1000, 2),
                    },
                )
            return response
        finally:
            request_id.reset(token)
