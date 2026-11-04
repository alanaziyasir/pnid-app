"""Feature-event ingestion must be allowlisted, bounded, and counted."""

from app.routers import events
from prometheus_client import REGISTRY


def counter_value(event_type: str) -> int:
    return REGISTRY.get_sample_value(
        "pnid_frontend_events_total", labels={"event_type": event_type}
    )


def test_accepts_allowlisted_events_and_counts_them(client):
    before = counter_value("upload_completed") or 0
    response = client.post(
        "/api/events",
        json={"events": [{"type": "upload_completed"}, {"type": "upload_failed", "status": 415}]},
    )
    assert response.status_code == 202
    assert response.json() == {"accepted": 2}
    assert counter_value("upload_completed") == before + 1


def test_rejects_unknown_event_types(client):
    response = client.post("/api/events", json={"events": [{"type": "screenshot_taken"}]})
    assert response.status_code == 422


def test_rejects_batches_over_the_bound(client):
    response = client.post(
        "/api/events", json={"events": [{"type": "chat_sent"} for _ in range(21)]}
    )
    assert response.status_code == 422


def test_rejects_non_http_status_attributes(client):
    response = client.post(
        "/api/events", json={"events": [{"type": "chat_failed", "status": "leaked detail"}]}
    )
    assert response.status_code == 422


def test_never_echoes_payload_fields(client):
    response = client.post(
        "/api/events",
        json={"events": [{"type": "detection_failed", "status": 503, "filename": "a.png"}]},
    )
    assert response.status_code == 202
    assert set(response.json()) == {"accepted"}


def test_event_types_are_documented_in_the_env_contract():
    # The allowlist is the contract shared with frontend/lib/telemetry.ts; keep
    # both sides identical when adding a new product event.
    assert set(events.EventType.__args__) == {
        "upload_started",
        "upload_completed",
        "upload_failed",
        "detection_started",
        "detection_completed",
        "detection_failed",
        "chat_sent",
        "chat_failed",
    }
