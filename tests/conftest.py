from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.rag.vector_store import SearchResult
from app.storage.database import Base


class FakeEmbeddings:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]


class FakeVectorStore:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[str, list[float], dict[str, Any]]] = {}

    def add(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        for chunk_id, text, embedding, metadata in zip(
            ids, texts, embeddings, metadatas, strict=True
        ):
            self.rows[chunk_id] = (text, embedding, metadata)

    def search(
        self,
        _query_embedding: list[float],
        workspace_id: str,
        top_k: int,
        threshold: float,
        include_embeddings: bool = False,
    ) -> list[SearchResult]:
        results = []
        for chunk_id, (text, embedding, metadata) in self.rows.items():
            if metadata["workspace_id"] == workspace_id and threshold <= 0.9:
                results.append(
                    SearchResult(
                        chunk_id,
                        text,
                        metadata,
                        0.9,
                        embedding if include_embeddings else None,
                    )
                )
        return results[:top_k]

    def delete_document(self, document_id: str) -> None:
        self.rows = {
            key: value for key, value in self.rows.items() if value[2]["document_id"] != document_id
        }

    def delete_workspace(self, workspace_id: str) -> None:
        self.rows = {
            key: value
            for key, value in self.rows.items()
            if value[2]["workspace_id"] != workspace_id
        }

    def count(self, workspace_id: str | None = None) -> int:
        if workspace_id is None:
            return len(self.rows)
        return sum(value[2]["workspace_id"] == workspace_id for value in self.rows.values())

    def total_count(self) -> int:
        return len(self.rows)


class FakeGenerator:
    async def generate(self, _prompt: str, _model: str, _temperature: float) -> str:
        return "Employees receive two volunteer days. [Source 1]"

    async def stream(self, _prompt: str, _model: str, _temperature: float):
        for token in ("Employees receive ", "two volunteer days. [Source 1]"):
            yield token


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path / 'data' / 'database' / 'test.db'}",
        chunk_size=100,
        chunk_overlap=20,
    )


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        yield db
