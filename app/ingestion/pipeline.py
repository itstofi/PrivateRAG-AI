import logging
from functools import partial
from pathlib import Path

from anyio import to_thread

from app.core.config import Settings, get_settings
from app.ingestion.chunking import chunk_pages
from app.ingestion.loaders import load_document
from app.ingestion.metadata import chunk_metadata
from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import VectorStore
from app.storage.models import Document
from app.storage.repositories import DocumentRepository

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(
        self,
        repository: DocumentRepository,
        embeddings: EmbeddingService,
        vector_store: VectorStore,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.settings = settings or get_settings()

    async def process(self, document: Document, path: Path) -> dict[str, int | str]:
        self.repository.update_status(document, "processing")
        try:
            pages = await to_thread.run_sync(
                partial(
                    load_document,
                    path,
                    self.settings.max_pdf_pages,
                    self.settings.max_document_chars,
                )
            )
            chunks = await to_thread.run_sync(
                partial(
                    chunk_pages,
                    pages,
                    self.settings.chunk_size,
                    self.settings.chunk_overlap,
                )
            )
            if not chunks:
                raise ValueError("No usable text chunks were produced.")
            vectors = await self.embeddings.embed_documents([chunk.text for chunk in chunks])
            ids = [f"{document.id}:{chunk.chunk_number}" for chunk in chunks]
            await to_thread.run_sync(partial(self.vector_store.delete_document, document.id))
            await to_thread.run_sync(
                partial(
                    self.vector_store.add,
                    ids,
                    [chunk.text for chunk in chunks],
                    vectors,
                    [chunk_metadata(document, chunk) for chunk in chunks],
                )
            )
            self.repository.update_status(
                document, "indexed", page_count=len(pages), chunk_count=len(chunks)
            )
            return {"status": "indexed", "pages": len(pages), "chunks": len(chunks)}
        except Exception as exc:
            await to_thread.run_sync(partial(self.vector_store.delete_document, document.id))
            self.repository.update_status(
                document, "failed", error=str(exc)[:1000], page_count=0, chunk_count=0
            )
            logger.exception("Document processing failed for id=%s", document.id)
            raise
