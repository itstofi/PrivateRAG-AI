from collections.abc import AsyncIterator

from app.services.ollama_service import OllamaService


class Generator:
    def __init__(self, ollama: OllamaService) -> None:
        self.ollama = ollama

    async def generate(self, prompt: str, model: str, temperature: float) -> str:
        return await self.ollama.generate(prompt, model, temperature)

    async def stream(self, prompt: str, model: str, temperature: float) -> AsyncIterator[str]:
        async for token in self.ollama.stream_generate(prompt, model, temperature):
            yield token
