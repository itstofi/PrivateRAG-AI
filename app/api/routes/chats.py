from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.schemas import ChatCreate, ChatDetail, ChatRead, ChatUpdate
from app.services.chat_service import export_chat_markdown
from app.storage.database import get_db
from app.storage.repositories import ChatRepository, WorkspaceRepository

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=list[ChatRead])
def list_chats(
    workspace_id: str | None = Query(default=None), session: Session = Depends(get_db)
) -> list[ChatRead]:
    return [ChatRead.model_validate(item) for item in ChatRepository(session).list(workspace_id)]


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
def create_chat(payload: ChatCreate, session: Session = Depends(get_db)) -> ChatRead:
    WorkspaceRepository(session).get(payload.workspace_id)
    return ChatRead.model_validate(
        ChatRepository(session).create(payload.workspace_id, payload.model, payload.title)
    )


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: str, session: Session = Depends(get_db)) -> ChatDetail:
    return ChatDetail.model_validate(ChatRepository(session).get(chat_id))


@router.patch("/{chat_id}", response_model=ChatRead)
def rename_chat(chat_id: str, payload: ChatUpdate, session: Session = Depends(get_db)) -> ChatRead:
    return ChatRead.model_validate(ChatRepository(session).rename(chat_id, payload.title))


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: str, session: Session = Depends(get_db)) -> Response:
    ChatRepository(session).delete(chat_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{chat_id}/export", response_class=PlainTextResponse)
def export_chat(chat_id: str, session: Session = Depends(get_db)) -> PlainTextResponse:
    chat = ChatRepository(session).get(chat_id)
    return PlainTextResponse(
        export_chat_markdown(chat),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="chat-{chat.id}.md"'},
    )
