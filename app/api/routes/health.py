from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import __version__
from app.api.dependencies import get_ollama, get_vector_store
from app.api.schemas import HealthResponse
from app.core.config import Settings, get_settings
from app.rag.vector_store import VectorStore
from app.services.ollama_service import OllamaService
from app.storage.database import get_db
from app.storage.models import Document

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "application": settings.app_name, "version": __version__}


@router.get("/api/status")
async def status(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    ollama: OllamaService = Depends(get_ollama),
    vector_store: VectorStore = Depends(get_vector_store),
) -> dict[str, Any]:
    session.execute(text("SELECT 1"))
    document_count = session.scalar(select(func.count(Document.id))) or 0
    ollama_status = await ollama.health()
    return {
        "ollama": ollama_status,
        "sqlite": {"connected": True},
        "vector_store": {
            "connected": True,
            "active_chunk_count": vector_store.count(),
            "total_chunk_count": vector_store.total_count(),
            "embedding_model": settings.ollama_embedding_model,
        },
        "document_count": document_count,
        "storage_location": str(settings.data_dir.resolve()),
        "privacy": {
            "local_inference": True,
            "local_documents": True,
            "local_embeddings": True,
            "local_chat_history": True,
            "cloud_ai_configured": False,
            "offline_capable": True,
        },
    }
