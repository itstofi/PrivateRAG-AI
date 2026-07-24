from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import (
    get_embeddings,
    get_generator,
    get_ollama,
    get_retriever,
    get_vector_store,
)
from app.main import app
from app.rag.retriever import Retriever
from app.storage.database import Base, get_db
from tests.conftest import FakeEmbeddings, FakeGenerator, FakeVectorStore


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    store = FakeVectorStore()
    embeddings = FakeEmbeddings()

    def database_override() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = database_override
    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_embeddings] = lambda: embeddings
    app.dependency_overrides[get_retriever] = lambda: Retriever(embeddings, store)
    app.dependency_overrides[get_generator] = lambda: FakeGenerator()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_health_workspace_and_chat_api(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    workspace = client.post("/api/workspaces", json={"name": "API Workspace"})
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    upload = client.post(
        "/api/documents/upload",
        data={"workspace_id": workspace_id},
        files={"file": ("policy.txt", b"Employees receive two volunteer days.", "text/plain")},
    )
    assert upload.status_code == 201
    assert upload.json()["document"]["status"] == "indexed"

    query = client.post(
        "/api/chat/query",
        json={
            "workspace_id": workspace_id,
            "question": "How many volunteer days?",
            "model": "fake-model",
            "retrieval": {"top_k": 5, "similarity_threshold": 0.2},
        },
    )
    assert query.status_code == 200
    assert query.json()["citations"][0]["source_filename"] == "policy.txt"

    chat_id = query.json()["chat_id"]
    exported = client.get(f"/api/chats/{chat_id}/export")
    assert exported.status_code == 200
    assert "two volunteer days" in exported.text


def test_ollama_connection_failure_is_actionable(client: TestClient) -> None:
    class OfflineOllama:
        async def health(self):
            return {
                "connected": False,
                "models": [],
                "message": "Start it with `ollama serve`.",
            }

    app.dependency_overrides[get_ollama] = lambda: OfflineOllama()
    response = client.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert "ollama serve" in body["message"]
