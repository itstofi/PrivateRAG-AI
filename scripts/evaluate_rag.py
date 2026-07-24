import argparse
import asyncio
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.ingestion.chunking import chunk_pages
from app.ingestion.loaders import load_document
from app.rag.prompts import INSUFFICIENT_CONTEXT, build_prompt_bundle
from app.rag.query_quality import content_tokens, detect_conflicts
from app.rag.retriever import Retriever
from app.rag.vector_store import SearchResult

DIMENSIONS = 1024


def stable_bucket(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % DIMENSIONS


def local_embedding(text: str) -> list[float]:
    counts = Counter(content_tokens(text))
    vector = [0.0] * DIMENSIONS
    for token, count in counts.items():
        vector[stable_bucket(token)] += 1.0 + math.log(count)
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class LocalEvaluationEmbeddings:
    async def embed_query(self, text: str) -> list[float]:
        return local_embedding(text)


@dataclass
class IndexedChunk:
    chunk_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


class LocalEvaluationStore:
    def __init__(self, chunks: list[IndexedChunk]) -> None:
        self.chunks = chunks

    def search(
        self,
        query_embedding: list[float],
        workspace_id: str,
        top_k: int,
        threshold: float,
        include_embeddings: bool = False,
    ) -> list[SearchResult]:
        scored: list[SearchResult] = []
        for chunk in self.chunks:
            if chunk.metadata["workspace_id"] != workspace_id:
                continue
            score = sum(
                left * right for left, right in zip(query_embedding, chunk.embedding, strict=True)
            )
            if score >= threshold:
                scored.append(
                    SearchResult(
                        chunk.chunk_id,
                        chunk.text,
                        chunk.metadata,
                        score,
                        chunk.embedding if include_embeddings else None,
                    )
                )
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


def build_index(manifest: dict[str, Any]) -> list[IndexedChunk]:
    indexed: list[IndexedChunk] = []
    for document in manifest["documents"]:
        path = Path(document["path"])
        pages = load_document(path)
        chunks = chunk_pages(pages, chunk_size=500, overlap=80)
        document_id = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
        for chunk in chunks:
            metadata = {
                "workspace_id": document["workspace"],
                "document_id": document_id,
                "source_filename": path.name,
                "chunk_number": chunk.chunk_number,
            }
            if chunk.page_number is not None:
                metadata["page_number"] = chunk.page_number
            indexed.append(
                IndexedChunk(
                    f"{document_id}:{chunk.chunk_number}",
                    chunk.text,
                    local_embedding(chunk.text),
                    metadata,
                )
            )
    return indexed


async def evaluate(manifest: dict[str, Any]) -> dict[str, Any]:
    chunks = build_index(manifest)
    retriever = Retriever(LocalEvaluationEmbeddings(), LocalEvaluationStore(chunks))
    outcomes: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        results = await retriever.retrieve(
            case["question"],
            case["workspace"],
            top_k=6,
            threshold=0.15,
            use_mmr=True,
        )
        sources = list(dict.fromkeys(result.metadata["source_filename"] for result in results))
        expected = set(case["expected_sources"])
        source_success = expected.issubset(sources)
        workspace_success = all(
            result.metadata["workspace_id"] == case["workspace"] for result in results
        )
        should_refuse = not results
        refusal_success = should_refuse == case["expected_refusal"]
        conflicts = detect_conflicts(results)
        conflict_success = bool(conflicts) == case["expected_conflict"]
        bundle = build_prompt_bundle(case["question"], results, 6000, conflicts)
        citation_success = all(
            result.metadata.get("source_filename") and result.metadata.get("chunk_number")
            for result in bundle.included_results
        )
        if case["injection_case"]:
            injection_success = (
                "Instruction-like text detected" in bundle.prompt
                and "higher priority than the question" in bundle.prompt
                and bundle.prompt.index("higher priority") < bundle.prompt.index("<source_text>")
            )
        else:
            injection_success = True
        outcomes.append(
            {
                "id": case["id"],
                "retrieved_sources": sources,
                "expected_sources": case["expected_sources"],
                "decision": INSUFFICIENT_CONTEXT if should_refuse else "answer_from_context",
                "source_retrieval": source_success,
                "workspace_isolation": workspace_success,
                "citation_accuracy": citation_success,
                "refusal": refusal_success,
                "conflict_detection": conflict_success,
                "prompt_injection_resistance": injection_success,
                "passed": all(
                    (
                        source_success,
                        workspace_success,
                        citation_success,
                        refusal_success,
                        conflict_success,
                        injection_success,
                    )
                ),
            }
        )
    metrics = {
        key: sum(bool(outcome[key]) for outcome in outcomes) / len(outcomes)
        for key in (
            "source_retrieval",
            "workspace_isolation",
            "citation_accuracy",
            "refusal",
            "conflict_detection",
            "prompt_injection_resistance",
            "passed",
        )
    }
    return {"case_count": len(outcomes), "metrics": metrics, "cases": outcomes}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline PrivateRAG evaluation.")
    parser.add_argument("--dataset", default="evaluation/rag_cases.json")
    parser.add_argument("--output", default="evaluation/latest_results.json")
    args = parser.parse_args()
    manifest = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    report = asyncio.run(evaluate(manifest))
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["metrics"], indent=2))
    return 0 if report["metrics"]["passed"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
