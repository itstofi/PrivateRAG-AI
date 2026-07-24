from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_ollama
from app.core.config import Settings, get_settings
from app.services.ollama_service import OllamaService

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("")
async def list_models(
    ollama: OllamaService = Depends(get_ollama),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    status = await ollama.health()
    models = status.get("models", [])
    chat_models = (
        await ollama.list_chat_models(models) if status.get("connected") and models else []
    )
    return {
        **status,
        "chat_models": chat_models,
        "selected_chat_model": settings.ollama_chat_model,
        "selected_embedding_model": settings.ollama_embedding_model,
    }
