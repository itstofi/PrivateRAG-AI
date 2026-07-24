from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    app_name: str = "PrivateRAG AI"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    data_dir: Path = Path("data")
    database_url: str = "sqlite:///./data/database/private_rag.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "nomic-embed-text"
    api_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:8501"
    max_upload_size_mb: int = Field(default=25, ge=1, le=1024)
    max_document_chars: int = Field(default=2_000_000, ge=10_000, le=50_000_000)
    max_pdf_pages: int = Field(default=1000, ge=1, le=10_000)
    chunk_size: int = Field(default=900, ge=100, le=10000)
    chunk_overlap: int = Field(default=150, ge=0, le=5000)
    embedding_batch_size: int = Field(default=16, ge=1, le=256)
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.25, ge=0, le=1)
    use_mmr: bool = False
    max_context_chars: int = Field(default=12000, ge=1000, le=100000)
    temperature: float = Field(default=0.1, ge=0, le=2)

    @field_validator("ollama_base_url", "api_base_url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("must be an HTTP(S) URL")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_chunking(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def vector_dir(self) -> Path:
        return self.data_dir / "vector_store"

    @property
    def database_dir(self) -> Path:
        return self.data_dir / "database"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.upload_dir, self.vector_dir, self.database_dir):
            path.expanduser().resolve().mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
