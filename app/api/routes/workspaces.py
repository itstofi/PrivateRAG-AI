from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_vector_store
from app.api.schemas import WorkspaceCreate, WorkspaceDetail, WorkspaceRead, WorkspaceUpdate
from app.rag.vector_store import VectorStore
from app.services.workspace_service import WorkspaceService
from app.storage.database import get_db
from app.storage.repositories import WorkspaceRepository

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def detail(
    repository: WorkspaceRepository, vector_store: VectorStore, workspace_id: str
) -> WorkspaceDetail:
    workspace = repository.get(workspace_id)
    return WorkspaceDetail.model_validate(
        {
            **workspace.__dict__,
            **repository.stats(workspace_id),
            "active_chunk_count": vector_store.count(workspace_id),
        }
    )


@router.get("", response_model=list[WorkspaceDetail])
def list_workspaces(
    session: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
) -> list[WorkspaceDetail]:
    repository = WorkspaceRepository(session)
    return [detail(repository, vector_store, workspace.id) for workspace in repository.list()]


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, session: Session = Depends(get_db)) -> WorkspaceRead:
    return WorkspaceRead.model_validate(WorkspaceRepository(session).create(payload.name))


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def rename_workspace(
    workspace_id: str, payload: WorkspaceUpdate, session: Session = Depends(get_db)
) -> WorkspaceRead:
    return WorkspaceRead.model_validate(
        WorkspaceRepository(session).rename(workspace_id, payload.name)
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: str,
    session: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
) -> Response:
    WorkspaceService(session, vector_store).delete(workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
