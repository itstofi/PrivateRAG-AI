from functools import lru_cache

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.rag.embeddings import EmbeddingService
from app.rag.generator import Generator
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.services.ollama_service import OllamaService
from app.storage.database import get_db


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore(get_settings())


def get_ollama(settings: Settings = Depends(get_settings)) -> OllamaService:
    return OllamaService(settings)


def get_embeddings(
    ollama: OllamaService = Depends(get_ollama),
    settings: Settings = Depends(get_settings),
) -> EmbeddingService:
    return EmbeddingService(ollama, settings)


def get_retriever(
    embeddings: EmbeddingService = Depends(get_embeddings),
    vector_store: VectorStore = Depends(get_vector_store),
) -> Retriever:
    return Retriever(embeddings, vector_store)


def get_generator(ollama: OllamaService = Depends(get_ollama)) -> Generator:
    return Generator(ollama)


DbSession = Depends(get_db)
