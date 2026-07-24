from __future__ import annotations

import builtins
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.storage.models import Chat, Document, Message, Workspace


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Workspace]:
        return list(self.session.scalars(select(Workspace).order_by(Workspace.name)))

    def get(self, workspace_id: str) -> Workspace:
        item = self.session.get(Workspace, workspace_id)
        if item is None:
            raise NotFoundError("Workspace not found.")
        return item

    def create(self, name: str) -> Workspace:
        item = Workspace(name=name.strip())
        self.session.add(item)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("A workspace with this name already exists.") from exc
        self.session.refresh(item)
        return item

    def rename(self, workspace_id: str, name: str) -> Workspace:
        item = self.get(workspace_id)
        item.name = name.strip()
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("A workspace with this name already exists.") from exc
        return item

    def delete(self, workspace_id: str) -> None:
        self.session.delete(self.get(workspace_id))
        self.session.commit()

    def stats(self, workspace_id: str) -> dict[str, int]:
        self.get(workspace_id)
        document_count, chunk_count = self.session.execute(
            select(func.count(Document.id), func.coalesce(func.sum(Document.chunk_count), 0)).where(
                Document.workspace_id == workspace_id
            )
        ).one()
        chat_count = self.session.scalar(
            select(func.count(Chat.id)).where(Chat.workspace_id == workspace_id)
        )
        return {
            "document_count": int(document_count),
            "chunk_count": int(chunk_count),
            "chat_count": int(chat_count or 0),
        }


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, workspace_id: str | None = None) -> list[Document]:
        query = select(Document).order_by(Document.uploaded_at.desc())
        if workspace_id:
            query = query.where(Document.workspace_id == workspace_id)
        return list(self.session.scalars(query))

    def get(self, document_id: str) -> Document:
        item = self.session.get(Document, document_id)
        if item is None:
            raise NotFoundError("Document not found.")
        return item

    def find_duplicate(self, workspace_id: str, sha256: str) -> Document | None:
        return self.session.scalar(
            select(Document).where(Document.workspace_id == workspace_id, Document.sha256 == sha256)
        )

    def create(self, **values: object) -> Document:
        item = Document(**values)
        self.session.add(item)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("This document already exists in the workspace.") from exc
        self.session.refresh(item)
        return item

    def update_status(
        self,
        document: Document,
        status: str,
        *,
        error: str | None = None,
        page_count: int | None = None,
        chunk_count: int | None = None,
    ) -> Document:
        document.status = status
        document.processing_error = error
        if page_count is not None:
            document.page_count = page_count
        if chunk_count is not None:
            document.chunk_count = chunk_count
        self.session.commit()
        return document

    def delete(self, document: Document) -> None:
        self.session.delete(document)
        self.session.commit()


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, workspace_id: str | None = None) -> list[Chat]:
        query = select(Chat).order_by(Chat.updated_at.desc())
        if workspace_id:
            query = query.where(Chat.workspace_id == workspace_id)
        return list(self.session.scalars(query))

    def get(self, chat_id: str, with_messages: bool = True) -> Chat:
        query = select(Chat).where(Chat.id == chat_id)
        if with_messages:
            query = query.options(selectinload(Chat.messages))
        item = self.session.scalar(query)
        if item is None:
            raise NotFoundError("Chat not found.")
        return item

    def create(self, workspace_id: str, model: str, title: str = "New chat") -> Chat:
        item = Chat(workspace_id=workspace_id, model=model, title=title.strip())
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def rename(self, chat_id: str, title: str) -> Chat:
        item = self.get(chat_id, with_messages=False)
        item.title = title.strip()
        item.updated_at = datetime.now(UTC)
        self.session.commit()
        return item

    def add_message(
        self,
        chat: Chat,
        role: str,
        content: str,
        model: str,
        workspace_id: str,
        citations: builtins.list[dict[str, object]] | None = None,
        retrieval_config: dict[str, object] | None = None,
    ) -> Message:
        item = Message(
            chat_id=chat.id,
            role=role,
            content=content,
            model=model,
            workspace_id=workspace_id,
            citations=citations or [],
            retrieval_config=retrieval_config or {},
        )
        chat.updated_at = datetime.now(UTC)
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, chat_id: str) -> None:
        self.session.delete(self.get(chat_id, with_messages=False))
        self.session.commit()
