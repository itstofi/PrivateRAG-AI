from app.core.config import Settings, get_settings
from app.services.ollama_service import OllamaService


class EmbeddingService:
    def __init__(
        self, ollama: OllamaService | None = None, settings: Settings | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self.ollama = ollama or OllamaService(self.settings)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        output: list[list[float]] = []
        size = self.settings.embedding_batch_size
        for start in range(0, len(texts), size):
            output.extend(await self.ollama.embed(texts[start : start + size]))
        return output

    async def embed_query(self, text: str) -> list[float]:
        return (await self.ollama.embed([text]))[0]
