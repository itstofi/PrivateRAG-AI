import pytest

from app.rag.retriever import Retriever
from tests.conftest import FakeEmbeddings, FakeVectorStore


@pytest.mark.asyncio
async def test_retrieval_is_filtered_by_workspace() -> None:
    store = FakeVectorStore()
    store.add(
        ["one:1", "two:1"],
        ["Workspace one", "Workspace two"],
        [[1.0, 0.0], [0.0, 1.0]],
        [
            {
                "workspace_id": "one",
                "document_id": "one",
                "source_filename": "one.txt",
            },
            {
                "workspace_id": "two",
                "document_id": "two",
                "source_filename": "two.txt",
            },
        ],
    )
    results = await Retriever(FakeEmbeddings(), store).retrieve("question", "one", 5, 0.2, False)
    assert [item.text for item in results] == ["Workspace one"]
