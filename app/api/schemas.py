from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WorkspaceUpdate(WorkspaceCreate):
    pass


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class WorkspaceDetail(WorkspaceRead):
    document_count: int
    chunk_count: int
    active_chunk_count: int
    chat_count: int


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    original_filename: str
    file_type: str
    file_size: int
    sha256: str
    status: str
    embedding_model: str
    processing_error: str | None
    page_count: int
    chunk_count: int
    uploaded_at: datetime


class UploadResponse(BaseModel):
    document: DocumentRead
    summary: dict[str, int | str]


class ChatCreate(BaseModel):
    workspace_id: str
    model: str = Field(min_length=1, max_length=120)
    title: str = Field(default="New chat", min_length=1, max_length=160)


class ChatUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    model: str
    workspace_id: str
    citations: list[dict[str, Any]]
    retrieval_config: dict[str, Any]
    created_at: datetime


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    title: str
    model: str
    created_at: datetime
    updated_at: datetime


class ChatDetail(ChatRead):
    messages: list[MessageRead]


class RetrievalConfig(BaseModel):
    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.25, ge=0, le=1)
    use_mmr: bool = False
    max_context_chars: int = Field(default=12000, ge=1000, le=100000)
    temperature: float = Field(default=0.1, ge=0, le=2)


class QueryRequest(BaseModel):
    workspace_id: str
    question: str = Field(min_length=1, max_length=10000)
    chat_id: str | None = None
    model: str = Field(min_length=1, max_length=120)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)


class QueryResponse(BaseModel):
    chat_id: str
    answer: str
    citations: list[dict[str, Any]]
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    application: str
    version: str


class RuntimeSettings(BaseModel):
    ollama_base_url: str | None = None
    ollama_chat_model: str | None = Field(default=None, min_length=1, max_length=120)
    ollama_embedding_model: str | None = Field(default=None, min_length=1, max_length=120)
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_k: int | None = Field(default=None, ge=1, le=50)
    similarity_threshold: float | None = Field(default=None, ge=0, le=1)
    chunk_size: int | None = Field(default=None, ge=100, le=10000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=5000)
    max_upload_size_mb: int | None = Field(default=None, ge=1, le=1024)
