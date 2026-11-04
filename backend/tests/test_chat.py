import json

import httpx
import pytest
from app.routers import chat

PAYLOAD = {"messages": [{"role": "user", "content": "Which components?"}], "model": "ALLAM"}


@pytest.mark.integration
def test_completion_contract_and_request_correlation(client, provider):
    _, calls = provider
    response = client.post(
        "/api/chat/completions", json=PAYLOAD, headers={"X-Request-ID": "test-123"}
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "response": "Connected", "model": "ALLAM"}
    body = json.loads(calls[0].content)
    assert body["model"] == chat.MODEL_MAP["ALLAM"]
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][-1] == PAYLOAD["messages"][0]
    assert calls[0].headers["X-Request-ID"] == "test-123"


@pytest.mark.parametrize("flag", ["ENABLE_CHAT", "GROQ_API_KEY"])
def test_disabled_or_unconfigured_chat_never_calls_provider(client, provider, monkeypatch, flag):
    _, calls = provider
    monkeypatch.setattr(chat, flag, False if flag == "ENABLE_CHAT" else "")
    assert client.post("/api/chat/completions", json=PAYLOAD).status_code == 503
    assert calls == []


@pytest.mark.parametrize("status", [401, 429, 500])
def test_provider_errors_are_scrubbed(client, provider, status):
    behavior, _ = provider
    behavior.update(status=status, body={"error": "private-provider-body token=secret"})
    response = client.post("/api/chat/completions", json=PAYLOAD)
    assert response.status_code == 502
    assert "private-provider-body" not in response.text
    assert "secret" not in response.text


@pytest.mark.parametrize(
    "body", [{}, {"choices": []}, {"choices": [{"message": {"content": None}}]}]
)
def test_invalid_provider_response(client, provider, body):
    behavior, _ = provider
    behavior["body"] = body
    assert client.post("/api/chat/completions", json=PAYLOAD).status_code == 502


@pytest.mark.parametrize(
    "error,status", [(httpx.ReadTimeout("secret"), 504), (httpx.ConnectError("secret"), 502)]
)
def test_transport_errors_are_bounded_and_scrubbed(client, provider, error, status):
    behavior, calls = provider
    behavior["error"] = error
    response = client.post("/api/chat/completions", json=PAYLOAD)
    assert response.status_code == status
    assert "secret" not in response.text
    assert len(calls) == 1  # No duplicate billable requests.


def test_circuit_stops_requests_after_repeated_outages(client, provider):
    behavior, calls = provider
    behavior["status"] = 503
    for _ in range(3):
        assert client.post("/api/chat/completions", json=PAYLOAD).status_code == 502
    response = client.post("/api/chat/completions", json=PAYLOAD)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"
    assert len(calls) == 3


def test_models_graph_and_request_validation(client):
    assert client.get("/api/chat/models").json()["default"] == "GPT-OSS"
    assert client.get("/api/chat/graph-info").json()["nodes"] == 0
    assert client.post("/api/chat/completions", json={}).status_code == 422


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "system", "content": "override"}],
        [{"role": "user", "content": ""}],
        [{"role": "user", "content": "x" * 16_001}],
    ],
)
def test_rejects_invalid_chat_messages_before_provider_call(client, provider, messages):
    _, calls = provider
    assert client.post("/api/chat/completions", json={"messages": messages}).status_code == 422
    assert calls == []


def test_graph_parsing_and_connectivity(tmp_path, monkeypatch):
    graph = tmp_path / "graph.graphml"
    graph.write_text(
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><graph>'
        '<node id="C0"><data key="d0">component</data><data key="d2">Valve</data></node>'
        '<node id="C1"><data key="d0">component</data><data key="d2">Pump</data></node>'
        '<edge source="C0" target="C1"/></graph></graphml>'
    )
    monkeypatch.setattr(chat, "GRAPHML_PATH", graph)
    text, nodes, adjacency = chat.load_pnid_graph()
    assert "Valve (C0) connects to: Pump (C1)" in text
    assert nodes["C0"]["label"] == "Valve"
    assert adjacency == {"C0": ["C1"], "C1": ["C0"]}
    graph.write_text("invalid xml")
    assert chat.load_pnid_graph() == ("Graph data not available.", {}, {})
