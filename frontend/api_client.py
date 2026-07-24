import json
from collections.abc import Iterator
from typing import Any

import httpx


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                timeout=300,
                trust_env=False,
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise ApiError("The local API is unavailable. Start it with `make run-api`.") from exc
        if response.status_code >= 400:
            try:
                message = response.json().get("error", response.text)
            except ValueError:
                message = response.text
            raise ApiError(message)
        if response.status_code == 204:
            return None
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.text

    def stream(self, path: str, payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}{path}",
                json=payload,
                timeout=300,
                trust_env=False,
            ) as response:
                if response.status_code >= 400:
                    raise ApiError(response.read().decode())
                for line in response.iter_lines():
                    if line:
                        yield json.loads(line)
        except httpx.RequestError as exc:
            raise ApiError("The local API or Ollama stream became unavailable.") from exc
