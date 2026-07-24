import asyncio

from app.services.ollama_service import OllamaService


async def check() -> int:
    status = await OllamaService().health()
    if not status["connected"]:
        print(status["message"])
        return 1
    print("Ollama is connected.")
    print(f"Chat model available: {status['chat_model_available']}")
    print(f"Embedding model available: {status['embedding_model_available']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
