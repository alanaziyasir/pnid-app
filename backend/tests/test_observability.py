import asyncio
import json
import logging
import re

import pytest
from app import main
from app.logging import JsonFormatter, request_id
from app.observability import RequestTelemetry
from app.resilience import CircuitBreaker, CircuitOpenError
from starlette.requests import Request


def test_health_features_and_metrics(client, monkeypatch):
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/").json()["version"] == "1.0.0"
    assert client.get("/api/features").json() == {"chat": True}
    response = client.get("/metrics")
    assert "pnid_http_requests_total" in response.text
    assert "pnid_http_request_duration_seconds" in response.text
    assert "text/plain" in response.headers["content-type"]
    monkeypatch.setattr(main, "ENABLE_METRICS", False)
    assert client.get("/metrics").status_code == 404


def test_request_ids_are_validated_and_exposed_to_browser(client):
    assert (
        client.get("/health", headers={"X-Request-ID": "qa-request"}).headers["x-request-id"]
        == "qa-request"
    )
    response = client.get(
        "/health", headers={"X-Request-ID": "private data " * 10, "Origin": "http://localhost:3000"}
    )
    assert re.fullmatch("[a-f0-9]{32}", response.headers["x-request-id"])
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]
    assert request_id.get() == "-"


def test_logs_allowlist_fields_and_scrub_interpolated_data():
    record = logging.LogRecord("app", logging.ERROR, "", 1, "secret: %s", ("private",), None)
    record.token = "do-not-log"
    record.status = 500
    record.exc_info = (ValueError, ValueError("provider-secret"), None)
    encoded = JsonFormatter().format(record)
    assert json.loads(encoded)["status"] == 500
    assert "private" not in encoded
    assert "secret" not in encoded
    assert "do-not-log" not in encoded
    record = logging.LogRecord("app", logging.ERROR, "", 1, "private-message", (), None)
    assert "private-message" not in JsonFormatter().format(record)


def test_unexpected_errors_keep_correlation_without_exposing_exception_text():
    async def fail(request):
        raise ValueError("private-exception-text")

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/failure",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
        }
    )
    middleware = RequestTelemetry(main.app)
    response = asyncio.run(middleware.dispatch(request, fail))
    assert response.status_code == 500
    assert b"private-exception-text" not in response.body
    assert re.fullmatch("[a-f0-9]{32}", response.headers["x-request-id"])
    assert request_id.get() == "-"


def test_circuit_half_open_probe_recovers_or_reopens():
    now = [0.0]
    circuit = CircuitBreaker(threshold=1, cooldown=10, clock=lambda: now[0])
    circuit.acquire()
    circuit.failure()
    with pytest.raises(CircuitOpenError):
        circuit.acquire()
    now[0] = 10
    circuit.acquire()
    with pytest.raises(CircuitOpenError):
        circuit.acquire()
    circuit.failure()
    now[0] = 20
    circuit.acquire()
    circuit.success()
    circuit.acquire()
    assert circuit.failures == 0
