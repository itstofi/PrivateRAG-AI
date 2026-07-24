import asyncio

from app.core.exceptions import ServiceUnavailableError
from app.services.ollama_service import OllamaService


async def list_models() -> int:
    try:
        models = await OllamaService().list_models()
    except ServiceUnavailableError as exc:
        print(exc.message)
        return 1
    if not models:
        print("No local models installed. Use `ollama pull <model>` explicitly.")
    for model in models:
        print(model)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(list_models()))
