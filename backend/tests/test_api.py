import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import main as app_module


client = TestClient(app_module.app)


def test_home():

    response = client.get("/")

    assert response.status_code == 200

    assert response.json()["assistant"] == "JARVIS"


def test_system_info_always_returns_numbers():

    response = client.get("/system-info")

    body = response.json()

    assert response.status_code == 200

    assert body["success"] is True

    for key in ("cpu", "ram", "storage"):

        assert isinstance(body[key], int)

    assert "network" in body


def test_capabilities_lists_websocket_and_modes():

    body = client.get("/capabilities").json()

    assert body["voice"]["websocket"] == "/ws/voice"

    assert "assistant" in body["modes"]

    assert "open_app" in body["intents"]


def test_models_exposes_provider_state():

    body = client.get("/models").json()

    assert body["success"] is True

    assert isinstance(body["providers"], list)

    assert all("available" in provider for provider in body["providers"])


def test_memory_endpoint():

    body = client.get("/memory").json()

    assert body["success"] is True

    assert set(("profile", "facts", "conversation_count") ).issubset(body)


def test_chat_rejects_empty_message():

    assert client.post("/chat", json={"message": "   "}).status_code == 400


def test_chat_remembers_and_recalls_without_ai():

    first = client.post("/chat", json={"message": "my name is TestUser"}).json()

    assert first["success"] is True

    second = client.post("/chat", json={"message": "what is my name"}).json()

    assert second["success"] is True

    assert "TestUser" in second["response"]

    # Router replies carry the action for the frontend.
    assert second["action"] == "recall"


def test_chat_system_status_is_local():

    body = client.post("/chat", json={"message": "system status"}).json()

    assert body["success"] is True

    assert "CPU" in body["response"]

    assert body["provider"] == "router"


def test_memory_clear():

    body = client.post(
        "/memory/clear",
        json={"scope": "conversation"},
    ).json()

    assert body["success"] is True


def test_state_changing_request_from_foreign_origin_is_rejected():

    response = client.post(
        "/chat",
        json={"message": "system status"},
        headers={"Origin": "http://evil.example"},
    )

    assert response.status_code == 403


def test_cross_site_fetch_metadata_is_rejected():

    response = client.post(
        "/memory/clear",
        json={"scope": "conversation"},
        headers={
            "Origin": "http://localhost:5173",
            "Sec-Fetch-Site": "cross-site",
        },
    )

    assert response.status_code == 403


def test_allowed_local_origin_is_accepted():

    response = client.post(
        "/memory/clear",
        json={"scope": "conversation"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200


def test_same_site_local_request_is_accepted():

    # The UI on :5173 -> API on :8000 is same-site, not cross-site.
    response = client.post(
        "/memory/clear",
        json={"scope": "conversation"},
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Sec-Fetch-Site": "same-site",
        },
    )

    assert response.status_code == 200


def test_read_only_request_allows_foreign_origin():

    # A foreign page may read public status, but it cannot cause effects.
    assert client.get("/", headers={"Origin": "http://evil.example"}).status_code == 200


def test_voice_websocket_rejects_foreign_origin():

    with pytest.raises(WebSocketDisconnect) as error:

        with client.websocket_connect(
            "/ws/voice",
            headers={"origin": "http://evil.example"},
        ) as websocket:

            websocket.receive_text()

    assert error.value.code == 1008
