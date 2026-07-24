import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_generator, get_retriever
from app.api.schemas import QueryRequest, QueryResponse
from app.rag.generator import Generator
from app.rag.retriever import Retriever
from app.services.chat_service import ChatService
from app.storage.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    session: Session = Depends(get_db),
    retriever: Retriever = Depends(get_retriever),
    generator: Generator = Depends(get_generator),
) -> QueryResponse:
    result = await ChatService(session, retriever, generator).query(
        payload.workspace_id,
        payload.question,
        payload.model,
        payload.chat_id,
        payload.retrieval.model_dump(),
    )
    return QueryResponse.model_validate(result)


@router.post("/stream")
async def stream(
    payload: QueryRequest,
    session: Session = Depends(get_db),
    retriever: Retriever = Depends(get_retriever),
    generator: Generator = Depends(get_generator),
) -> StreamingResponse:
    service = ChatService(session, retriever, generator)
    iterator = service.stream(
        payload.workspace_id,
        payload.question,
        payload.model,
        payload.chat_id,
        payload.retrieval.model_dump(),
    )
    first_event = await anext(iterator)

    async def events():
        yield json.dumps(first_event, ensure_ascii=False) + "\n"
        try:
            async for event in iterator:
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception:
            logger.exception("Chat stream failed")
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "error": "The local answer stream failed. Check Ollama and try again.",
                    }
                )
                + "\n"
            )

    return StreamingResponse(events(), media_type="application/x-ndjson")
