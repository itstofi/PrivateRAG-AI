from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import safe_unlink
from app.rag.vector_store import VectorStore
from app.storage.repositories import DocumentRepository, WorkspaceRepository


class WorkspaceService:
    def __init__(
        self,
        session: Session,
        vector_store: VectorStore,
        settings: Settings | None = None,
    ) -> None:
        self.workspaces = WorkspaceRepository(session)
        self.documents = DocumentRepository(session)
        self.vector_store = vector_store
        self.settings = settings or get_settings()

    def delete(self, workspace_id: str) -> None:
        workspace = self.workspaces.get(workspace_id)
        documents = self.documents.list(workspace.id)
        self.vector_store.delete_workspace(workspace.id)
        for document in documents:
            safe_unlink(
                self.settings.upload_dir, self.settings.upload_dir / document.stored_filename
            )
        self.workspaces.delete(workspace.id)
