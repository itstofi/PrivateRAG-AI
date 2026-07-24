from typing import Any

from fastapi import APIRouter, Depends

from app.api.schemas import RuntimeSettings
from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError

router = APIRouter(prefix="/api/settings", tags=["settings"])

FIELDS = (
    "ollama_base_url",
    "ollama_chat_model",
    "ollama_embedding_model",
    "temperature",
    "top_k",
    "similarity_threshold",
    "chunk_size",
    "chunk_overlap",
    "max_upload_size_mb",
)


def public_settings(settings: Settings) -> dict[str, Any]:
    return {field: getattr(settings, field) for field in FIELDS}


@router.get("")
def read_settings(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return public_settings(settings)


@router.patch("")
def update_settings(
    payload: RuntimeSettings, settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    changes = payload.model_dump(exclude_none=True)
    chunk_size = int(changes.get("chunk_size", settings.chunk_size))
    overlap = int(changes.get("chunk_overlap", settings.chunk_overlap))
    if overlap >= chunk_size:
        raise ValidationError("Chunk overlap must be smaller than chunk size.")
    url = changes.get("ollama_base_url")
    if url and not str(url).startswith(("http://", "https://")):
        raise ValidationError("Ollama URL must be an HTTP(S) URL.")
    for field, value in changes.items():
        setattr(settings, field, str(value).rstrip("/") if field == "ollama_base_url" else value)
    return public_settings(settings)
