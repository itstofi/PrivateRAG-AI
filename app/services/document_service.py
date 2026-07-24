from functools import partial

from anyio import to_thread
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError
from app.core.security import generated_filename, safe_unlink, sha256_bytes
from app.ingestion.loaders import validate_upload
from app.ingestion.pipeline import IngestionPipeline
from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import VectorStore
from app.storage.models import Document
from app.storage.repositories import DocumentRepository, WorkspaceRepository


class DocumentService:
    def __init__(
        self,
        session: Session,
        embeddings: EmbeddingService,
        vector_store: VectorStore,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = DocumentRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.vector_store = vector_store
        self.pipeline = IngestionPipeline(self.repository, embeddings, vector_store, self.settings)

    async def upload(
        self, workspace_id: str, filename: str, content: bytes, content_type: str | None
    ) -> tuple[Document, dict[str, int | str]]:
        self.workspaces.get(workspace_id)
        extension = validate_upload(filename, content, self.settings.max_upload_bytes, content_type)
        digest = sha256_bytes(content)
        duplicate = self.repository.find_duplicate(workspace_id, digest)
        if duplicate:
            raise ConflictError(
                f"'{filename}' duplicates the existing document '{duplicate.original_filename}'."
            )
        stored_filename = generated_filename(filename)
        path = self.settings.upload_dir / stored_filename
        await to_thread.run_sync(partial(path.write_bytes, content))
        try:
            document = self.repository.create(
                workspace_id=workspace_id,
                original_filename=filename,
                stored_filename=stored_filename,
                file_type=extension.removeprefix("."),
                file_size=len(content),
                sha256=digest,
                status="pending",
                embedding_model=self.settings.ollama_embedding_model,
            )
        except Exception:
            safe_unlink(self.settings.upload_dir, path)
            raise
        try:
            summary = await self.pipeline.process(document, path)
        except Exception:
            return document, {"status": "failed", "pages": 0, "chunks": 0}
        return document, summary

    async def reindex(self, document_id: str) -> tuple[Document, dict[str, int | str]]:
        document = self.repository.get(document_id)
        document.embedding_model = self.settings.ollama_embedding_model
        path = self.settings.upload_dir / document.stored_filename
        summary = await self.pipeline.process(document, path)
        return document, summary

    def delete(self, document_id: str) -> None:
        document = self.repository.get(document_id)
        self.vector_store.delete_document(document.id)
        safe_unlink(self.settings.upload_dir, self.settings.upload_dir / document.stored_filename)
        self.repository.delete(document)
