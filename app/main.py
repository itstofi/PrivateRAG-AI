import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    chat,
    chats,
    documents,
    health,
    models,
    workspaces,
)
from app.api.routes import (
    settings as settings_route,
)
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.storage.database import init_database

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_directories()
    init_database()
    yield


app = FastAPI(
    title="PrivateRAG AI API",
    description="Local-only document ingestion and retrieval-augmented generation.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
for router in (
    health.router,
    models.router,
    settings_route.router,
    workspaces.router,
    documents.router,
    chats.router,
    chat.router,
):
    app.include_router(router)


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    logger.warning("Application error code=%s detail=%s", exc.code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "detail": None},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected local application error occurred.",
            "code": "internal_error",
            "detail": None,
        },
    )


@app.get("/", include_in_schema=False)
def root() -> dict[str, Any]:
    return {"name": settings.app_name, "docs": "/docs", "privacy": "local-only"}
