from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.rag.retriever import Retriever
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.storage.repositories import ChatRepository, WorkspaceRepository
from tests.conftest import FakeEmbeddings, FakeGenerator, FakeVectorStore


@pytest.mark.asyncio
async def test_upload_index_query_persist_and_delete(
    session: Session, settings, tmp_path: Path
) -> None:
    settings.ensure_directories()
    workspace = WorkspaceRepository(session).create("Employment")
    store = FakeVectorStore()
    documents = DocumentService(session, FakeEmbeddings(), store, settings)
    content = b"FICTIONAL POLICY\nEmployees receive two paid volunteer days each calendar year."
    document, summary = await documents.upload(workspace.id, "policy.txt", content, "text/plain")
    assert summary["status"] == "indexed"
    assert document.status == "indexed"
    assert store.count(workspace.id) == 1

    with pytest.raises(ConflictError):
        await documents.upload(workspace.id, "copy.txt", content, "text/plain")

    chat_service = ChatService(
        session, Retriever(FakeEmbeddings(), store), FakeGenerator(), settings
    )
    answer = await chat_service.query(
        workspace.id,
        "How many volunteer days?",
        "fake-local-model",
        None,
        {"top_k": 5, "similarity_threshold": 0.2},
    )
    assert "two volunteer days" in answer["answer"]
    persisted = ChatRepository(session).get(answer["chat_id"])
    assert [message.role for message in persisted.messages] == ["user", "assistant"]
    assert persisted.messages[1].citations[0]["source_filename"] == "policy.txt"

    upload_path = settings.upload_dir / document.stored_filename
    assert upload_path.exists()
    documents.delete(document.id)
    assert not upload_path.exists()
    assert store.count(workspace.id) == 0


@pytest.mark.asyncio
async def test_workspace_isolation(session: Session, settings) -> None:
    settings.ensure_directories()
    first = WorkspaceRepository(session).create("First")
    second = WorkspaceRepository(session).create("Second")
    store = FakeVectorStore()
    service = DocumentService(session, FakeEmbeddings(), store, settings)
    await service.upload(first.id, "first.txt", b"Alpha private fact", "text/plain")
    await service.upload(second.id, "second.txt", b"Beta private fact", "text/plain")
    results = await Retriever(FakeEmbeddings(), store).retrieve("fact", first.id, 10, 0.1, False)
    assert len(results) == 1
    assert "Alpha" in results[0].text
