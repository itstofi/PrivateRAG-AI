import json

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.services.ollama_service import OllamaService


@pytest.mark.asyncio
async def test_mocked_ollama_models_embeddings_and_generation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "local-embed:latest"},
                        {"name": "local-chat:latest"},
                    ]
                },
            )
        if request.url.path == "/api/show":
            model = json.loads(request.content)["model"]
            capabilities = ["embedding"] if "embed" in model else ["completion"]
            return httpx.Response(200, json={"capabilities": capabilities})
        if request.url.path == "/api/embed":
            assert json.loads(request.content)["input"] == ["alpha", "beta"]
            return httpx.Response(200, json={"embeddings": [[1.0, 0.0], [0.0, 1.0]]})
        if request.url.path == "/api/generate":
            assert json.loads(request.content)["stream"] is False
            return httpx.Response(200, json={"response": " Grounded answer. "})
        return httpx.Response(404)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    ) as client:
        service = OllamaService(
            Settings(
                _env_file=None,
                ollama_base_url="http://ollama.test",
                ollama_chat_model="local-chat",
                ollama_embedding_model="local-embed",
            ),
            client,
        )
        models = await service.list_models()
        assert models == ["local-embed:latest", "local-chat:latest"]
        assert await service.list_chat_models(models) == ["local-chat:latest"]
        status = await service.health()
        assert status["chat_model_available"] is True
        assert status["embedding_model_available"] is True
        assert await service.embed(["alpha", "beta"]) == [[1.0, 0.0], [0.0, 1.0]]
        assert await service.generate("Prompt", "local-chat", 0.0) == "Grounded answer."


@pytest.mark.asyncio
async def test_mocked_ollama_connection_failure() -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(fail), base_url="http://ollama.test"
    ) as client:
        service = OllamaService(
            Settings(_env_file=None, ollama_base_url="http://ollama.test"), client
        )
        with pytest.raises(ServiceUnavailableError, match="Start it with"):
            await service.list_models()
        status = await service.health()
        assert status["connected"] is False
        assert status["models"] == []
