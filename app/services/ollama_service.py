import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError


class OllamaService:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self._client = client

    def _make_client(self, timeout: float = 60.0) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient(
            base_url=self.settings.ollama_base_url, timeout=timeout, trust_env=False
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        client = self._make_client()
        should_close = self._client is None
        try:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ServiceUnavailableError(
                "Ollama is unavailable. Start it with `ollama serve` and check the configured URL."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise ServiceUnavailableError("Ollama rejected the request.", detail=detail) from exc
        finally:
            if should_close:
                await client.aclose()

    async def list_models(self) -> list[str]:
        response = await self._request("GET", "/api/tags")
        payload = self._json(response)
        models = payload.get("models", [])
        if not isinstance(models, list):
            raise ServiceUnavailableError("Ollama returned an invalid model-list response.")
        return [
            item["name"]
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]

    @staticmethod
    def model_names_match(configured: str, installed: str) -> bool:
        """Treat Ollama's implicit default tag as equivalent to `:latest`."""
        if ":" in configured:
            return configured == installed
        return installed in {configured, f"{configured}:latest"}

    async def list_chat_models(self, models: list[str] | None = None) -> list[str]:
        installed = models if models is not None else await self.list_models()
        chat_models: list[str] = []
        for model in installed:
            try:
                response = await self._request("POST", "/api/show", json={"model": model})
                capabilities = self._json(response).get("capabilities", [])
            except ServiceUnavailableError:
                capabilities = []
            if isinstance(capabilities, list) and "completion" in capabilities:
                chat_models.append(model)
            elif not capabilities and not self.model_names_match(
                self.settings.ollama_embedding_model, model
            ):
                # Older Ollama versions may not expose capabilities. In that case,
                # at least keep the configured embedding model out of the chat list.
                chat_models.append(model)
        return chat_models

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ServiceUnavailableError("Ollama returned malformed JSON.") from exc
        if not isinstance(payload, dict):
            raise ServiceUnavailableError("Ollama returned an invalid response.")
        return payload

    async def health(self) -> dict[str, Any]:
        try:
            models = await self.list_models()
        except ServiceUnavailableError as exc:
            return {"connected": False, "models": [], "message": exc.message}
        return {
            "connected": True,
            "models": models,
            "chat_model_available": any(
                self.model_names_match(self.settings.ollama_chat_model, model) for model in models
            ),
            "embedding_model_available": any(
                self.model_names_match(self.settings.ollama_embedding_model, model)
                for model in models
            ),
        }

    async def validate_model(self, model: str) -> None:
        if not any(
            self.model_names_match(model, installed) for installed in await self.list_models()
        ):
            raise ServiceUnavailableError(
                f"Model '{model}' is not installed. Run `ollama pull {model}` explicitly."
            )

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        response = await self._request(
            "POST",
            "/api/embed",
            json={"model": model or self.settings.ollama_embedding_model, "input": texts},
            timeout=120.0,
        )
        embeddings = self._json(response).get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise ServiceUnavailableError("Ollama returned an invalid embedding response.")
        return embeddings

    async def generate(
        self, prompt: str, model: str | None = None, temperature: float | None = None
    ) -> str:
        response = await self._request(
            "POST",
            "/api/generate",
            json={
                "model": model or self.settings.ollama_chat_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.settings.temperature if temperature is None else temperature
                },
            },
            timeout=300.0,
        )
        raw_answer = self._json(response).get("response", "")
        answer = raw_answer.strip() if isinstance(raw_answer, str) else ""
        if not answer:
            raise ServiceUnavailableError("Ollama returned an empty response.")
        return answer

    async def stream_generate(
        self, prompt: str, model: str | None = None, temperature: float | None = None
    ) -> AsyncIterator[str]:
        client = self._make_client(timeout=300.0)
        should_close = self._client is None
        try:
            async with client.stream(
                "POST",
                "/api/generate",
                json={
                    "model": model or self.settings.ollama_chat_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": self.settings.temperature
                        if temperature is None
                        else temperature
                    },
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        token = json.loads(line).get("response")
                        if token:
                            yield token
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise ServiceUnavailableError("Ollama streaming failed.", detail=str(exc)) from exc
        finally:
            if should_close:
                await client.aclose()
