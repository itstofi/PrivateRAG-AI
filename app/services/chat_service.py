from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationError
from app.rag.generator import Generator
from app.rag.prompts import INSUFFICIENT_CONTEXT, build_prompt_bundle
from app.rag.query_quality import (
    contextualize_query,
    detect_conflicts,
    preprocess_query,
    sanitize_citation_markers,
)
from app.rag.retriever import Retriever
from app.rag.vector_store import SearchResult
from app.storage.models import Chat
from app.storage.repositories import ChatRepository, DocumentRepository, WorkspaceRepository


def citation_from_result(index: int, result: SearchResult) -> dict[str, Any]:
    return {
        "index": index,
        "source_filename": result.metadata["source_filename"],
        "page_number": result.metadata.get("page_number"),
        "section": result.metadata.get("section"),
        "chunk_id": result.chunk_id,
        "chunk_number": result.metadata.get("chunk_number"),
        "excerpt": result.text[:600],
        "relevance_score": round(result.score, 4),
    }


def export_chat_markdown(chat: Chat) -> str:
    lines = [
        f"# {chat.title}",
        "",
        f"- Workspace: {chat.workspace.name}",
        f"- Model: {chat.model}",
        f"- Created: {chat.created_at.isoformat()}",
        "",
    ]
    for message in chat.messages:
        lines.extend([f"## {message.role.title()}", "", message.content, ""])
        if message.citations:
            lines.append("### Sources")
            lines.append("")
            for citation in message.citations:
                page = f", page {citation['page_number']}" if citation.get("page_number") else ""
                lines.append(
                    f"- {citation['source_filename']}{page} "
                    f"(chunk {citation.get('chunk_number', 'n/a')})"
                )
            lines.append("")
    return "\n".join(lines)


class ChatService:
    def __init__(
        self,
        session: Session,
        retriever: Retriever,
        generator: Generator,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.chats = ChatRepository(session)
        self.workspaces = WorkspaceRepository(session)
        self.documents = DocumentRepository(session)
        self.retriever = retriever
        self.generator = generator

    async def prepare(
        self,
        workspace_id: str,
        question: str,
        model: str,
        chat_id: str | None,
        config: dict[str, Any],
    ) -> tuple[Chat, str, list[dict[str, Any]], list[dict[str, object]], dict[str, Any]]:
        normalized_question = preprocess_query(question)
        if not normalized_question:
            raise ValidationError("Question must contain readable text.")
        self.workspaces.get(workspace_id)
        if not any(
            item.status == "indexed"
            and item.embedding_model == self.settings.ollama_embedding_model
            for item in self.documents.list(workspace_id)
        ):
            raise ValidationError(
                "No documents are indexed with the active embedding model in this workspace."
            )
        chat = (
            self.chats.get(chat_id)
            if chat_id
            else self.chats.create(workspace_id, model, normalized_question[:80])
        )
        if chat.workspace_id != workspace_id:
            raise ValidationError("The chat does not belong to the selected workspace.")
        history = [(message.role, message.content) for message in chat.messages[-6:]]
        previous_user_question = next(
            (content for role, content in reversed(history) if role == "user"), None
        )
        retrieval = {
            "top_k": config.get("top_k", self.settings.top_k),
            "similarity_threshold": config.get(
                "similarity_threshold", self.settings.similarity_threshold
            ),
            "use_mmr": config.get("use_mmr", self.settings.use_mmr),
            "max_context_chars": config.get("max_context_chars", self.settings.max_context_chars),
        }
        self.chats.add_message(
            chat, "user", normalized_question, model, workspace_id, [], retrieval
        )
        retrieval_question = contextualize_query(normalized_question, previous_user_question)
        results = await self.retriever.retrieve(
            retrieval_question,
            workspace_id,
            int(retrieval["top_k"]),
            float(retrieval["similarity_threshold"]),
            bool(retrieval["use_mmr"]),
        )
        initial_bundle = build_prompt_bundle(
            normalized_question,
            results,
            int(retrieval["max_context_chars"]),
            history=history,
        )
        detected = detect_conflicts(initial_bundle.included_results)
        bundle = build_prompt_bundle(
            normalized_question,
            initial_bundle.included_results,
            int(retrieval["max_context_chars"]),
            detected,
            history,
        )
        citations = [
            citation_from_result(index, result)
            for index, result in enumerate(bundle.included_results, 1)
        ]
        conflicts = [item.as_dict() for item in detected]
        retrieval["detected_conflicts"] = conflicts
        return chat, bundle.prompt if citations else "", citations, conflicts, retrieval

    async def query(
        self,
        workspace_id: str,
        question: str,
        model: str,
        chat_id: str | None,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        chat, prompt, citations, conflicts, retrieval = await self.prepare(
            workspace_id, question, model, chat_id, config
        )
        answer = (
            await self.generator.generate(
                prompt, model, float(config.get("temperature", self.settings.temperature))
            )
            if citations
            else INSUFFICIENT_CONTEXT
        )
        answer = sanitize_citation_markers(answer, len(citations))
        self.chats.add_message(chat, "assistant", answer, model, workspace_id, citations, retrieval)
        return {
            "chat_id": chat.id,
            "answer": answer,
            "citations": citations,
            "conflicts": conflicts,
        }

    async def stream(
        self,
        workspace_id: str,
        question: str,
        model: str,
        chat_id: str | None,
        config: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        chat, prompt, citations, conflicts, retrieval = await self.prepare(
            workspace_id, question, model, chat_id, config
        )
        yield {
            "type": "metadata",
            "chat_id": chat.id,
            "citations": citations,
            "conflicts": conflicts,
        }
        if not citations:
            answer = INSUFFICIENT_CONTEXT
            yield {"type": "token", "content": answer}
        else:
            parts: list[str] = []
            async for token in self.generator.stream(
                prompt, model, float(config.get("temperature", self.settings.temperature))
            ):
                parts.append(token)
                yield {"type": "token", "content": token}
            answer = "".join(parts)
        answer = sanitize_citation_markers(answer, len(citations))
        self.chats.add_message(chat, "assistant", answer, model, workspace_id, citations, retrieval)
        yield {"type": "done", "answer": answer}
