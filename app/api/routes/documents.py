from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_embeddings, get_vector_store
from app.api.schemas import DocumentRead, UploadResponse
from app.core.config import Settings, get_settings
from app.rag.embeddings import EmbeddingService
from app.rag.vector_store import VectorStore
from app.services.document_service import DocumentService
from app.storage.database import get_db
from app.storage.repositories import DocumentRepository

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(
    workspace_id: str | None = Query(default=None), session: Session = Depends(get_db)
) -> list[DocumentRead]:
    return [
        DocumentRead.model_validate(item) for item in DocumentRepository(session).list(workspace_id)
    ]


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    embeddings: EmbeddingService = Depends(get_embeddings),
    vector_store: VectorStore = Depends(get_vector_store),
) -> UploadResponse:
    content = await file.read(settings.max_upload_bytes + 1)
    document, summary = await DocumentService(session, embeddings, vector_store, settings).upload(
        workspace_id, file.filename or "", content, file.content_type
    )
    return UploadResponse(document=DocumentRead.model_validate(document), summary=summary)


@router.post("/{document_id}/reindex", response_model=UploadResponse)
async def reindex_document(
    document_id: str,
    session: Session = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embeddings),
    vector_store: VectorStore = Depends(get_vector_store),
) -> UploadResponse:
    document, summary = await DocumentService(session, embeddings, vector_store).reindex(
        document_id
    )
    return UploadResponse(document=DocumentRead.model_validate(document), summary=summary)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    session: Session = Depends(get_db),
    embeddings: EmbeddingService = Depends(get_embeddings),
    vector_store: VectorStore = Depends(get_vector_store),
) -> Response:
    DocumentService(session, embeddings, vector_store).delete(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
