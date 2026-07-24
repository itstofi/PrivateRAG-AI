import hashlib
import math
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    score: float
    embedding: list[float] | None = None


class VectorStore:
    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self.settings = settings or get_settings()
        try:
            self.client = client or chromadb.PersistentClient(
                path=str(self.settings.vector_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._get_collection()
        except Exception as exc:
            raise ServiceUnavailableError("The local vector database is unavailable.") from exc

    def _collection_name(self, model: str | None = None) -> str:
        selected = model or self.settings.ollama_embedding_model
        digest = hashlib.sha256(selected.encode("utf-8")).hexdigest()[:12]
        return f"private_rag_chunks_{digest}"

    def _get_collection(self, model: str | None = None) -> Any:
        selected = model or self.settings.ollama_embedding_model
        return self.client.get_or_create_collection(
            self._collection_name(selected),
            metadata={"hnsw:space": "cosine", "embedding_model": selected},
        )

    @property
    def collection(self) -> Any:
        return self._get_collection()

    def _managed_collections(self) -> list[Any]:
        return [
            collection
            for collection in self.client.list_collections()
            if collection.name == "private_rag_chunks"
            or collection.name.startswith("private_rag_chunks_")
        ]

    def add(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if ids:
            self.collection.upsert(
                ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas
            )

    def search(
        self,
        query_embedding: list[float],
        workspace_id: str,
        top_k: int,
        threshold: float,
        include_embeddings: bool = False,
    ) -> list[SearchResult]:
        count = self.collection.count()
        if not count:
            return []
        include = ["documents", "metadatas", "distances"]
        if include_embeddings:
            include.append("embeddings")
        raw = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(max(top_k, 1), count),
            where={"workspace_id": workspace_id},
            include=include,
        )
        embeddings = raw.get("embeddings")
        results: list[SearchResult] = []
        for index, chunk_id in enumerate(raw["ids"][0]):
            distance = float(raw["distances"][0][index])
            score = max(0.0, min(1.0, 1.0 - distance))
            if score >= threshold:
                vector = None
                if embeddings is not None:
                    vector = list(embeddings[0][index])
                results.append(
                    SearchResult(
                        chunk_id=chunk_id,
                        text=raw["documents"][0][index],
                        metadata=raw["metadatas"][0][index],
                        score=score,
                        embedding=vector,
                    )
                )
        return results

    def delete_document(self, document_id: str) -> None:
        for collection in self._managed_collections():
            collection.delete(where={"document_id": document_id})

    def delete_workspace(self, workspace_id: str) -> None:
        for collection in self._managed_collections():
            collection.delete(where={"workspace_id": workspace_id})

    def count(self, workspace_id: str | None = None) -> int:
        if workspace_id is None:
            return self.collection.count()
        result = self.collection.get(where={"workspace_id": workspace_id}, include=[])
        return len(result["ids"])

    def total_count(self) -> int:
        return sum(collection.count() for collection in self._managed_collections())


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0
