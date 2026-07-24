from functools import partial
from typing import Protocol

from anyio import to_thread

from app.rag.query_quality import deduplicate_results, query_variants
from app.rag.vector_store import SearchResult, cosine_similarity


class QueryEmbeddingProvider(Protocol):
    async def embed_query(self, text: str) -> list[float]: ...


class VectorSearchProvider(Protocol):
    def search(
        self,
        query_embedding: list[float],
        workspace_id: str,
        top_k: int,
        threshold: float,
        include_embeddings: bool = False,
    ) -> list[SearchResult]: ...


class Retriever:
    def __init__(
        self, embeddings: QueryEmbeddingProvider, vector_store: VectorSearchProvider
    ) -> None:
        self.embeddings = embeddings
        self.vector_store = vector_store

    async def retrieve(
        self,
        question: str,
        workspace_id: str,
        top_k: int,
        threshold: float,
        use_mmr: bool,
    ) -> list[SearchResult]:
        variants = query_variants(question)
        if not variants:
            return []
        candidate_limit = max(top_k * 4, top_k)
        merged: dict[str, SearchResult] = {}
        for variant in variants:
            query = await self.embeddings.embed_query(variant)
            matches = await to_thread.run_sync(
                partial(
                    self.vector_store.search,
                    query,
                    workspace_id,
                    candidate_limit,
                    threshold,
                    use_mmr,
                )
            )
            for match in matches:
                existing = merged.get(match.chunk_id)
                if existing is None or match.score > existing.score:
                    merged[match.chunk_id] = match
        candidates = sorted(merged.values(), key=lambda item: item.score, reverse=True)
        candidates = deduplicate_results(candidates)
        if not use_mmr or len(candidates) <= top_k:
            return candidates[:top_k]
        selected: list[SearchResult] = []
        remaining = candidates.copy()
        while remaining and len(selected) < top_k:
            if not selected:
                choice = remaining[0]
            else:
                choice = max(
                    remaining,
                    key=lambda item: 0.7 * item.score
                    - 0.3
                    * max(
                        cosine_similarity(item.embedding or [], chosen.embedding or [])
                        for chosen in selected
                    ),
                )
            selected.append(choice)
            remaining.remove(choice)
        return sorted(selected, key=lambda item: item.score, reverse=True)
