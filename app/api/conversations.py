from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rate_limit import limiter, _get_user_key
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.schemas.message import MessageResponse, MessageCreate
from app.models.conversation import Conversation
from app.services.conversation_service import ConversationService
from app.services.chat_service import ChatService
from app.services.billing_service import get_user_limits

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ConversationService.list_conversations(db, current_user.id, limit=limit, offset=offset)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_admin = any(r.name == "admin" for r in current_user.roles)
    if not is_admin:
        limits = get_user_limits(db, current_user.id)
        max_conv = limits["max_conversations"]
        if max_conv is not None:
            count = db.query(Conversation).filter(Conversation.user_id == current_user.id).count()
            if count >= max_conv:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Conversation limit reached ({max_conv}). Upgrade your plan to create more.",
                )
    return ConversationService.create_conversation(db, current_user.id, data)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ConversationService.delete_conversation(db, conversation_id, current_user.id)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    before_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ConversationService.get_messages(
        db, conversation_id, current_user.id, limit=limit, before_id=before_id
    )


@router.post("/{conversation_id}/messages/stream")
@limiter.limit(lambda: settings.RATE_LIMIT_CHAT, key_func=_get_user_key)
async def stream_message(
    request: Request,
    conversation_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return StreamingResponse(
        ChatService.stream_message(db, conversation_id, current_user.id, body.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
