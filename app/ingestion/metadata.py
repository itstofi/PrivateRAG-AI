from typing import Any

from app.ingestion.chunking import TextChunk
from app.storage.models import Document


def chunk_metadata(document: Document, chunk: TextChunk) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "document_id": document.id,
        "workspace_id": document.workspace_id,
        "source_filename": document.original_filename,
        "file_type": document.file_type,
        "chunk_number": chunk.chunk_number,
        "embedding_model": document.embedding_model,
    }
    if chunk.page_number is not None:
        metadata["page_number"] = chunk.page_number
    if chunk.section:
        metadata["section"] = chunk.section
    return metadata
