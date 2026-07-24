from sqlalchemy.orm import Session

from app.rag.prompts import INSUFFICIENT_CONTEXT, build_grounded_prompt
from app.rag.vector_store import SearchResult
from app.services.chat_service import citation_from_result, export_chat_markdown
from app.storage.repositories import ChatRepository, DocumentRepository, WorkspaceRepository


def result(workspace_id: str = "workspace") -> SearchResult:
    return SearchResult(
        "doc:1",
        "Employees receive two paid volunteer days.",
        {
            "source_filename": "policy.pdf",
            "page_number": 2,
            "chunk_number": 1,
            "workspace_id": workspace_id,
        },
        0.91,
    )


def test_prompt_contains_source_and_injection_boundary() -> None:
    prompt = build_grounded_prompt("How many days?", [result()], 1000)
    assert "[Source 1: policy.pdf, page 2]" in prompt
    assert "untrusted data" in prompt
    assert INSUFFICIENT_CONTEXT in prompt


def test_citation_formatting() -> None:
    citation = citation_from_result(1, result())
    assert citation["source_filename"] == "policy.pdf"
    assert citation["page_number"] == 2
    assert citation["relevance_score"] == 0.91


def test_repository_crud_duplicate_and_chat_export(session: Session) -> None:
    workspaces = WorkspaceRepository(session)
    documents = DocumentRepository(session)
    chats = ChatRepository(session)
    workspace = workspaces.create("Policies")
    document = documents.create(
        workspace_id=workspace.id,
        original_filename="policy.txt",
        stored_filename="abc.txt",
        file_type="txt",
        file_size=10,
        sha256="a" * 64,
    )
    assert documents.find_duplicate(workspace.id, "a" * 64).id == document.id
    chat = chats.create(workspace.id, "local-model", "Policy review")
    chats.add_message(chat, "user", "Question", "local-model", workspace.id)
    chats.add_message(
        chat,
        "assistant",
        "Answer",
        "local-model",
        workspace.id,
        [citation_from_result(1, result(workspace.id))],
    )
    markdown = export_chat_markdown(chats.get(chat.id))
    assert "# Policy review" in markdown
    assert "policy.pdf, page 2" in markdown
    assert workspaces.stats(workspace.id) == {
        "document_count": 1,
        "chunk_count": 0,
        "chat_count": 1,
    }
