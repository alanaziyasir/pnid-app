"""All API tests use disposable storage and an in-memory provider transport."""

import atexit
import os
import tempfile

import httpx
import pytest
from fastapi.testclient import TestClient

_storage = tempfile.TemporaryDirectory(prefix="pnid-tests-")
atexit.register(_storage.cleanup)
os.environ["UPLOAD_DIR"] = _storage.name
os.environ["GRAPHML_PATH"] = f"{_storage.name}/missing.graphml"
os.environ["GROQ_API_KEY"] = "unit-test-not-a-secret"
os.environ["ENABLE_METRICS"] = "true"
os.environ["ENABLE_CHAT"] = "true"

from app.main import app  # noqa: E402
from app.resilience import CircuitBreaker  # noqa: E402
from app.routers import chat, detection, upload  # noqa: E402


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(upload, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(detection, "UPLOAD_DIR", tmp_path)
    # StaticFiles resolves paths from all_directories, not just directory.
    static = next(route.app for route in app.routes if route.path == "/uploads")
    monkeypatch.setattr(static, "directory", str(tmp_path))
    monkeypatch.setattr(static, "all_directories", [str(tmp_path)])
    monkeypatch.setattr(chat, "provider_circuit", CircuitBreaker())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def provider(monkeypatch):
    calls = []
    behavior = {"status": 200, "body": {"choices": [{"message": {"content": "Connected"}}]}}
    original_client = httpx.AsyncClient

    def respond(request):
        calls.append(request)
        if "error" in behavior:
            raise behavior["error"]
        return httpx.Response(behavior["status"], json=behavior["body"])

    def factory(**kwargs):
        return original_client(**kwargs, transport=httpx.MockTransport(respond))

    monkeypatch.setattr(chat.httpx, "AsyncClient", factory)
    return behavior, calls
