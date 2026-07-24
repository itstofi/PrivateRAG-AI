import os

import pytest

from app.services.ollama_service import OllamaService


@pytest.mark.ollama
@pytest.mark.skipif(not os.getenv("RUN_OLLAMA_TESTS"), reason="explicit opt-in required")
@pytest.mark.asyncio
async def test_real_ollama_connection() -> None:
    status = await OllamaService().health()
    assert status["connected"] is True
    assert status["models"]
