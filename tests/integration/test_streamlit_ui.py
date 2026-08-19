import json
from typing import Any

import httpx
import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize(
    ("section", "expected_header"),
    [
        ("Chat", "Chat"),
        ("Documents", "Documents"),
        ("Workspaces", "Workspaces"),
        ("Settings", "Settings"),
        ("System health", "System health"),
    ],
)
def test_streamlit_pages_render_when_api_is_offline(
    section: str, expected_header: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:9")
    app = AppTest.from_file("frontend/streamlit_app.py", default_timeout=10).run()
    app.radio[0].set_value(section).run()
    assert not app.exception
    assert expected_header in [header.value for header in app.header]


def test_workspace_form_explains_blank_submission(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:9")
    app = AppTest.from_file("frontend/streamlit_app.py", default_timeout=10).run()
    app.radio[0].set_value("Workspaces").run()
    app.button[0].click().run()

    assert not app.exception
    assert "Enter a workspace name before creating it." in [
        warning.value for warning in app.warning
    ]


def test_new_chat_button_resets_history_without_mutating_widget_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = {
        "id": "workspace-1",
        "name": "Test workspace",
        "document_count": 0,
        "chunk_count": 0,
        "active_chunk_count": 0,
        "chat_count": 1,
    }

    def fake_request(method: str, url: str, **_kwargs: Any) -> httpx.Response:
        path = httpx.URL(url).path
        payload: Any
        if path == "/api/status":
            payload = {
                "ollama": {
                    "connected": True,
                    "embedding_model_available": False,
                },
                "vector_store": {"active_chunk_count": 0},
            }
        elif path == "/api/models":
            payload = {"models": ["llama3.2:latest"]}
        elif path == "/api/workspaces":
            payload = [workspace]
        elif path == "/api/chats":
            payload = [
                {
                    "id": "chat-1",
                    "title": "Existing chat",
                    "workspace_id": "workspace-1",
                }
            ]
        else:
            raise AssertionError(f"Unexpected {method} request to {url}")
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(httpx, "request", fake_request)
    app = AppTest.from_file("frontend/streamlit_app.py", default_timeout=10).run()
    new_chat = next(button for button in app.button if button.label == "New chat")
    new_chat.click().run()

    assert not app.exception


def test_system_health_does_not_render_streamlit_internal_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(method: str, url: str, **_kwargs: Any) -> httpx.Response:
        path = httpx.URL(url).path
        if path == "/api/status":
            return httpx.Response(
                200,
                json={
                    "ollama": {
                        "connected": True,
                        "chat_model_available": True,
                        "embedding_model_available": True,
                    },
                    "vector_store": {"active_chunk_count": 3},
                    "document_count": 2,
                    "storage_location": "/tmp/private-rag",
                },
            )
        if path == "/api/models":
            return httpx.Response(200, json={"models": ["llama3.2:latest"]})
        if path == "/api/workspaces":
            return httpx.Response(200, json=[])
        raise AssertionError(f"Unexpected {method} request to {url}")

    monkeypatch.setattr(httpx, "request", fake_request)
    app = AppTest.from_file("frontend/streamlit_app.py", default_timeout=10).run()
    app.radio[0].set_value("System health").run()

    assert not app.get("doc_string")
    assert "/tmp/private-rag" not in json.dumps(app.json[0].value)
